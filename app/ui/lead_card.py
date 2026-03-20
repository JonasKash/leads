"""
lead_card.py — Card expandido de cada lead no dashboard.
"""

import base64
import requests
import streamlit as st
from functools import lru_cache

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.instagram.com/",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}


@lru_cache(maxsize=300)
def _avatar_data_uri(url: str) -> str:
    """Baixa a imagem com headers de browser e retorna data URI base64."""
    try:
        r = requests.get(url, headers=_HEADERS, timeout=6)
        if r.status_code == 200:
            ct = r.headers.get("Content-Type", "image/jpeg").split(";")[0]
            b64 = base64.b64encode(r.content).decode()
            return f"data:{ct};base64,{b64}"
    except Exception:
        pass
    return ""


def _badge(label: str, color: str) -> str:
    return f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600">{label}</span>'


def _classificacao_color(cls: str) -> str:
    if "Quente" in cls:
        return "#EF4444"
    if "Morno" in cls:
        return "#F59E0B"
    return "#3B82F6"


def render_lead_card(lead: dict):
    """Renderiza o card expandido de um lead dentro de um st.expander."""
    cls = lead.get("classificacao", "")
    score = lead.get("score", 0)
    color = _classificacao_color(cls)

    with st.expander(
        f"{cls}  ·  Score {score}/100  ·  @{lead.get('username', '')}  —  {lead.get('full_name', '')}",
        expanded=False,
    ):
        col1, col2 = st.columns([1, 3])

        with col1:
            avatar_url = str(lead.get("avatar_url", "")).strip()
            username = lead.get("username", "")
            initial = (lead.get("full_name") or username or "?")[0].upper()
            fallback_html = (
                f'<div style="width:80px;height:80px;border-radius:50%;background:#1E3050;'
                f'border:2px solid #2D4A6E;display:flex;align-items:center;justify-content:center;'
                f'font-size:28px;font-weight:700;color:#F59E0B">{initial}</div>'
            )
            if avatar_url and avatar_url.lower() not in ("nan", "none", "0", "") and avatar_url.startswith("http"):
                data_uri = _avatar_data_uri(avatar_url)
                if data_uri:
                    st.markdown(
                        f'<img src="{data_uri}" width="80" height="80" '
                        f'style="border-radius:50%;object-fit:cover;border:2px solid #2D4A6E;display:block" />',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(fallback_html, unsafe_allow_html=True)
            else:
                st.markdown(fallback_html, unsafe_allow_html=True)

        with col2:
            st.markdown(
                f"<h3 style='margin:0;color:#F1F5F9;font-weight:700'>{lead.get('full_name','')}</h3>"
                f"<p style='margin:4px 0;color:#94A3B8'>@{lead.get('username','')} · "
                f"⚖️ {lead.get('nicho','Geral')} · "
                f"{lead.get('followers',0):,} seguidores</p>",
                unsafe_allow_html=True,
            )

        st.divider()

        # ── Dados estruturados ────────────────────────────────────────────────
        col_oab, col_cnpj, col_site = st.columns(3)

        with col_oab:
            st.markdown("**OAB**")
            if lead.get("oab_encontrado"):
                st.markdown(
                    f"**{lead.get('oab_numero','')} {lead.get('oab_seccional','')}** — "
                    f"{lead.get('oab_situacao','')}"
                )
                anos = lead.get("oab_anos_ativo")
                if anos is not None:
                    st.caption(f"Inscrito há {anos:.0f} ano(s)")
            else:
                st.caption("Não encontrado")

        with col_cnpj:
            st.markdown("**CNPJ**")
            if lead.get("cnpj_numero"):
                st.markdown(lead.get("cnpj_razao_social", lead.get("cnpj_numero", "")))
                st.caption(lead.get("cnpj_situacao", ""))
            else:
                st.caption("Não encontrado")

        with col_site:
            st.markdown("**Site**")
            if lead.get("site_encontrado"):
                site_url = lead.get("site_url", "")
                st.markdown(f"[{site_url[:40]}...]({site_url})" if len(site_url) > 40 else f"[{site_url}]({site_url})")
                pixels = []
                if lead.get("has_fb_pixel"):
                    pixels.append("Pixel FB")
                if lead.get("has_ga"):
                    pixels.append("GA/GTM")
                if lead.get("has_google_ads"):
                    pixels.append("Google Ads")
                if pixels:
                    st.caption("✓ " + " · ".join(pixels))
                else:
                    st.caption("⚠️ Sem rastreamento")
            else:
                st.caption("Não encontrado +20pts")

        # ── Contatos ──────────────────────────────────────────────────────────
        st.divider()
        phone = lead.get("phone_full", "") or lead.get("phone_from_bio", "")
        email = lead.get("email", "")

        contact_cols = st.columns(3)
        with contact_cols[0]:
            if phone:
                st.markdown(f"📱 `{phone}`")
                wa_url = f"https://wa.me/{phone.lstrip('+')}"
                st.link_button("WhatsApp", wa_url, use_container_width=True)

        with contact_cols[1]:
            if email:
                st.markdown(f"✉️ `{email}`")
                st.link_button("Email", f"mailto:{email}", use_container_width=True)

        with contact_cols[2]:
            ig_url = lead.get("profile_url", f"https://instagram.com/{lead.get('username','')}")
            st.link_button("Ver Instagram", ig_url, use_container_width=True)

        # ── Insight ───────────────────────────────────────────────────────────
        insight = lead.get("insight", "")
        if insight:
            st.divider()
            st.info(f"💡 {insight}")

        # ── Score breakdown ───────────────────────────────────────────────────
        criterios = lead.get("criterios_aplicados", [])
        if criterios:
            with st.expander("Ver breakdown do score", expanded=False):
                from scoring.engine import CRITERIOS
                for c in criterios:
                    pts = CRITERIOS.get(c, 0)
                    color_pt = "#16A34A" if pts > 0 else "#DC2626"
                    sign = "+" if pts > 0 else ""
                    st.markdown(
                        f"<span style='color:{color_pt};font-weight:600'>{sign}{pts}pts</span> "
                        f"<span style='color:#94A3B8'>{c}</span>",
                        unsafe_allow_html=True,
                    )
