"""
main.py — Entrypoint Streamlit do OAB Lead Qualifier.
CRM com dashboard principal + painéis por closer.
"""

import os
import concurrent.futures
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from upload import parse_growman_xlsx
from enrichment.bio_parser import parse_bio
from enrichment.oab_module import lookup_oab
from enrichment.site_checker import check_site
from scoring.engine import calcular_score
from ui.dashboard import render_dashboard
from ui.closer_panel import render_closer_panel
from storage import save_leads, load_leads, update_closer

CLOSERS = {
    "matheus":  "Matheus",
    "jonas":    "Jonas",
    "giovanne": "Giovanne",
}

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="OAB Lead Qualifier",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS customizado — dark theme Trust & Authority
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* ── Base ───────────────────────────────────────────────── */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', sans-serif !important;
        background-color: #0D1B2A !important;
        color: #F1F5F9 !important;
    }

    /* ── Header / topbar ────────────────────────────────────── */
    header[data-testid="stHeader"] {
        background-color: #0A1628 !important;
        border-bottom: 1px solid #1E3050;
    }

    /* ── Container principal ────────────────────────────────── */
    .block-container {
        max-width: 1280px !important;
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
    }

    /* ── Sidebar ────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background-color: #0A1628 !important;
        border-right: 1px solid #1E3050;
        min-width: 240px !important;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1rem !important;
    }

    /* Botões de navegação da sidebar */
    section[data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        border: none !important;
        color: #94A3B8 !important;
        font-weight: 500 !important;
        text-align: left !important;
        padding: 8px 12px !important;
        border-radius: 8px !important;
        width: 100% !important;
        transition: all 0.15s !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #162032 !important;
        color: #F1F5F9 !important;
        border: none !important;
    }

    /* ── Métricas ────────────────────────────────────────────── */
    div[data-testid="metric-container"] {
        background: #162032 !important;
        border: 1px solid #2D4A6E !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        transition: border-color 0.2s;
    }
    div[data-testid="metric-container"]:hover {
        border-color: #F59E0B !important;
    }
    div[data-testid="metric-container"] label {
        color: #94A3B8 !important;
        font-size: 13px !important;
        font-weight: 500 !important;
    }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #F1F5F9 !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
    }

    /* ── Expanders ───────────────────────────────────────────── */
    details {
        background: #162032 !important;
        border: 1px solid #2D4A6E !important;
        border-radius: 10px !important;
        margin-bottom: 10px !important;
        overflow: hidden;
    }
    details summary {
        padding: 14px 18px !important;
        color: #F1F5F9 !important;
        font-weight: 500 !important;
        cursor: pointer;
        background: #162032 !important;
    }
    details summary:hover {
        background: #1E3050 !important;
    }
    details[open] summary {
        border-bottom: 1px solid #2D4A6E;
    }
    details > div {
        padding: 16px 18px !important;
    }

    /* ── Botões principais ───────────────────────────────────── */
    .block-container .stButton > button {
        border-radius: 8px !important;
        background: #1E3050 !important;
        color: #F1F5F9 !important;
        border: 1px solid #2D4A6E !important;
        font-weight: 600 !important;
        padding: 8px 16px !important;
        transition: all 0.2s !important;
    }
    .block-container .stButton > button:hover {
        background: #F59E0B !important;
        color: #0A1628 !important;
        border-color: #F59E0B !important;
    }

    /* ── Link buttons ────────────────────────────────────────── */
    a[data-testid="stLinkButton"] {
        border-radius: 8px !important;
        background: #1E3050 !important;
        border: 1px solid #2D4A6E !important;
        color: #F1F5F9 !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
    }
    a[data-testid="stLinkButton"]:hover {
        background: #F59E0B !important;
        border-color: #F59E0B !important;
        color: #0A1628 !important;
    }

    /* ── File uploader ───────────────────────────────────────── */
    [data-testid="stFileUploaderDropzone"] {
        background: #162032 !important;
        border: 2px dashed #2D4A6E !important;
        border-radius: 12px !important;
        transition: border-color 0.2s;
    }
    [data-testid="stFileUploaderDropzone"]:hover {
        border-color: #F59E0B !important;
    }
    [data-testid="stFileUploaderDropzone"] p,
    [data-testid="stFileUploaderDropzone"] span,
    [data-testid="stFileUploaderDropzone"] small {
        color: #94A3B8 !important;
    }

    /* ── Selectbox ───────────────────────────────────────────── */
    [data-testid="stSelectbox"] > div > div {
        background: #162032 !important;
        border: 1px solid #2D4A6E !important;
        border-radius: 8px !important;
        color: #F1F5F9 !important;
    }

    /* ── Checkbox ────────────────────────────────────────────── */
    [data-testid="stCheckbox"] label {
        color: #F1F5F9 !important;
    }

    /* ── Download button ─────────────────────────────────────── */
    [data-testid="stDownloadButton"] > button {
        background: #F59E0B !important;
        color: #0A1628 !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
    }
    [data-testid="stDownloadButton"] > button:hover {
        background: #D97706 !important;
        color: #0A1628 !important;
    }

    /* ── Progress bar ────────────────────────────────────────── */
    [data-testid="stProgressBar"] > div > div {
        background: linear-gradient(90deg, #F59E0B, #EF4444) !important;
        border-radius: 4px !important;
    }

    /* ── Info / warning / error boxes ───────────────────────── */
    [data-testid="stAlert"] {
        border-radius: 10px !important;
        border-left-width: 4px !important;
    }
    div[data-baseweb="notification"] {
        background: #162032 !important;
        border-color: #F59E0B !important;
    }

    /* ── Divider ─────────────────────────────────────────────── */
    hr {
        border-color: #2D4A6E !important;
        margin: 16px 0 !important;
    }

    /* ── Caption / small text ────────────────────────────────── */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: #64748B !important;
    }

    /* ── Scrollbar ───────────────────────────────────────────── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0D1B2A; }
    ::-webkit-scrollbar-thumb { background: #2D4A6E; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #F59E0B; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Enriquecimento de lead ────────────────────────────────────────────────────
def _enrich_lead(lead_dict: dict) -> dict:
    bio = lead_dict.get("bio", "")
    external_url = lead_dict.get("external_url", "")
    phone_full = lead_dict.get("phone_full", "")
    username = lead_dict.get("username", "")
    full_name = lead_dict.get("full_name_normalizado", lead_dict.get("full_name", ""))
    city = lead_dict.get("city", "")

    bio_data = parse_bio(bio, external_url=external_url, phone_full=phone_full, username=username)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        fut_oab = ex.submit(lookup_oab, full_name, city)
        fut_site = ex.submit(check_site, external_url, full_name, city)
        oab_data = fut_oab.result()
        site_data = fut_site.result()

    enriched = {**lead_dict, **bio_data, **oab_data, **site_data}
    enriched.setdefault("cnpj_numero", "")
    enriched.setdefault("cnpj_situacao", "")
    enriched.setdefault("cnpj_cnae_juridico", False)
    enriched.setdefault("cnpj_razao_social", "")
    enriched.setdefault("gmb_encontrado", False)
    enriched.setdefault("gmb_reviews", 0)
    enriched.setdefault("closer", "")

    return calcular_score(enriched)


# ── Sidebar de navegação (sempre visível) ─────────────────────────────────────
def render_sidebar(leads: list[dict], pagina: str):
    disponiveis = sum(1 for l in leads if not l.get("closer"))

    with st.sidebar:
        st.markdown(
            "<div style='padding:8px 4px 16px'>"
            "<span style='font-size:1.4rem'>⚖️</span> "
            "<span style='font-size:1rem;font-weight:800;color:#F1F5F9'>OAB Lead Qualifier</span>"
            "</div>",
            unsafe_allow_html=True,
        )

        # ── Dashboard principal ──
        ativo_dash = pagina == "dashboard"
        _nav_btn(
            f"{'▶ ' if ativo_dash else ''}📊 Dashboard ({disponiveis})",
            "dashboard", ativo_dash,
        )

        st.markdown(
            "<p style='color:#64748B;font-size:11px;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.8px;margin:16px 4px 6px'>Closers</p>",
            unsafe_allow_html=True,
        )

        # ── Painel de cada closer ──
        for slug, nome in CLOSERS.items():
            count = sum(1 for l in leads if l.get("closer") == slug)
            ativo = pagina == f"closer_{slug}"
            _nav_btn(
                f"{'▶ ' if ativo else ''}👤 {nome} ({count})",
                f"closer_{slug}", ativo,
            )

        st.divider()

        # ── Upload / Admin ──
        ativo_up = pagina == "upload"
        _nav_btn(
            f"{'▶ ' if ativo_up else ''}⬆️ Upload / Admin",
            "upload", ativo_up,
        )

        st.divider()
        st.markdown(
            "<p style='color:#64748B;font-size:11px;text-align:center'>"
            "💾 Dados salvos automaticamente</p>",
            unsafe_allow_html=True,
        )


def _nav_btn(label: str, pagina_destino: str, ativo: bool):
    """Botão de navegação da sidebar — muda de página ao clicar."""
    style = (
        "background:#162032!important;color:#F1F5F9!important;"
        "border:1px solid #2D4A6E!important;font-weight:700!important;"
        if ativo else ""
    )
    # Injetar estilo inline via container
    if ativo:
        st.markdown(
            f"<style>#btn_{pagina_destino.replace('-','_')} button"
            f"{{background:#162032!important;color:#F59E0B!important;"
            f"border:1px solid #F59E0B!important;font-weight:700!important}}</style>"
            f"<span id='btn_{pagina_destino.replace('-','_')}'></span>",
            unsafe_allow_html=True,
        )
    if st.button(label, use_container_width=True, key=f"nav_{pagina_destino}"):
        st.session_state["pagina"] = pagina_destino
        st.rerun()


# ── Tela Upload / Admin ───────────────────────────────────────────────────────
def tela_upload_admin(leads: list[dict]):
    # Stats dos leads atuais
    if leads:
        total = len(leads)
        disponiveis = sum(1 for l in leads if not l.get("closer"))
        atribuidos = total - disponiveis
        st.markdown(
            "<h3 style='color:#F1F5F9;font-weight:700;margin-bottom:16px'>Base de leads atual</h3>",
            unsafe_allow_html=True,
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total de leads", total)
        c2.metric("Disponíveis", disponiveis)
        c3.metric("Atribuídos", atribuidos)
        c4.metric(
            "Closers ativos",
            len([s for s in CLOSERS if any(l.get("closer") == s for l in leads)]),
        )
        st.divider()

    # Upload de nova base
    st.markdown(
        "<h3 style='color:#F1F5F9;font-weight:700;margin-bottom:4px'>Enviar nova planilha</h3>"
        "<p style='color:#94A3B8;margin-bottom:20px'>Um novo upload substitui toda a base atual "
        "e reseta as atribuições dos closers.</p>",
        unsafe_allow_html=True,
    )

    col = st.columns([1, 2, 1])[1]
    with col:
        uploaded = st.file_uploader(
            "Arraste o .xlsx do Growman aqui",
            type=["xlsx"],
            help="Exportação padrão do Growman — aba 'contacts'",
        )
        if uploaded:
            st.session_state["uploaded_file"] = uploaded
            st.session_state["pagina"] = "processando"
            st.rerun()
        st.caption("Suporta exportações do Growman IG · Dados são processados localmente")


# ── Tela Processando ──────────────────────────────────────────────────────────
def tela_processando():
    st.markdown(
        "<h2 style='color:#F1F5F9;font-weight:700'>⏳ Processando leads...</h2>",
        unsafe_allow_html=True,
    )

    uploaded = st.session_state.get("uploaded_file")
    if not uploaded:
        st.session_state["pagina"] = "upload"
        st.rerun()
        return

    try:
        df, stats = parse_growman_xlsx(uploaded)
    except ValueError as e:
        st.error(f"Erro ao ler o arquivo: {e}")
        if st.button("Tentar novamente"):
            st.session_state["pagina"] = "upload"
            st.rerun()
        return

    st.info(
        f"📊 {stats['total_bruto']} registros no arquivo · "
        f"{stats.get('apos_filtro_privado', '?')} públicos · "
        f"**{stats['advogados']} advogados detectados**"
    )

    leads_raw = df.to_dict("records")
    total = len(leads_raw)

    if total == 0:
        st.warning("Nenhum advogado encontrado. Verifique se o arquivo é do Growman.")
        if st.button("Voltar"):
            st.session_state["pagina"] = "upload"
            st.rerun()
        return

    progress = st.progress(0, text="Iniciando...")
    status_box = st.empty()
    preview_container = st.container()
    leads_processados = []

    for i, lead in enumerate(leads_raw):
        pct = i / total
        nome = lead.get("full_name", lead.get("username", f"Lead {i+1}"))
        progress.progress(pct, text=f"Processando {i+1}/{total} — {nome}")
        status_box.caption(f"⚡ Enriquecendo: {nome}")

        try:
            enriched = _enrich_lead(lead)
        except Exception:
            enriched = {**lead, "score": 0, "classificacao": "❄️ Frio",
                        "insight": "Erro no processamento.", "criterios_aplicados": [],
                        "closer": ""}

        leads_processados.append(enriched)

        if i < 5:
            cls = enriched.get("classificacao", "")
            score = enriched.get("score", 0)
            nicho = enriched.get("nicho", "")
            with preview_container:
                st.markdown(f"✓ **{nome}** · {nicho} · Score **{score}** · {cls}")

    progress.progress(1.0, text="Concluído!")
    status_box.empty()

    st.session_state["leads"] = leads_processados
    st.session_state["pagina"] = "dashboard"
    # Salvar automaticamente ao processar
    save_leads(leads_processados)
    st.rerun()


# ── Roteador principal ────────────────────────────────────────────────────────
def main():
    # ── Processar atribuição pendente (event-first) ──
    if "assign_action" in st.session_state:
        action = st.session_state.pop("assign_action")
        username = action["username"]
        closer   = action["closer"]
        # Gravar só esse lead no banco — não reescreve tudo
        update_closer(username, closer)
        # Sincronizar session_state
        for lead in st.session_state.get("leads", []):
            if lead.get("username") == username:
                lead["closer"] = closer
                break

    # ── Carregar leads na inicialização ──
    if "leads" not in st.session_state:
        carregados = load_leads()
        st.session_state["leads"] = carregados or []

    # ── Página padrão ──
    if "pagina" not in st.session_state:
        st.session_state["pagina"] = "dashboard" if st.session_state["leads"] else "upload"

    leads = st.session_state["leads"]
    pagina = st.session_state["pagina"]

    # ── Sidebar (sempre visível, exceto durante processamento) ──
    if pagina != "processando":
        render_sidebar(leads, pagina)

    # ── Roteamento ──
    if pagina == "upload":
        tela_upload_admin(leads)
    elif pagina == "processando":
        tela_processando()
    elif pagina == "dashboard":
        render_dashboard(leads)
    elif pagina.startswith("closer_"):
        closer_slug = pagina.replace("closer_", "")
        closer_nome = CLOSERS.get(closer_slug, closer_slug.capitalize())
        render_closer_panel(leads, closer_slug, closer_nome)


if __name__ == "__main__":
    main()
