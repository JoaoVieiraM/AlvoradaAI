# AlvoradaAI

Agente autônomo que roda todo dia às **06h00 BRT**, varre as principais fontes de IA, Machine Learning e Computação Quântica, analisa tudo com um LLM e entrega um digest mastigado focado em **aplicabilidade real** e **impacto social**.

---

## Como funciona

```
ArXiv ──────┐
RSS (8 fontes) ─┼──▶ Coleta paralela ──▶ Claude / Groq ──▶ digest.md + digest.html
Papers w/ Code ─┘                                        └──▶ e-mail (opcional)
```

1. **Coleta** — fetchers assíncronos buscam papers e artigos das últimas 96h em paralelo
2. **Análise** — o LLM filtra, prioriza e analisa cada item: o que é, onde aplicar, impacto social, urgência
3. **Entrega** — salva `.md` e `.html` em `outputs/`; envia por e-mail se SMTP configurado

---

## Fontes cobertas

| Fonte | Tipo |
|---|---|
| ArXiv (cs.AI, cs.LG, cs.CL, quant-ph) | Papers |
| HuggingFace Blog | Lab |
| OpenAI Blog | Lab |
| MIT Technology Review | Notícias |
| Ben's Bites | Newsletter |
| Quanta Magazine | Ciência |
| Synced Review | Indústria |
| Stanford HAI | Acadêmico |
| Towards Data Science | Comunidade |
| Papers with Code | Papers + código |

---

## Setup

### 1. Clone e instale

```bash
git clone https://github.com/JoaoVieiraM/AlvoradaAI.git
cd AlvoradaAI
pip install -r requirements.txt
```

### 2. Configure as variáveis de ambiente

```bash
cp .env.example .env
# Edite .env com suas credenciais
```

#### Opção A — Groq (gratuito, ideal para começar)

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...        # console.groq.com — free tier generoso
GROQ_MODEL=llama-3.3-70b-versatile
```

#### Opção B — Anthropic (produção, ~$1-2/mês)

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Rode manualmente

```bash
python agent.py
# Digest salvo em outputs/digest_YYYY-MM-DD.md
```

---

## Agendamento com GitHub Actions

O workflow `.github/workflows/daily_digest.yml` roda automaticamente às **06h00 BRT** todos os dias.

### Ativar em 3 passos

**1.** Faça o push do repositório para o GitHub

**2.** Adicione os secrets em **Settings → Secrets and variables → Actions**:

| Secret | Valor |
|---|---|
| `LLM_PROVIDER` | `groq` ou `anthropic` |
| `GROQ_API_KEY` | sua key do Groq |
| `ANTHROPIC_API_KEY` | sua key da Anthropic |
| `DIGEST_SMTP_HOST` | opcional — para entrega por e-mail |

**3.** Teste em **Actions → Morning Digest → Run workflow**

O digest gerado aparece na aba **Artifacts** em ~1 minuto.

---

## Estrutura do projeto

```
AlvoradaAI/
├── agent.py                 # Orquestrador: coleta → analisa → entrega
├── formatter.py             # Salva .md e .html, envia e-mail
├── requirements.txt
├── .env.example
├── fetchers/
│   ├── arxiv_fetcher.py     # API oficial do ArXiv
│   ├── rss_fetcher.py       # RSS/Atom (Atom e RSS 2.0)
│   └── web_fetcher.py       # Papers with Code API
├── prompts/
│   └── analysis_prompt.py   # Prompt de análise (PT-BR)
├── outputs/                 # Digests gerados (criado automaticamente)
└── .github/
    └── workflows/
        └── daily_digest.yml # Cron 06h00 BRT
```

---

## Custo estimado

| Componente | Custo |
|---|---|
| GitHub Actions | **$0** — dentro do free tier (< 100 min/mês) |
| Groq (Llama 3.3 70B) | **$0** — free tier |
| Anthropic Sonnet 4.6 | **~$1–2/mês** com prompt caching |

---

## Customização

### Adicionar uma fonte RSS

Em `agent.py`, adicione à lista `RSS_SOURCES`:

```python
{"name": "Nome da fonte", "url": "https://fonte.com/feed", "category": "news"},
```

### Mudar o foco da análise

Edite `prompts/analysis_prompt.py` — o `SYSTEM_PROMPT` é em português e bem comentado. Você pode focar só em saúde, finanças, aplicações empresariais, etc.

### Trocar o modelo

Basta alterar `LLM_PROVIDER` no `.env`. O adapter suporta `anthropic`, `groq` e `ollama` sem nenhuma mudança no código.

---

## Licença

MIT — use, modifique e distribua livremente.
