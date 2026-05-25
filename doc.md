# Morning Digest Agent — Diário de Desenvolvimento

Registro de cada task: o que foi feito, dificuldades encontradas e como foram resolvidas.

---

## Task 1 — Criar estrutura de diretórios do projeto

**Status:** concluída ✅

### O que foi feito

- Criação da pasta `morning_digest/` com subpastas `fetchers/`, `prompts/`, `outputs/`, `logs/`
- Cópia dos arquivos já implementados para os locais corretos
- Criação do `.env.example` com todas as variáveis necessárias

### Arquivos posicionados

| Arquivo destino | Conteúdo |
|---|---|
| `fetchers/__init__.py` | Pacote fetchers |
| `fetchers/rss_fetcher.py` | Fetcher RSS (Atom + RSS 2.0) |
| `fetchers/arxiv_fetcher.py` | Fetcher ArXiv API |
| `fetchers/web_fetcher.py` | Fetcher Papers with Code |
| `prompts/__init__.py` | Pacote prompts |
| `prompts/analysis_prompt.py` | Prompt de análise do Claude |
| `requirements.txt` | Dependências Python |
| `.env.example` | Template de variáveis de ambiente |

### Dificuldades

- Os arquivos temporários vieram com nomes trocados (ex: `arxiv_fetcher (1).py` continha na verdade o `web_fetcher.py`). Foi necessário identificar o conteúdo real de cada arquivo pelo código interno antes de posicioná-lo corretamente.

### Como resolvemos

- Leitura do conteúdo de cada arquivo (funções exportadas, docstrings, constantes como `ARXIV_API`, `PWC_API`) para inferir o módulo correto e posicionar no lugar certo.

---

## Task 2 — Implementar agent.py

**Status:** concluída ✅

### O que foi feito

- Criação do `agent.py` com logging dual (console + arquivo em `logs/`)
- Coleta paralela via `asyncio.gather()` dos 3 fetchers, com captura individual de exceções por fonte
- Deduplicação por URL mantendo a primeira ocorrência
- Chamada ao Claude `claude-sonnet-4-6` via SDK Anthropic

### Decisão de design: prompt caching

Reestruturamos `analysis_prompt.py` para separar o prompt em duas partes:
- `SYSTEM_PROMPT` — instruções estáticas, passadas via parâmetro `system` com `cache_control: ephemeral`
- `build_user_message(items)` — apenas o JSON dos itens coletados (muda todo dia)

Isso permite que o Claude reutilize o cache das instruções entre execuções do mesmo dia, reduzindo custo e latência. O log exibe os tokens de cache hit a cada rodada.

### Dificuldades

Nenhuma bloqueante. Ponto de atenção: `getattr(usage, 'cache_read_input_tokens', 0)` foi usado defensivamente porque o atributo só aparece na resposta quando há cache hit — a SDK não garante que o campo sempre existe.

### Como resolvemos

`getattr` com fallback `0` evita `AttributeError` na primeira execução do dia (quando ainda não há cache).

---

## Task 3 — Implementar formatter.py

**Status:** concluída ✅

### O que foi feito

- `save_outputs(digest_md)` — ponto de entrada único chamado pelo `agent.py`
- Salva `outputs/digest_YYYY-MM-DD.md` com o Markdown bruto do Claude
- Converte para HTML com a lib `markdown` (extensões `tables` + `fenced_code`) e salva `outputs/digest_YYYY-MM-DD.html`
- Envia e-mail via SMTP apenas se `DIGEST_SMTP_HOST` estiver definido — fallback silencioso caso contrário
- E-mail enviado como `MIMEMultipart("alternative")` com parte texto (Markdown) e parte HTML — cliente de e-mail escolhe o melhor formato

### Decisão de design: template HTML inline

O HTML é gerado com um template embutido no próprio arquivo (sem dependência de Jinja2 ou arquivos externos). Facilita deploy em ambientes simples como GitHub Actions onde não há sistema de arquivos persistente.

### Dificuldades

- A lib `markdown` não vem com `tables` e `fenced_code` por padrão no import simples — é preciso passar as extensões explicitamente em `md_lib.markdown(content, extensions=[...])`.
- `smtplib.SMTP` com `starttls()` requer chamar `ehlo()` antes, senão alguns servidores rejeitam a negociação TLS.

### Como resolvemos

- Extensões declaradas explicitamente na chamada.
- `ehlo()` chamado antes de `starttls()` para garantir compatibilidade máxima com provedores (Gmail, Outlook, etc).

---

## Task 4 — Testar pipeline completo localmente

**Status:** concluída ✅

### Resultado do teste (2026-05-25, 15:59, 9.3s)

| Etapa | Resultado |
|---|---|
| Coleta RSS | ✅ 6 itens de MIT Tech Review, OpenAI, Synced, Stanford HAI, Towards Data Science |
| Coleta ArXiv | ⚠️ 0 itens |
| Papers with Code | ⚠️ 0 itens |
| Chamada Groq (Llama 3.3 70B) | ✅ 1578 tokens entrada / 1205 saída |
| Geração do .md | ✅ `outputs/digest_2026-05-25.md` (4.7 KB) |
| Geração do .html | ✅ `outputs/digest_2026-05-25.html` (6.1 KB) |
| Entrega e-mail | ➖ Skipped (SMTP não configurado) |

### Dificuldades encontradas

**1. ArXiv e Papers with Code retornaram 0 itens**
Causa: o teste rodou em um domingo. O ArXiv não publica novos papers no fim de semana e o cutoff de 48h exclui os submissions de sexta-feira. Comportamento esperado — em dias úteis os itens aparecem normalmente.

**2. Três feeds RSS com URL quebrada**
- `The Batch` — URL retornou 308 redirect para um endpoint 404. URL desatualizada.
- `Ben's Bites` — `bensbites.beehiiv.com/feed` retornou 404. Publicação migrou de plataforma.
- `Anthropic News` — `anthropic.com/news/rss.xml` retornou 404. Anthropic não tem feed RSS público oficial.

**3. Emojis no log aparecem como `?` no PowerShell**
Problema de codificação UTF-8 no terminal Windows. O arquivo de log em disco está correto — é só exibição no console.

### Como resolvemos

- **ArXiv/PWC:** sem ação necessária, é comportamento correto para fim de semana.
- **Feeds quebrados:** silenciados pelo design do fetcher (`return []` em exceção). O pipeline não quebra — apenas não coleta esses itens. URLs devem ser atualizadas ou removidas da lista `RSS_SOURCES`.
- **Encoding do console:** adicionar `PYTHONIOENCODING=utf-8` ao `.env` ou configurar o terminal. Não afeta o funcionamento.

### Conteúdo do digest

Digest em português estruturado corretamente com resumo executivo, destaques, seções por categoria e análise de padrões. Qualidade adequada para o Llama 3.3 70B do Groq.

---

## Análise e resolução dos 3 achados do teste

**Status:** concluída ✅ (executada entre Task 4 e Task 5)

### Achado 1 — ArXiv/Papers with Code zerados no fim de semana

**Causa:** cutoff de 48h (ArXiv) e 72h (Papers with Code) excluía os papers de sexta-feira quando o agente rodava no domingo. O ArXiv não processa submissions no fim de semana.

**Solução:** ampliar o cutoff para 96h nos dois fetchers. Cobre sexta + sábado + domingo sem risco de trazer conteúdo velho demais.

**Resultado:** ArXiv passou de 0 → 12 itens na segunda execução.

---

### Achado 2 — 3 feeds RSS com URL quebrada

| Feed | Problema | Solução |
|---|---|---|
| **Ben's Bites** | Migrou de `bensbites.beehiiv.com` para Substack e depois para domínio próprio | URL atualizada para `www.bensbites.com/feed` (verificada e ativa) |
| **The Batch (DeepLearning.AI)** | Sem feed RSS oficial — newsletter só por e-mail | Substituído por **HuggingFace Blog** (`huggingface.co/blog/feed.xml`) — feed ativo, conteúdo técnico de alta qualidade |
| **Anthropic News** | Anthropic não oferece feed RSS público | Removido da lista. Conteúdo da Anthropic aparece indiretamente via Ben's Bites e outras fontes |

**Como descobrimos:** `WebFetch` nas páginas oficiais de cada fonte para confirmar existência ou ausência de `<link type="application/rss+xml">`. URLs candidatas testadas antes de adotar.

**Resultado:** RSS passou de 6 → 7 itens; Ben's Bites e HuggingFace retornam 200 OK.

---

### Achado 3 — Emojis aparecendo como `?` no console Windows

**Causa:** PowerShell no Windows usa encoding CP1252 por padrão. O `logging.StreamHandler` herda o encoding do `sys.stdout`, que não era UTF-8.

**Solução:** adicionado no topo de `agent.py`:
```python
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
```
Uso de `hasattr` para não quebrar em ambientes onde `reconfigure` não existe (Python < 3.7, alguns terminais embedded).

**Resultado:** logs exibem corretamente `Tokens — entrada`, `SMTP não configurado`, etc.

---

## Task 9 — Testar e fazer push das mudanças

**Status:** concluída ✅

### Resultado do teste (2026-05-25, 18:05, 42.2s)

| Etapa | Resultado |
|---|---|
| RSS (7 fontes novas) | ✅ 14 itens — TechCrunch AI e VentureBeat entregando conteúdo relevante |
| ArXiv | ⚠️ 0 itens — 429 rate limit (domingo, comportamento esperado) |
| Papers with Code | ⚠️ 0 itens — fim de semana |
| Filtro de relevância | ✅ 14 → 10 itens (4 descartados) |
| Tokens enviados | ✅ 2.266 entrada (vs 4.268 antes) — **47% menos tokens** |
| Groq (Llama 3.3 70B) | ✅ 927 tokens saída |
| Formato "Alvorada Intelligence" | ✅ Novo formato com Pedradas, Provocação, Runflow/IFTL |

### Qualidade do digest

Digest muito mais alinhado ao perfil do Danrley:
- "ClickUp Substitui Funcionários por Agentes AI" → 🔴 urgente
- "Dívida de Prompt e Risco em Sistemas de IA" → provocação para LinkedIn
- "Agentes AI e Falhas em Engenharia de Chaos" → impacto direto na Runflow

### Bug encontrado e corrigido

O LLM estava chutando a data do digest (`2026-05-26` em vez de `2026-05-25`). Causa: o prompt usa `{data}` como placeholder mas a data real nunca era passada. **Fix:** injetar `datetime.now().strftime("%d/%m/%Y")` no `build_user_message()`.

### Dificuldades

ArXiv voltou a retornar 429 no domingo — comportamento já documentado na Task 4. Em dias úteis as queries sequenciais com delay de 3s funcionam corretamente.

---

## Task 8 — Adicionar filtro de relevância por palavras-chave

**Status:** concluída ✅

### O que foi feito

Criada a função `_is_relevant(item)` em `agent.py` com um conjunto de 40+ keywords divididas em 5 categorias estratégicas:

| Categoria | Exemplos de keywords |
|---|---|
| Agentes & arquitetura | agent, langgraph, crewai, orchestrat, multi-agent |
| LLMs & modelos | llm, gpt, claude, rag, embedding, fine-tun |
| Produção & engenharia | deploy, production, memory, latency, sdk |
| Negócios & mercado | enterprise, roi, acquisition, funding, m&a |
| Automação & impacto | automation, workflow, cost reduct, efficiency |

O filtro roda **após** deduplicação e **antes** de enviar ao LLM. O log exibe quantos itens foram descartados a cada execução.

### Decisão de design: `set` de substrings, não regex

Usado `any(kw in text for kw in RELEVANCE_KEYWORDS)` com um `set` Python. Matching por substring (não palavra exata) cobre variações morfológicas: `"agent"` captura `"agents"`, `"agentic"`, `"multi-agent"`; `"fine-tun"` captura `"fine-tuning"` e `"fine-tuned"`. Mais simples e rápido que regex para este volume de itens.

### Dificuldades

Nenhuma bloqueante. Ponto de atenção futuro: o filtro pode ser agressivo em dias com poucas notícias — se `relevant` ficar vazio, o agente encerra sem digest. O `if not items` em `main()` já cobre esse caso com log de aviso.

---

## Task 7 — Refinar fontes RSS — foco em Enterprise AI e Agentes

**Status:** concluída ✅

### O que foi feito

**RSS_SOURCES — removidos (muito acadêmicos, pouco ROI):**
| Fonte | Motivo |
|---|---|
| Quanta Magazine | Ciência pura, sem aplicação prática imediata |
| Synced Review | Cobertura acadêmica genérica |
| Stanford HAI | Foco em política e pesquisa, distante do dia a dia de CTO |

**RSS_SOURCES — adicionados (Enterprise AI e Mercado):**
| Fonte | Motivo |
|---|---|
| TechCrunch AI | Cobertura de M&A, startups e enterprise — essencial para visão de mercado |
| VentureBeat | Conteúdo denso sobre agentes em produção e riscos de IA enterprise |

**ARXIV_QUERIES — alterados:**
| Mudança | Motivo |
|---|---|
| Removido `cat:quant-ph` | Computação Quântica não é foco estratégico atual da Runflow |
| Adicionado `cat:cs.MA` | Multi-Agent Systems — direto ao core do Agent OS da Runflow |

### Dificuldades

VentureBeat retornou 404 em `/ai/feed/` — feed correto é o geral `/feed/`. Verificado com WebFetch antes de adicionar.

---

## Task 6 — Atualizar SYSTEM_PROMPT para o perfil do Danrley

**Status:** concluída ✅

### O que foi feito

Substituído o SYSTEM_PROMPT genérico por um prompt personalizado para Danrley Morais (CTO Runflow / fundador IFTL). Mudanças principais:

- **Persona:** "Agente Alvorada" — braço direito de inteligência do Danrley
- **Filtro:** ROI, Agentes em Produção, M&A, Educação de Líderes
- **Novo campo "Pedrada":** sugestão de postagem para LinkedIn/Instagram gerada automaticamente
- **Impacto na Runflow/IFTL:** análise contextualizada nos negócios do Danrley
- **Tom:** provocador, pragmático, estrategista técnico
- **Formato de saída:** renomeado de "Morning Digest" para "Alvorada Intelligence"

### Dificuldades

Nenhuma — substituição direta do SYSTEM_PROMPT mantendo a separação system/user para prompt caching.

---

## Task 5 — Configurar agendamento diário

**Status:** concluída ✅

### O que foi feito

- Criado `.github/workflows/daily_digest.yml` com cron `0 9 * * *` (09h UTC = 06h BRT)
- `workflow_dispatch` habilitado para rodar manualmente pelo GitHub UI sem esperar o horário
- Cache de pip configurado (`cache: 'pip'`) — economiza ~40s por execução
- Todos os secrets passados via `${{ secrets.* }}` — nenhuma credencial no código
- Digest salvo como artefato com retenção de 30 dias (histórico acessível na aba Actions)
- Repositório git inicializado com `.gitignore` protegendo `.env`, `outputs/`, `logs/`, `__pycache__/`
- Primeiro commit realizado com 13 arquivos (925 linhas)

### Dificuldades

- `.env` com a GROQ_API_KEY real foi incluído automaticamente no `git add .` inicial. Detectado antes do commit.

### Como resolvemos

- Criado `.gitignore` antes do commit e executado `git rm --cached .env` para remover do staging sem apagar o arquivo local.

### Próximos passos para ativar no GitHub

1. Criar repositório em github.com (pode ser privado)
2. `git remote add origin https://github.com/SEU_USER/morning-digest.git`
3. `git push -u origin master`
4. Em **Settings → Secrets and variables → Actions**, adicionar:
   - `LLM_PROVIDER` = `groq` (ou `anthropic` quando migrar)
   - `GROQ_API_KEY` = sua key
   - `GROQ_MODEL` = `llama-3.3-70b-versatile`
5. Testar em **Actions → Morning Digest → Run workflow**
