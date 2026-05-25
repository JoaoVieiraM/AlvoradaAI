# AlvoradaAI

Agente de inteligência autônomo que roda todo dia às **06h00 BRT**, varre as principais fontes de IA, agentes em produção e mercado tech, filtra pelo perfil estratégico do **Danrley Morais** (CTO da Runflow / fundador do IFTL) e entrega um digest provocador focado em **ROI, Agentes em Produção e M&A**.

---

## Como funciona

```
TechCrunch AI ──┐
VentureBeat ────┤
OpenAI Blog ────┤
HuggingFace ────┼──▶ Coleta paralela ──▶ Filtro de relevância ──▶ Groq / Claude ──▶ Alvorada Intelligence
Ben's Bites ────┤                         (40+ keywords)
MIT Tech Review ┤
ArXiv (4 cats) ─┘
```

1. **Coleta** — fetchers assíncronos buscam artigos e papers das últimas 96h em paralelo
2. **Filtro** — descarta itens sem keywords estratégicas (agent, roi, deploy, m&a, llm...)
3. **Análise** — o LLM analisa sob a ótica de CTO: Pedrada do Dia, Visão CTO, Impacto na Runflow/IFTL
4. **Entrega** — salva `.md` e `.html` em `outputs/`; envia por e-mail se SMTP configurado

---

## Fontes cobertas

| Fonte | Tipo | Foco |
|---|---|---|
| TechCrunch AI | Notícias | M&A, Enterprise, Startups |
| VentureBeat | Notícias | Agentes em produção, riscos enterprise |
| MIT Technology Review | Notícias | Tendências e impacto de longo prazo |
| OpenAI Blog | Lab | Atualizações de modelos e produtos |
| HuggingFace Blog | Lab | Engenharia e modelos open-source |
| Ben's Bites | Newsletter | Curadoria de builders e líderes de IA |
| Towards Data Science | Comunidade | Implementação prática |
| ArXiv cs.AI | Papers | IA aplicada |
| ArXiv cs.LG | Papers | Machine Learning |
| ArXiv cs.CL | Papers | LLMs e NLP |
| ArXiv cs.MA | Papers | Multi-Agent Systems (core da Runflow) |
| Papers with Code | Papers + código | Implementações prontas |

---

## O Digest — Alvorada Intelligence

O formato é personalizado para o perfil de Danrley:

```markdown
# 🌅 Alvorada Intelligence — DD/MM/AAAA

## 📊 Resumo do Front
Big Picture do dia focado em ROI e Estratégia de IA

## 🔥 As Pedradas do Dia (Top 3)
- Visão CTO: impacto técnico conectado ao produto
- A Provocação: sugestão de postagem para LinkedIn/Instagram
- Impacto na Runflow/IFTL: análise nos negócios do Danrley
- Urgência: 🔴 Agora / 🟡 Observar / 🟢 Longo prazo

## 🛠️ Tech & Agents (Produção)
Frameworks, LLMs e infraestrutura para agentes

## 📈 Business & M&A
Movimentações de mercado e parcerias

## 💡 Conexão Estratégica
O padrão que ninguém está vendo
```

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

### Ativar em 2 passos

**1.** Adicione o secret em **Settings → Secrets and variables → Actions**:

| Secret | Valor |
|---|---|
| `GROQ_API_KEY` | sua key do Groq (console.groq.com) |

> `LLM_PROVIDER` e `GROQ_MODEL` já estão fixos no workflow — não precisam de secret.

**2.** Teste em **Actions → Morning Digest → Run workflow**

O digest aparece na aba **Artifacts** em ~1 minuto.

---

## Estrutura do projeto

```
AlvoradaAI/
├── agent.py                 # Orquestrador: coleta → filtra → analisa → entrega
├── formatter.py             # Salva .md e .html, envia e-mail
├── requirements.txt
├── .env.example
├── fetchers/
│   ├── arxiv_fetcher.py     # API do ArXiv (queries sequenciais, delay 3s)
│   ├── rss_fetcher.py       # RSS/Atom assíncrono
│   └── web_fetcher.py       # Papers with Code API
├── prompts/
│   └── analysis_prompt.py   # SYSTEM_PROMPT perfil Danrley + build_user_message()
├── outputs/                 # Digests gerados (criado automaticamente)
├── logs/                    # Logs de execução (criado automaticamente)
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
| Anthropic Sonnet 4.6 | **~$1/mês** com filtro de relevância + prompt caching |

> O filtro de relevância por keywords reduziu o consumo de tokens em ~47% comparado à versão sem filtro.

---

## Customização

### Mudar o perfil de análise

Edite `prompts/analysis_prompt.py` — o `SYSTEM_PROMPT` define o filtro e o formato do digest. Adapte para o seu perfil: setor, empresa, foco estratégico.

### Adicionar uma fonte RSS

Em `agent.py`, adicione à lista `RSS_SOURCES`:

```python
{"name": "Nome da fonte", "url": "https://fonte.com/feed", "category": "news"},
```

### Ajustar o filtro de relevância

Em `agent.py`, edite o conjunto `RELEVANCE_KEYWORDS` para incluir ou remover termos alinhados ao seu contexto.

### Trocar o modelo

Altere `LLM_PROVIDER` no `.env` ou no workflow. Suporta `anthropic`, `groq` e `ollama` sem mudança no código.

---

## Licença

MIT — use, modifique e distribua livremente.
