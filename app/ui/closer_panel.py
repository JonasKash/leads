"""
closer_panel.py — Painel de leads atribuídos a um closer específico.
"""

import streamlit as st
from ui.lead_card import render_lead_card


def render_closer_panel(leads: list[dict], closer_slug: str, closer_nome: str):
    """Renderiza o painel de um closer com seus leads atribuídos."""

    leads_closer = sorted(
        [l for l in leads if l.get("closer") == closer_slug],
        key=lambda x: x.get("score", 0),
        reverse=True,
    )

    total = len(leads_closer)
    quentes = sum(1 for l in leads_closer if "Quente" in str(l.get("classificacao", "")))
    com_contato = sum(
        1 for l in leads_closer
        if l.get("phone_full") or l.get("phone_from_bio") or l.get("email")
    )

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        f"<h2 style='color:#F1F5F9;font-weight:800;letter-spacing:-0.5px;margin-bottom:4px'>"
        f"👤 {closer_nome}</h2>"
        f"<p style='color:#64748B;margin-bottom:20px'>Leads atribuídos para abordagem</p>",
        unsafe_allow_html=True,
    )

    # ── Métricas ──────────────────────────────────────────────────────────────
    m1, m2, m3 = st.columns(3)
    m1.metric("Total atribuídos", total)
    m2.metric("🔥 Quentes", quentes)
    m3.metric("📱 Com contato", com_contato)

    st.divider()

    # ── Lista vazia ───────────────────────────────────────────────────────────
    if total == 0:
        st.markdown(
            "<div style='text-align:center;padding:60px 20px;color:#64748B'>"
            "<div style='font-size:3rem;margin-bottom:12px'>📭</div>"
            "<h3 style='color:#94A3B8;margin-bottom:8px'>Nenhum lead atribuído ainda</h3>"
            "<p>Vá ao Dashboard Principal e atribua leads para este closer.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    # ── Cards ─────────────────────────────────────────────────────────────────
    for lead in leads_closer:
        username = lead.get("username", "")

        render_lead_card(lead, show_assign=False)

        # Botão devolver — fora do expander, logo abaixo do card
        col_dev, col_esp = st.columns([1, 4])
        with col_dev:
            if st.button(
                "⮐ Devolver ao pool",
                key=f"devolver_{username}",
                use_container_width=True,
            ):
                st.session_state["assign_action"] = {"username": username, "closer": ""}
                st.rerun()
