"""
bio_parser.py — Análise da bio do Instagram (sem API, instantâneo).
Detecta nicho jurídico, CTA, link, escritório, telefone.
"""

import re

# ── Nichos jurídicos ──────────────────────────────────────────────────────────
NICHOS = {
    "Previdenciário": [
        r"previdenci", r"inss", r"aposentadori", r"benefício", r"BPC",
        r"LOAS", r"auxílio.?doença", r"invalidez",
    ],
    "Trabalhista": [
        r"trabalh", r"CLT", r"rescis", r"demiss", r"FGTS", r"trabalhador",
        r"empregad", r"reclamação.?trabalhista",
    ],
    "Família": [
        r"famíli", r"familia", r"divórcio", r"divorcio", r"inventário",
        r"pensão.?alimentícia", r"guarda", r"adoç", r"herança",
    ],
    "Criminal": [
        r"criminal", r"penal", r"defesa.?criminal", r"júri", r"habeas",
        r"crime", r"réu", r"acusad",
    ],
    "Empresarial": [
        r"empresari", r"societário", r"contrato", r"startup", r"holding",
        r"fusão", r"aquisição", r"LGPD", r"compliance",
    ],
    "Imobiliário": [
        r"imobiliári", r"imóvel", r"imovel", r"incorporaç", r"construtora",
        r"compra.?e.?venda", r"locaç", r"condomini",
    ],
    "Tributário": [
        r"tributári", r"tributo", r"imposto", r"fiscal", r"planej.?tributári",
        r"ICMS", r"ISS", r"IR\b",
    ],
    "Consumidor": [
        r"consumidor", r"CDC", r"direito.?do.?consumidor", r"recall",
        r"produto.?defeitu",
    ],
    "Cível": [
        r"cível", r"civil", r"indeniz", r"dano.?moral", r"responsabilidade.?civil",
    ],
}

# ── CTA (call-to-action) ──────────────────────────────────────────────────────
CTA_PATTERNS = [
    r"agende", r"marque", r"clique", r"whatsapp", r"consulta",
    r"fale.?comigo", r"entre.?em.?contato", r"me.?chame", r"link.?na.?bio",
    r"acesse", r"saiba.?mais",
]

# ── Telefone na bio ───────────────────────────────────────────────────────────
PHONE_RE = re.compile(
    r"(?:\+?55\s?)?(?:\(?\d{2}\)?[\s\-]?)(?:9\s?)?\d{4}[\s\-]?\d{4}"
)

# ── Menção de @handle (escritório) ────────────────────────────────────────────
HANDLE_RE = re.compile(r"@([\w.]+)")


def _detect_nicho(bio: str) -> str:
    """Retorna o nicho jurídico detectado ou 'Geral'."""
    for nicho, patterns in NICHOS.items():
        for p in patterns:
            if re.search(p, bio, re.IGNORECASE):
                return nicho
    return "Geral"


def _detect_cta(bio: str) -> bool:
    """Retorna True se houver call-to-action na bio."""
    for p in CTA_PATTERNS:
        if re.search(p, bio, re.IGNORECASE):
            return True
    return False


def _detect_phone_in_bio(bio: str, phone_full: str = "") -> str:
    """
    Extrai telefone da bio se diferente do campo phone_full já mapeado.
    Retorna o número encontrado ou ''.
    """
    match = PHONE_RE.search(bio)
    if not match:
        return ""
    found = re.sub(r"\D", "", match.group())
    # Não retornar se já existe e é igual
    phone_clean = re.sub(r"\D", "", phone_full)
    if phone_clean and found.endswith(phone_clean[-8:]):
        return ""
    return found


def _detect_office_handle(bio: str, own_username: str = "") -> str:
    """
    Detecta menção a @escritório na bio (handle diferente do próprio).
    Retorna o @handle encontrado ou ''.
    """
    handles = HANDLE_RE.findall(bio)
    for h in handles:
        if h.lower() != own_username.lower():
            return f"@{h}"
    return ""


def parse_bio(bio: str, external_url: str = "", phone_full: str = "", username: str = "") -> dict:
    """
    Analisa a bio e retorna um dict com todos os campos enriquecidos.

    Returns:
        {
            nicho: str,
            has_cta: bool,
            has_link: bool,
            cta_sem_link: bool,       # CTA na bio mas sem link externo
            phone_from_bio: str,      # telefone extra encontrado na bio
            office_handle: str,       # @escritório mencionado
        }
    """
    nicho = _detect_nicho(bio)
    has_cta = _detect_cta(bio)
    has_link = bool(external_url and external_url.strip())
    cta_sem_link = has_cta and not has_link
    phone_from_bio = _detect_phone_in_bio(bio, phone_full)
    office_handle = _detect_office_handle(bio, username)

    return {
        "nicho": nicho,
        "has_cta": has_cta,
        "has_link": has_link,
        "cta_sem_link": cta_sem_link,
        "phone_from_bio": phone_from_bio,
        "office_handle": office_handle,
    }
