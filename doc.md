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

## Task 5 — Configurar agendamento diário

**Status:** pendente
