"""
scoring/engine.py — Motor de score e classificação de leads.
Recebe o dict enriquecido de um lead e retorna score (0-100),
classificação e insight personalizado.
"""

# ── Pesos dos critérios ───────────────────────────────────────────────────────
CRITERIOS = {
    # OAB (Bônus se disponível, mas não obrigatório)
    "oab_ativo":              25,
    "oab_recente_1_3anos":    10,
    "oab_senior_10anos":      -5,

    # CNPJ
    "cnpj_ativo_juridico":    15,
    "cnpj_ativo_generico":     5,
    "sem_cnpj":               15,

    # Presença digital (Bio + Site)
    "sem_site":               15,
    "site_sem_pixel":         10,
    "site_com_pixel":         -10,
    "sem_gmb":                10,
    "gmb_ativo_semreviews":    5,
    "gmb_forte":              -15,

    # Instagram (Peso maior para garantir classificação no browser)
    "sem_link_na_bio":        20,
    "cta_na_bio_sem_link":    25,
    "identificado_pela_bio":  30,  # CRÍTICO: Pontos por ser advogado detectado
    "followers_500_5k":       10,
    "conta_business":          5,
    "email_disponivel":        5,
    "telefone_disponivel":    10,
}


def classificar(score: int) -> str:
    if score >= 70:
        return "🔥 Quente"
    elif score >= 45:
        return "🟡 Morno"
    else:
        return "❄️ Frio"


def _gerar_insight(lead: dict) -> str:
    """Gera 1 frase de insight personalizado baseada nos dados do lead."""
    nicho = lead.get("nicho", "")
    nicho_str = f" {nicho.lower()}" if nicho and nicho != "Geral" else ""
    nome = lead.get("full_name", "").split()[0] if lead.get("full_name") else "Advogado(a)"

    oab_anos = lead.get("oab_anos_ativo")
    oab_ativo = lead.get("oab_situacao", "") == "ATIVO"
    site = lead.get("site_encontrado", False)
    pixel = lead.get("has_fb_pixel", False) or lead.get("has_ga", False)
    gmb = lead.get("gmb_encontrado", False)
    cta_sem_link = lead.get("cta_sem_link", False)
    tem_email = bool(lead.get("email", ""))
    tem_fone = bool(lead.get("phone_full", "") or lead.get("phone_from_bio", ""))

    partes = []

    # Base: nicho + OAB
    if oab_ativo and oab_anos is not None:
        if oab_anos <= 3:
            partes.append(f"Advogado(a){nicho_str} com OAB ativo há {oab_anos:.0f} ano(s)")
        elif oab_anos >= 10:
            partes.append(f"Advogado(a){nicho_str} com OAB ativo há {oab_anos:.0f} anos")
        else:
            partes.append(f"Advogado(a){nicho_str} com OAB ativo")
    else:
        partes.append(f"Advogado(a){nicho_str}")

    # Lacunas digitais
    lacunas = []
    if not site:
        lacunas.append("sem site")
    elif not pixel:
        lacunas.append("sem pixel de rastreamento")
    if not gmb:
        lacunas.append("sem GMB")
    if cta_sem_link:
        lacunas.append("CTA na bio sem link")

    if lacunas:
        partes.append(", ".join(lacunas))
        partes.append("— perfil ideal para mentoria de presença digital jurídica")
    else:
        partes.append("— já investiu em presença digital")

    return " ".join(partes) + "."


def calcular_score(lead: dict) -> dict:
    """
    Calcula o score do lead com base nos dados enriquecidos.

    Parâmetros esperados no dict `lead`:
        oab_situacao, oab_anos_ativo,
        cnpj_situacao, cnpj_cnae_juridico,
        site_encontrado, has_fb_pixel, has_ga,
        gmb_encontrado, gmb_reviews,
        has_link (external_url), cta_sem_link,
        followers, is_business, email, phone_full

    Returns:
        lead atualizado com: score, classificacao, insight, criterios_aplicados
    """
    pontos = 0
    aplicados = []

    # Bônus Base: Identificado como advogado na Bio (crítico para rodar em browsers/Vercel)
    pontos += CRITERIOS["identificado_pela_bio"]
    aplicados.append("identificado_pela_bio")

    # ── OAB ──────────────────────────────────────────────────────────────────
    oab_situacao = lead.get("oab_situacao", "").upper()
    oab_anos = lead.get("oab_anos_ativo")

    if oab_situacao == "ATIVO":
        pontos += CRITERIOS["oab_ativo"]
        aplicados.append("oab_ativo")

        if oab_anos is not None:
            if 1 <= oab_anos <= 3:
                pontos += CRITERIOS["oab_recente_1_3anos"]
                aplicados.append("oab_recente_1_3anos")
            elif oab_anos > 10:
                pontos += CRITERIOS["oab_senior_10anos"]
                aplicados.append("oab_senior_10anos")

    # ── CNPJ ─────────────────────────────────────────────────────────────────
    cnpj_situacao = lead.get("cnpj_situacao", "").upper()
    cnpj_juridico = lead.get("cnpj_cnae_juridico", False)
    cnpj_numero = lead.get("cnpj_numero", "")

    if cnpj_situacao == "ATIVA" and cnpj_juridico:
        pontos += CRITERIOS["cnpj_ativo_juridico"]
        aplicados.append("cnpj_ativo_juridico")
    elif cnpj_situacao == "ATIVA":
        pontos += CRITERIOS["cnpj_ativo_generico"]
        aplicados.append("cnpj_ativo_generico")
    elif not cnpj_numero:
        pontos += CRITERIOS["sem_cnpj"]
        aplicados.append("sem_cnpj")

    # ── Presença digital — Site ───────────────────────────────────────────────
    site = lead.get("site_encontrado", False)
    tem_pixel = lead.get("has_fb_pixel", False) or lead.get("has_ga", False)

    if not site:
        pontos += CRITERIOS["sem_site"]
        aplicados.append("sem_site")
    elif not tem_pixel:
        pontos += CRITERIOS["site_sem_pixel"]
        aplicados.append("site_sem_pixel")
    else:
        pontos += CRITERIOS["site_com_pixel"]
        aplicados.append("site_com_pixel")

    # ── Presença digital — GMB ────────────────────────────────────────────────
    gmb_encontrado = lead.get("gmb_encontrado", False)
    gmb_reviews = lead.get("gmb_reviews", 0) or 0

    if not gmb_encontrado:
        pontos += CRITERIOS["sem_gmb"]
        aplicados.append("sem_gmb")
    elif gmb_reviews < 10:
        pontos += CRITERIOS["gmb_ativo_semreviews"]
        aplicados.append("gmb_ativo_semreviews")
    else:
        pontos += CRITERIOS["gmb_forte"]
        aplicados.append("gmb_forte")

    # ── Instagram ─────────────────────────────────────────────────────────────
    has_link = lead.get("has_link", False)
    cta_sem_link = lead.get("cta_sem_link", False)
    followers = lead.get("followers", 0) or 0

    if cta_sem_link:
        pontos += CRITERIOS["cta_na_bio_sem_link"]
        aplicados.append("cta_na_bio_sem_link")
    elif not has_link:
        pontos += CRITERIOS["sem_link_na_bio"]
        aplicados.append("sem_link_na_bio")

    if 500 <= followers <= 5000:
        pontos += CRITERIOS["followers_500_5k"]
        aplicados.append("followers_500_5k")

    if lead.get("is_business", False):
        pontos += CRITERIOS["conta_business"]
        aplicados.append("conta_business")

    if lead.get("email", ""):
        pontos += CRITERIOS["email_disponivel"]
        aplicados.append("email_disponivel")

    if lead.get("phone_full", "") or lead.get("phone_from_bio", ""):
        pontos += CRITERIOS["telefone_disponivel"]
        aplicados.append("telefone_disponivel")

    # ── Finalizar ─────────────────────────────────────────────────────────────
    score = max(0, min(100, pontos))
    classificacao = classificar(score)
    insight = _gerar_insight(lead)

    return {
        **lead,
        "score": score,
        "classificacao": classificacao,
        "insight": insight,
        "criterios_aplicados": aplicados,
    }
