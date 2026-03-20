# ⚖️ OAB Lead Qualifier

SaaS de qualificação automática de leads para advogados brasileiros. O sistema enriquece leads extraídos do Instagram (via Growman) com dados públicos (OAB, CNPJ, GMB, Sites) e classifica-os em **Quente / Morno / Frio** para abordagens comerciais eficientes.

---

## 🚀 Como Executar Localmente

### 1. Pré-requisitos
*   **Python 3.11 ou superior** instalado.
*   **Git** instalado.

### 2. Clonar ou Inicializar o Projeto
Se você já tem o código no seu computador:
1. Abra o terminal na pasta do projeto.
2. Crie um ambiente virtual (recomendado):
   ```bash
   python -m venv venv
   ```
3. Ative o ambiente virtual:
   *   **Windows:** `venv\Scripts\activate`
   *   **Linux/Mac:** `source venv/bin/activate`

### 3. Instalar Dependências
Com o ambiente virtual ativo, execute:
```bash
pip install -r requirements.txt
```

### 4. Configurar Variáveis de Ambiente
O projeto precisa de chaves de API para funcionar.
1. Renomeie o arquivo `.env.example` para `.env`:
   ```bash
   cp .env.example .env
   ```
2. Abra o arquivo `.env` e insira suas credenciais (Google API Key, Search Engine ID, etc.).

### 5. Rodar o Dashboard
Execute o comando do Streamlit:
```bash
streamlit run app/main.py
```
O sistema abrirá automaticamente no seu navegador em `http://localhost:8501`.

---

## 🌐 Como Colocar Online (Deploy)

### Passo 1: Subir para o GitHub
1. Crie um repositório no [GitHub](https://github.com/new).
2. No seu terminal, execute:
   ```bash
   git add .
   git commit -m "Setup inicial e documentação"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
   git push -u origin main
   ```

### Passo 2: Hospedar no Streamlit Cloud (Recomendado para o MVP)
1. Acesse [share.streamlit.io](https://share.streamlit.io/).
2. Conecte sua conta do GitHub.
3. Selecione o seu repositório `oab-lead-qualifier`.
4. **Main file path:** `app/main.py`.
5. **Configurações Importantes:**
   *   Vá em **Advanced Settings**.
   *   Em **Secrets**, copie e cole exatamente o que está no seu arquivo `.env`.
6. Clique em **Deploy**!

### Passo 3: Hospedar no Render (Opção v1.0)
1. No [Render.com](https://render.com/), crie um novo **Web Service**.
2. **Build Command:** `pip install -r requirements.txt`
3. **Start Command:** `streamlit run app/main.py --server.port $PORT --server.address 0.0.0.0`
4. Na aba **Environment**, adicione as chaves que estão no seu `.env`.

---

## 📁 Estrutura do Projeto
*   `app/main.py`: Ponto de entrada da aplicação.
*   `app/enrichment/`: Módulos de busca de dados (OAB, CNPJ, Sites).
*   `app/scoring/`: Motor de classificação de leads.
*   `app/ui/`: Componentes visuais do dashboard.
*   `CLAUDE.md`: Guia técnico detalhado para IA e desenvolvedores.

---

## 🛠️ Tecnologias Utilizadas
*   **Python:** Linguagem principal.
*   **Streamlit:** Framework para interface do usuário (UI).
*   **Pandas:** Manipulação de dados e arquivos XLSX.
*   **Aiohttp:** Requisições assíncronas para enriquecimento rápido.
