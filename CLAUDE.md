# OAB Lead Qualifier — CLAUDE.md
> Guia de comportamento, arquitetura e skills para o Claude Code neste projeto.
> Leia este arquivo inteiro antes de escrever qualquer linha de código.

---

## 🎯 O que é este projeto

SaaS de qualificação automática de leads para advogados brasileiros.
O usuário faz upload de um `.xlsx` exportado pelo **Growman** (extrator de seguidores do Instagram),
e o sistema enriquece cada lead com dados públicos, classifica em **Quente / Morno / Frio**
e exibe um dashboard interativo pronto para abordagem comercial.

**Público-alvo dos leads:** Advogados ativos no Instagram, preferencialmente com nicho
(Previdenciário, Trabalhista, Família, Criminal, Empresarial).

**Produto a ser vendido para esses leads:** Mentorias, cursos e consultoria de presença digital
jurídica.

---

## 📁 Estrutura do projeto

```
oab-lead-saas/
├── CLAUDE.md                  ← este arquivo
├── .env.example               ← variáveis de ambiente necessárias
├── requirements.txt
├── app/
│   ├── main.py                ← entrypoint Streamlit
│   ├── upload.py              ← parser do XLSX do Growman
│   ├── enrichment/
│   │   ├── __init__.py
│   │   ├── bio_parser.py      ← extrai nicho, link, telefone da bio
│   │   ├── oab_module.py      ← consulta CNA público
│   │   ├── cnpj_module.py     ← Google CSE + ReceitaWS
│   │   ├── site_checker.py    ← verifica site, pixel FB/GA, PageSpeed
│   │   └── google_meu_negocio.py ← verifica GMB via Google Places API
│   ├── scoring/
│   │   ├── __init__.py
│   │   └── engine.py          ← motor de score e classificação
│   └── ui/
│       ├── dashboard.py       ← tabela interativa de leads
│       └── lead_card.py       ← card expandido de cada lead
├── .claude/
│   └── skills/                ← skills instaladas (ver seção Skills abaixo)
└── design-system/
    └── MASTER.md              ← gerado pelo ui-ux-pro-max após setup
```

---

## 🗂️ Formato do arquivo Growman (XLSX)

O Growman exporta um arquivo `.xlsx` com aba `contacts` e as seguintes colunas
(mapeamento obrigatório — não altere os nomes internos):

| Coluna Growman        | Campo interno         | Uso                              |
|-----------------------|-----------------------|----------------------------------|
| Instagram ID          | `ig_id`               | Identificador único              |
| Username              | `username`            | @ do Instagram                   |
| Full name             | `full_name`           | Nome para busca OAB/CNPJ         |
| Profile link          | `profile_url`         | Link direto do perfil            |
| Avatar pic            | `avatar_url`          | Foto de perfil (display)         |
| Followers count       | `followers`           | Volume de audiência              |
| Following count       | `following`           | Ratio seguidor/seguindo          |
| Biography             | `bio`                 | Fonte principal de dados         |
| Category              | `ig_category`         | Categoria IG (ex: Music Producer)|
| Public email          | `email`               | Email público extraído pelo Growman|
| Posts count           | `posts`               | Atividade do perfil              |
| Phone country code    | `phone_code`          | DDI                              |
| Phone number          | `phone`               | Telefone/WhatsApp                |
| City                  | `city`                | Cidade declarada                 |
| Address               | `address`             | Endereço (raro)                  |
| Is private            | `is_private`          | Perfil privado? (filtrar fora)   |
| Is business           | `is_business`         | Conta comercial IG               |
| External url          | `external_url`        | Link na bio (linktree, site etc) |
| Is verified           | `is_verified`         | Conta verificada                 |
| Followed by viewer    | `followed_by_viewer`  | Já é seguidor                    |

**Regras de parsing:**
- Ignorar linhas onde `is_private == "YES"` (não dá pra ver o perfil)
- Filtrar apenas advogados: `bio` deve conter pelo menos um dos termos:
  `adv`, `advogad`, `OAB`, `direito`, `jurídico`, `advocaci`, `Dr.`, `Dra.`
- Normalizar `full_name`: remover emojis, pipes, separadores antes de buscar OAB/CNPJ

---

## 🔬 Pipeline de Enriquecimento

Cada lead passa pelos seguintes módulos **em paralelo** (usar `asyncio` ou `ThreadPoolExecutor`):

### 1. `bio_parser.py` — Análise da bio (sem API, instantâneo)
- Detectar **nicho jurídico** via regex/keywords:
  - Previdenciário, Trabalhista, Família, Criminal, Empresarial, Imobiliário, Tributário
- Detectar **link na bio** (External url preenchido = tem link)
- Detectar **call-to-action** na bio: "agende", "marque", "clique", "whatsapp", "consulta"
- Detectar **menção a escritório** (@handle diferente do próprio)
- Extrair **telefone** da bio se diferente do campo Phone

### 2. `oab_module.py` — Consulta CNA (API pública OAB)
- Endpoint: `https://cna.oab.org.br/api/advogados?nome={nome}&uf={uf}`
- Retornar: número OAB, seccional, subseção, situação (ATIVO/SUSPENSO/CANCELADO),
  tipo de inscrição, data de inscrição
- **Calcular tempo de OAB ativo** em anos a partir da data de inscrição
- Rate limit seguro: 1 req/segundo
- Fallback: se nome com acentos falhar, tentar sem acentos (unidecode)

### 3. `cnpj_module.py` — Busca CNPJ
- Google Custom Search: `"{nome}" CNPJ advogado`
- Validar via ReceitaWS: `https://receitaws.com.br/v1/cnpj/{cnpj}`
- Verificar se CNPJ é de escritório (CNAE 6911/6912/6920/6922)
- Retornar: CNPJ formatado, razão social, situação, município/UF, email/telefone do CNPJ

### 4. `site_checker.py` — Análise do site
- Se `external_url` preenchido → usar direto
- Senão → Google CSE: `"{nome}" advogado site`
- No site encontrado verificar:
  - **Pixel do Facebook**: buscar `fbq(`, `facebook.net/en_US/fbevents.js`
  - **Google Analytics/Tag Manager**: buscar `gtag(`, `UA-`, `G-`, `GTM-`
  - **Google Ads**: buscar `AW-`
  - **PageSpeed Score**: via `https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&strategy=mobile`
- Retornar score de presença digital (0-100)

### 5. `google_meu_negocio.py` — Google Meu Negócio
- Google Places API Text Search: `"{nome}" advogado {cidade}`
- Verificar se há listing ativo com avaliações
- Retornar: rating, total de reviews, endereço confirmado, telefone GMB

---

## 🏆 Motor de Score (`scoring/engine.py`)

### Critérios e pesos

```python
CRITERIOS = {
    # OAB
    "oab_ativo":              30,   # OAB com situação ATIVO
    "oab_recente_1_3anos":    15,   # inscrito há 1-3 anos (mais receptivo)
    "oab_senior_10anos":      -5,   # >10 anos pode já ter estrutura

    # CNPJ
    "cnpj_ativo_juridico":    20,   # CNPJ de escritório ativo
    "cnpj_ativo_generico":    10,   # CNPJ ativo mas não jurídico
    "sem_cnpj":               15,   # sem estrutura = oportunidade

    # Presença digital (quanto MENOS, maior a oportunidade de venda)
    "sem_site":               20,   # sem site = venda fácil
    "site_sem_pixel":         15,   # tem site mas sem rastreamento
    "site_com_pixel":         -10,  # já investe em marketing digital
    "sem_gmb":                10,   # sem GMB = oportunidade
    "gmb_ativo_semreviews":   5,    # tem GMB mas fraco
    "gmb_forte":              -15,  # bem posicionado = não precisa

    # Instagram
    "sem_link_na_bio":        15,   # não tem link = oportunidade
    "cta_na_bio_sem_link":    20,   # tem CTA mas sem link = frustração = venda
    "followers_500_5k":       10,   # audiência em crescimento
    "conta_business":         5,    # já tem conta profissional
    "email_disponivel":       5,    # tem email = contato direto
    "telefone_disponivel":    10,   # tem WhatsApp = contato direto
}
```

### Classificação final

```python
def classificar(score: int) -> str:
    if score >= 70:
        return "🔥 Quente"
    elif score >= 45:
        return "🟡 Morno"
    else:
        return "❄️ Frio"
```

### Geração de insight personalizado
Para cada lead, gerar 1 frase de insight baseada nos dados:
- Exemplo: "Advogada previdenciária sem site e sem pixel — perfil ideal para mentoria de presença digital"
- Exemplo: "OAB ativo há 2 anos, sem GMB, CTA na bio sem link — oportunidade de conversão alta"

---

## 🖥️ Interface (Streamlit + UI UX Pro Max)

### Estilo visual
Este projeto é um **SaaS jurídico de qualificação**. O ui-ux-pro-max skill deve aplicar:
- **Estilo:** Trust & Authority + Minimal & Direct
- **Paleta:** Azul marinho profundo (#0A1628), branco, acentos em âmbar (#F59E0B)
- **Tipografia:** Inter (sans-serif limpa) — sem serifa, sem gradientes AI
- **Anti-padrões a evitar:** gradientes roxo/rosa de IA, glassmorphism excessivo, dark mode OLED

### Telas

#### Tela 1 — Upload
```
┌─────────────────────────────────────────┐
│  ⚖️  OAB Lead Qualifier                  │
│  Qualifique seus leads em segundos      │
│                                         │
│  [ Arraste o .xlsx do Growman aqui ]    │
│  ou clique para selecionar              │
│                                         │
│  Suporta exportações do Growman IG      │
└─────────────────────────────────────────┘
```

#### Tela 2 — Processando
- Barra de progresso com etapa atual por lead
- Contador: "Processando 12/56 leads..."
- Preview dos primeiros leads já processados (streaming)

#### Tela 3 — Dashboard
- Filtros no topo: Classificação | Nicho | Com Email | Com Telefone | Com Site
- Métricas resumo: Total | Quentes | Mornos | Frios | Com contato direto
- Tabela com colunas:
  - Avatar | Nome | @ | Nicho | Score | Classificação | OAB | CNPJ | Site | Pixel | Contato
- Cada linha expansível → Lead Card completo
- Botão "Exportar CSV filtrado"

#### Lead Card (expandido)
```
┌──────────────────────────────────────────────────────┐
│ 🔥 Quente — Score 87/100                             │
│ ─────────────────────────────────────────────────    │
│ @sablinacastro  |  Sablina Castro                    │
│ ⚖️ Previdenciário  |  1.676 seguidores               │
│                                                      │
│ OAB: ████ SP — ATIVO (2 anos)                        │
│ CNPJ: Castro Rigueira Advocacia — ATIVA              │
│ Site: Não encontrado                +20pts           │
│ Pixel: Não instalado               +15pts            │
│ GMB: Não cadastrado                +10pts            │
│ Bio: CTA "Agende" sem link         +20pts            │
│                                                      │
│ 📱 31982424656  |  ✉️ sablina.castro@hotmail.com     │
│                                                      │
│ 💡 Advogada previdenciária com OAB recente,          │
│    sem site e sem pixel — perfil ideal para          │
│    mentoria de presença digital jurídica.            │
│                                                      │
│ [ Copiar WhatsApp ]  [ Copiar Email ]  [ Ver IG ]   │
└──────────────────────────────────────────────────────┘
```

---

## 🛠️ Stack técnica

```
Backend:   Python 3.11+
Frontend:  Streamlit (MVP) → Next.js (v2)
APIs:      Google Custom Search, ReceitaWS, Google Places, PageSpeed
Async:     asyncio + aiohttp para enriquecimento paralelo
Export:    pandas → CSV / XLSX
Env:       python-dotenv
```

---

## 🔑 Variáveis de ambiente (.env)

```bash
# Google Custom Search (gratuito: 100 req/dia)
GOOGLE_API_KEY=sua_chave_aqui
GOOGLE_CSE_ID=seu_cse_id_aqui

# Google Places API (para GMB)
GOOGLE_PLACES_API_KEY=sua_chave_aqui  # pode ser a mesma do CSE

# Rate limits (segundos entre requests)
DELAY_GOOGLE=1.2
DELAY_RECEITAWS=0.8
DELAY_OAB=1.0
DELAY_PAGESPEED=0.5
```

---

## 📦 Skills instaladas neste projeto

### 1. UI UX Pro Max (design intelligence)
**Repo:** https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
**Instalação no Claude Code:**
```bash
/plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill
/plugin install ui-ux-pro-max@ui-ux-pro-max-skill
```
**Uso neste projeto:**
- Antes de criar qualquer componente de UI, rode:
  ```bash
  python3 .claude/skills/ui-ux-pro-max/scripts/search.py "legal SaaS jurídico qualificação leads" --design-system -p "OAB Lead Qualifier"
  ```
- Persista o design system:
  ```bash
  python3 .claude/skills/ui-ux-pro-max/scripts/search.py "legal SaaS" --design-system --persist -p "OABLeadQualifier"
  ```
- Sempre consulte `design-system/MASTER.md` antes de criar componentes novos.

### 2. Lead Research Assistant (lógica de enriquecimento)
**Repo:** https://github.com/ComposioHQ/awesome-claude-skills/tree/master/lead-research-assistant
**Uso neste projeto:**
- Aplicar os padrões de pesquisa paralela de leads definidos nesta skill
- Usar como referência para estrutura dos módulos de enriquecimento
- O pipeline de busca de dados públicos segue a arquitetura desta skill

### 3. MCP Builder (integrações futuras)
**Repo:** https://github.com/ComposioHQ/awesome-claude-skills/tree/master/mcp-builder
**Uso futuro:**
- Quando o projeto escalar para integração com CRM (HubSpot, Pipedrive)
- Para construir o conector Growman headless (Playwright + extensão embarcada)
- Webhooks de entrada de leads em tempo real

---

## ⚙️ Comandos de setup (rode na ordem)

```bash
# 1. Dependências Python
pip install streamlit pandas openpyxl aiohttp requests \
            python-dotenv unidecode beautifulsoup4 lxml

# 2. Copiar .env.example
cp .env.example .env
# (editar com suas chaves)

# 3. Instalar skill de UI
npm install -g uipro-cli
uipro init --ai claude

# 4. Gerar design system
python3 .claude/skills/ui-ux-pro-max/scripts/search.py \
  "legal SaaS lead qualification jurídico" \
  --design-system --persist -p "OABLeadQualifier"

# 5. Rodar o SaaS localmente
streamlit run app/main.py
```

---

## 🧠 Regras de comportamento do Claude Code neste projeto

### Sempre faça
- Ler `design-system/MASTER.md` antes de criar qualquer UI
- Usar `asyncio`/`ThreadPoolExecutor` para chamadas de API em paralelo
- Respeitar os delays de rate limit definidos no `.env`
- Logar progresso por lead com `st.progress()` e `st.status()`
- Tratar erros de API silenciosamente (retornar campo vazio, não crashar)
- Manter o score como inteiro de 0 a 100
- Gerar o insight de 1 frase para cada lead automaticamente

### Nunca faça
- Criar área de login ou autenticação (MVP sem auth)
- Usar dados privados ou não-públicos
- Fazer scraping sem delays entre requests
- Mostrar dados de CNPJs de pessoas físicas (apenas jurídicos/MEI)
- Bloquear a UI enquanto processa (sempre usar async/spinner)
- Hardcodar chaves de API no código (sempre usar `.env`)

### Prioridades de desenvolvimento
1. Upload do XLSX e parser do Growman (funciona hoje)
2. bio_parser (sem API — instantâneo)
3. oab_module (API pública — mais crítico para qualificação)
4. site_checker + pixel detector
5. cnpj_module (Google CSE + ReceitaWS)
6. google_meu_negocio
7. Dashboard e Lead Card
8. Export CSV filtrado

---

## 📊 Dados reais de referência (arquivo de teste)

O arquivo `follower-of-fredpataro-20260319.xlsx` tem **56 leads** com esta distribuição:
- 21 bios com termos jurídicos (advogados reais)
- 5 com email público
- 4 com telefone
- 14 com link externo (site/linktree)
- 9 contas Business

**Lead de exemplo real (Sablina Castro):**
```json
{
  "username": "sablinacastro",
  "full_name": "Sablina Castro",
  "followers": 1676,
  "bio": "⚖️ Advogada | @castro_rigueira\n📚 Especialista em Direito Previdenciário\n☎️ Agende sua consulta",
  "email": "sablina.castro@hotmail.com",
  "phone": "31982424656",
  "external_url": null,
  "is_business": "NO",
  "nicho_detectado": "Previdenciário",
  "cta_sem_link": true
}
```

---

## 🚀 Roadmap

### v0.1 — MVP Local (agora)
- Upload XLSX → bio_parser → OAB check → score → dashboard básico

### v0.2 — Enriquecimento completo
- Todos os módulos ativos + export CSV

### v0.3 — Automação Growman
- Input por @ do Instagram → Playwright headless com Growman embarcado

### v1.0 — SaaS público
- Deploy (Railway/Render) + auth simples + planos de uso
