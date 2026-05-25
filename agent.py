"""
Morning Digest Agent — orquestrador principal.
Coleta fontes, analisa com Claude e entrega o digest.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Garante UTF-8 no console Windows para exibir emojis nos logs
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import anthropic
import openai
from dotenv import load_dotenv

from fetchers.arxiv_fetcher import fetch_arxiv
from fetchers.rss_fetcher import fetch_rss_sources
from fetchers.web_fetcher import fetch_web_sources
from prompts.analysis_prompt import SYSTEM_PROMPT, build_user_message
import formatter

load_dotenv()

# ---------------------------------------------------------------------------
# Validação de startup — falha rápido com mensagem clara
# ---------------------------------------------------------------------------

def _validate_env() -> None:
    provider = (os.getenv("LLM_PROVIDER") or "anthropic").strip().lower()
    missing = []

    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    elif provider == "groq" and not os.getenv("GROQ_API_KEY"):
        missing.append("GROQ_API_KEY")
    elif provider == "ollama":
        pass  # Ollama não precisa de key
    elif provider not in ("anthropic", "groq", "ollama"):
        missing.append(f"LLM_PROVIDER válido (recebido: '{provider}' — use anthropic, groq ou ollama)")

    if missing:
        for m in missing:
            print(f"[ERRO] Variável de ambiente obrigatória não configurada: {m}", flush=True)
        print("[ERRO] Configure os secrets em: Settings → Secrets and variables → Actions", flush=True)
        sys.exit(1)

_validate_env()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f"logs/agent_{datetime.now().strftime('%Y-%m-%d')}.log",
            encoding="utf-8",
        ),
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fontes
# ---------------------------------------------------------------------------

RSS_SOURCES = [
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/",  "category": "news"},
    {"name": "OpenAI Blog",           "url": "https://openai.com/blog/rss.xml",         "category": "lab"},
    {"name": "HuggingFace Blog",      "url": "https://huggingface.co/blog/feed.xml",    "category": "lab"},
    {"name": "Ben's Bites",           "url": "https://www.bensbites.com/feed",          "category": "newsletter"},
    {"name": "Quanta Magazine",       "url": "https://www.quantamagazine.org/feed/",    "category": "science"},
    {"name": "Synced Review",         "url": "https://syncedreview.com/feed/",          "category": "industry"},
    {"name": "Stanford HAI",          "url": "https://hai.stanford.edu/news/rss.xml",   "category": "academic"},
    {"name": "Towards Data Science",  "url": "https://towardsdatascience.com/feed",     "category": "community"},
]

ARXIV_QUERIES = [
    "cat:cs.AI",
    "cat:cs.LG",
    "cat:cs.CL",
    "cat:quant-ph",
]

# ---------------------------------------------------------------------------
# Coleta
# ---------------------------------------------------------------------------

async def collect_items() -> list[dict]:
    log.info("Iniciando coleta em paralelo...")
    results = await asyncio.gather(
        fetch_rss_sources(RSS_SOURCES, max_per_source=5),
        fetch_arxiv(ARXIV_QUERIES, max_per_query=3),
        fetch_web_sources(max_items=5),
        return_exceptions=True,
    )

    all_items: list[dict] = []
    labels = ["RSS", "ArXiv", "Papers with Code"]
    for label, batch in zip(labels, results):
        if isinstance(batch, Exception):
            log.warning(f"{label} falhou: {batch}")
        else:
            log.info(f"{label}: {len(batch)} itens")
            all_items.extend(batch)

    # Deduplica por URL — mantém primeira ocorrência
    seen: set[str] = set()
    unique: list[dict] = []
    for item in all_items:
        url = item.get("url", "")
        if url and url in seen:
            continue
        if url:
            seen.add(url)
        unique.append(item)

    log.info(f"Total: {len(unique)} itens únicos (de {len(all_items)} coletados)")
    return unique

# ---------------------------------------------------------------------------
# Análise com LLM — despacha para o provider configurado
# ---------------------------------------------------------------------------

def call_llm(items: list[dict]) -> str:
    provider = (os.getenv("LLM_PROVIDER") or "anthropic").strip().lower()
    log.info(f"Provider LLM: {provider} | {len(items)} itens")

    if provider == "anthropic":
        return _call_anthropic(items)
    elif provider in ("groq", "ollama"):
        return _call_openai_compat(items, provider)
    else:
        raise ValueError(f"LLM_PROVIDER desconhecido: '{provider}'. Use anthropic, groq ou ollama.")


def _call_anthropic(items: list[dict]) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": build_user_message(items)}],
    )
    usage = response.usage
    log.info(
        f"Tokens — entrada: {usage.input_tokens} "
        f"(cache hit: {getattr(usage, 'cache_read_input_tokens', 0)}) | "
        f"saída: {usage.output_tokens}"
    )
    return response.content[0].text


def _call_openai_compat(items: list[dict], provider: str) -> str:
    if provider == "groq":
        base_url = "https://api.groq.com/openai/v1"
        api_key = os.environ["GROQ_API_KEY"]
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    else:  # ollama
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        api_key = "ollama"  # Ollama não valida a key, mas o SDK exige um valor
        model = os.getenv("OLLAMA_MODEL", "llama3.2")

    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": build_user_message(items)},
        ],
    )
    usage = response.usage
    log.info(f"Tokens — entrada: {usage.prompt_tokens} | saída: {usage.completion_tokens}")
    return response.choices[0].message.content

# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

async def main() -> None:
    log.info("=== Morning Digest Agent iniciado ===")
    start = datetime.now()

    items = await collect_items()
    if not items:
        log.warning("Nenhum item coletado. Encerrando.")
        return

    digest_md = call_llm(items)
    formatter.save_outputs(digest_md)

    elapsed = (datetime.now() - start).total_seconds()
    log.info(f"=== Digest concluído em {elapsed:.1f}s ===")


if __name__ == "__main__":
    asyncio.run(main())
