"""
main.py — Entrypoint Streamlit do OAB Lead Qualifier.
Orquestra upload → enriquecimento paralelo → score → dashboard.
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
from storage import save_leads, load_leads

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="OAB Lead Qualifier",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
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

    /* ── Botões ──────────────────────────────────────────────── */
    .stButton > button {
        border-radius: 8px !important;
        background: #1E3050 !important;
        color: #F1F5F9 !important;
        border: 1px solid #2D4A6E !important;
        font-weight: 600 !important;
        padding: 8px 16px !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
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


def _enrich_lead(lead_dict: dict) -> dict:
    """
    Enriquece um único lead com todos os módulos em paralelo.
    Executado dentro de um ThreadPoolExecutor.
    """
    bio = lead_dict.get("bio", "")
    external_url = lead_dict.get("external_url", "")
    phone_full = lead_dict.get("phone_full", "")
    username = lead_dict.get("username", "")
    full_name = lead_dict.get("full_name_normalizado", lead_dict.get("full_name", ""))
    city = lead_dict.get("city", "")

    # bio_parser — sem API, instantâneo
    bio_data = parse_bio(bio, external_url=external_url, phone_full=phone_full, username=username)

    # Módulos com API — rodar em paralelo
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        fut_oab = ex.submit(lookup_oab, full_name, city)
        fut_site = ex.submit(check_site, external_url, full_name, city)
        oab_data = fut_oab.result()
        site_data = fut_site.result()

    enriched = {**lead_dict, **bio_data, **oab_data, **site_data}

    # Stub CNPJ e GMB (módulos v0.2) — valores neutros para não penalizar
    enriched.setdefault("cnpj_numero", "")
    enriched.setdefault("cnpj_situacao", "")
    enriched.setdefault("cnpj_cnae_juridico", False)
    enriched.setdefault("cnpj_razao_social", "")
    enriched.setdefault("gmb_encontrado", False)
    enriched.setdefault("gmb_reviews", 0)

    return calcular_score(enriched)


# ── Tela 1 — Upload ───────────────────────────────────────────────────────────
def tela_upload():
    st.markdown(
        """
        <div style="text-align:center;padding:60px 20px 30px">
            <div style="display:inline-block;background:#162032;border:1px solid #2D4A6E;border-radius:16px;padding:40px 60px;box-shadow:0 8px 32px rgba(0,0,0,0.4)">
                <div style="font-size:3rem;margin-bottom:12px">⚖️</div>
                <h1 style="color:#F1F5F9;font-size:2.4rem;margin:0 0 8px;font-weight:800;letter-spacing:-0.5px">OAB Lead Qualifier</h1>
                <p style="color:#94A3B8;font-size:1.1rem;margin:0">
                    Qualifique seus leads de advogados em segundos
                </p>
            </div>
        </div>
        """,
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
            st.session_state["tela"] = "processando"
            st.rerun()

        st.caption("Suporta exportações do Growman IG · Dados são processados localmente")


# ── Tela 2 — Processando ─────────────────────────────────────────────────────
def tela_processando():
    st.markdown(
        "<h2 style='color:#F1F5F9;font-weight:700'>⏳ Processando leads...</h2>",
        unsafe_allow_html=True,
    )

    uploaded = st.session_state.get("uploaded_file")
    if not uploaded:
        st.session_state["tela"] = "upload"
        st.rerun()
        return

    try:
        df, stats = parse_growman_xlsx(uploaded)
    except ValueError as e:
        st.error(f"Erro ao ler o arquivo: {e}")
        if st.button("Tentar novamente"):
            st.session_state["tela"] = "upload"
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
        st.warning("Nenhum advogado encontrado no arquivo. Verifique se as colunas estão no formato Growman.")
        if st.button("Voltar"):
            st.session_state["tela"] = "upload"
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
        except Exception as ex:
            # Nunca crashar — retornar lead com score 0
            enriched = {**lead, "score": 0, "classificacao": "❄️ Frio",
                        "insight": "Erro no processamento.", "criterios_aplicados": []}

        leads_processados.append(enriched)

        # Preview dos primeiros 5
        if i < 5:
            cls = enriched.get("classificacao", "")
            score = enriched.get("score", 0)
            nicho = enriched.get("nicho", "")
            with preview_container:
                st.markdown(
                    f"✓ **{nome}** · {nicho} · Score **{score}** · {cls}",
                    unsafe_allow_html=False,
                )

    progress.progress(1.0, text="Concluído!")
    status_box.empty()

    st.session_state["leads"] = leads_processados
    st.session_state["tela"] = "dashboard"
    st.rerun()


# ── Roteador principal ────────────────────────────────────────────────────────
def main():
    if "tela" not in st.session_state:
        # Auto-carregar leads salvos do projeto (para equipe acessar sem upload)
        leads_salvos = load_leads()
        if leads_salvos:
            st.session_state["leads"] = leads_salvos
            st.session_state["tela"] = "dashboard"
            st.session_state["leads_do_arquivo"] = True
        else:
            st.session_state["tela"] = "upload"

    tela = st.session_state["tela"]

    if tela == "upload":
        tela_upload()
    elif tela == "processando":
        tela_processando()
    elif tela == "dashboard":
        leads = st.session_state.get("leads", [])
        if not leads:
            st.session_state["tela"] = "upload"
            st.rerun()
        else:
            with st.sidebar:
                # Salvar para equipe (gera data/leads.json para commitar)
                st.markdown(
                    "<p style='color:#94A3B8;font-size:12px;font-weight:600;"
                    "text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px'>"
                    "Compartilhar</p>",
                    unsafe_allow_html=True,
                )
                if st.button("💾 Salvar para equipe", use_container_width=True):
                    try:
                        save_leads(leads)
                        st.success("Salvo! Faça git push para a equipe ver.", icon="✅")
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

                st.divider()
                if st.button("⬅️ Novo upload", use_container_width=True):
                    st.session_state["tela"] = "upload"
                    st.session_state.pop("leads", None)
                    st.session_state.pop("uploaded_file", None)
                    st.session_state.pop("leads_do_arquivo", None)
                    st.rerun()

            # Banner informativo se carregado do arquivo salvo
            if st.session_state.get("leads_do_arquivo"):
                st.info(
                    "📂 Exibindo leads salvos do projeto. "
                    "Para processar novos leads, clique em **Novo upload** na barra lateral.",
                    icon="ℹ️",
                )

            render_dashboard(leads)


if __name__ == "__main__":
    main()
