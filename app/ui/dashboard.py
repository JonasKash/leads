"""
dashboard.py — Tela 3: Dashboard interativo com tabela de leads filtráveis.
"""

import io
import pandas as pd
import streamlit as st
from ui.lead_card import render_lead_card


def _color_cls(val: str) -> str:
    if "Quente" in str(val):
        return "color: #EF4444; font-weight: 700"
    if "Morno" in str(val):
        return "color: #F59E0B; font-weight: 700"
    return "color: #3B82F6; font-weight: 700"


def render_dashboard(leads: list[dict]):
    """Renderiza o dashboard completo com filtros, métricas e tabela de leads."""

    st.markdown(
        "<h2 style='color:#F1F5F9;margin-bottom:4px;font-weight:800;letter-spacing:-0.5px'>Dashboard de Leads</h2>",
        unsafe_allow_html=True,
    )

    df = pd.DataFrame(leads)

    # ── Métricas resumo ───────────────────────────────────────────────────────
    total = len(df)
    quentes = df["classificacao"].str.contains("Quente").sum() if "classificacao" in df else 0
    mornos = df["classificacao"].str.contains("Morno").sum() if "classificacao" in df else 0
    frios = df["classificacao"].str.contains("Frio").sum() if "classificacao" in df else 0
    com_contato = df.apply(
        lambda r: bool(r.get("phone_full") or r.get("phone_from_bio") or r.get("email")),
        axis=1,
    ).sum()

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total", total)
    m2.metric("🔥 Quentes", quentes)
    m3.metric("🟡 Mornos", mornos)
    m4.metric("❄️ Frios", frios)
    m5.metric("📱 Com contato", com_contato)

    st.divider()

    # ── Filtros ───────────────────────────────────────────────────────────────
    f1, f2, f3, f4, f5 = st.columns(5)

    with f1:
        opcoes_cls = ["Todos"] + sorted(df["classificacao"].unique().tolist()) if "classificacao" in df else ["Todos"]
        filtro_cls = st.selectbox("Classificação", opcoes_cls)

    with f2:
        nichos = ["Todos"] + sorted(df["nicho"].unique().tolist()) if "nicho" in df else ["Todos"]
        filtro_nicho = st.selectbox("Nicho", nichos)

    with f3:
        filtro_email = st.checkbox("Com email")

    with f4:
        filtro_fone = st.checkbox("Com telefone")

    with f5:
        filtro_site = st.checkbox("Com site")

    # Aplicar filtros
    mask = pd.Series([True] * len(df), index=df.index)

    if filtro_cls != "Todos":
        mask &= df["classificacao"].str.contains(filtro_cls.replace("🔥 ", "").replace("🟡 ", "").replace("❄️ ", ""))

    if filtro_nicho != "Todos":
        mask &= df["nicho"] == filtro_nicho

    if filtro_email:
        mask &= df["email"].fillna("").astype(str).str.strip().ne("")

    if filtro_fone:
        mask &= (
            df.get("phone_full", pd.Series("")).fillna("").astype(str).str.strip().ne("") |
            df.get("phone_from_bio", pd.Series("")).fillna("").astype(str).str.strip().ne("")
        )

    if filtro_site:
        mask &= df.get("site_encontrado", pd.Series(False)).fillna(False)

    df_filtered = df[mask].copy()

    st.caption(f"Exibindo {len(df_filtered)} de {total} leads")

    # ── Exportar ──────────────────────────────────────────────────────────────
    if len(df_filtered) > 0:
        csv_buf = io.StringIO()
        export_cols = [
            "username", "full_name", "nicho", "score", "classificacao",
            "oab_numero", "oab_seccional", "oab_situacao", "oab_anos_ativo",
            "cnpj_numero", "cnpj_razao_social",
            "site_url", "has_fb_pixel", "has_ga",
            "email", "phone_full", "phone_from_bio",
            "followers", "profile_url", "insight",
        ]
        export_cols = [c for c in export_cols if c in df_filtered.columns]
        df_filtered[export_cols].to_csv(csv_buf, index=False, encoding="utf-8-sig")
        st.download_button(
            "⬇️ Exportar CSV filtrado",
            csv_buf.getvalue().encode("utf-8-sig"),
            file_name="leads_qualificados.csv",
            mime="text/csv",
        )

    st.divider()

    # ── Cards de leads ────────────────────────────────────────────────────────
    if len(df_filtered) == 0:
        st.info("Nenhum lead encontrado com os filtros selecionados.")
        return

    # Ordenar por score desc
    df_sorted = df_filtered.sort_values("score", ascending=False)

    for _, row in df_sorted.iterrows():
        render_lead_card(row.to_dict())
