"""
upload.py — Parser do arquivo XLSX exportado pelo Growman.
Lê, valida, filtra advogados e normaliza campos.
"""

import re
import pandas as pd
from unidecode import unidecode

# Mapeamento colunas Growman → campos internos
COLUMN_MAP = {
    "Instagram ID": "ig_id",
    "Username": "username",
    "Full name": "full_name",
    "Profile link": "profile_url",
    "Avatar pic": "avatar_url",
    "Followers count": "followers",
    "Following count": "following",
    "Biography": "bio",
    "Category": "ig_category",
    "Public email": "email",
    "Posts count": "posts",
    "Phone country code": "phone_code",
    "Phone number": "phone",
    "City": "city",
    "Address": "address",
    "Is private": "is_private",
    "Is business": "is_business",
    "External url": "external_url",
    "Is verified": "is_verified",
    "Followed by viewer": "followed_by_viewer",
}

# Termos que indicam perfil de advogado na bio
LAWYER_KEYWORDS = [
    r"\badv\b", r"advogad", r"\bOAB\b", r"direito",
    r"jurídico", r"juridico", r"advocaci", r"\bDr\.\b", r"\bDra\.\b",
]

EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)


def _is_lawyer(bio: str) -> bool:
    """Retorna True se a bio contiver termos jurídicos."""
    if not isinstance(bio, str):
        return False
    for kw in LAWYER_KEYWORDS:
        if re.search(kw, bio, re.IGNORECASE):
            return True
    return False


def _normalize_name(name: str) -> str:
    """Remove emojis, pipes e separadores do nome para busca OAB/CNPJ."""
    if not isinstance(name, str):
        return ""
    name = EMOJI_RE.sub("", name)
    name = re.sub(r"[|/\\–—_]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _parse_bool_col(val) -> bool:
    """Converte 'YES'/'NO' ou 1/0 para bool."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().upper() == "YES"
    return bool(val)


def _safe_int(val, default=0) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def parse_growman_xlsx(file) -> tuple[pd.DataFrame, dict]:
    """
    Lê o arquivo XLSX do Growman, renomeia colunas, filtra perfis privados
    e não-advogados, normaliza campos e retorna o DataFrame limpo.

    Returns:
        df: DataFrame com apenas os leads advogados e públicos
        stats: dict com métricas do parse (total, filtrados, advogados)
    """
    # Tentar ler a aba 'contacts'; fallback para primeira aba
    try:
        raw = pd.read_excel(file, sheet_name="contacts", dtype=str)
    except Exception:
        raw = pd.read_excel(file, sheet_name=0, dtype=str)

    stats = {"total_bruto": len(raw)}

    # Renomear colunas conforme mapeamento
    present = {k: v for k, v in COLUMN_MAP.items() if k in raw.columns}
    df = raw.rename(columns=present)

    # Garantir colunas mínimas obrigatórias
    required = ["username", "full_name", "bio", "is_private"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Arquivo inválido: colunas ausentes após mapeamento: {missing}. "
            f"Colunas encontradas: {list(raw.columns)}"
        )

    # Filtrar perfis privados
    df["is_private"] = df["is_private"].apply(_parse_bool_col)
    df = df[~df["is_private"]].copy()
    stats["apos_filtro_privado"] = len(df)

    # Filtrar advogados pela bio
    df["bio"] = df["bio"].fillna("")
    df = df[df["bio"].apply(_is_lawyer)].copy()
    stats["advogados"] = len(df)

    # Normalizar nome
    df["full_name"] = df["full_name"].fillna("")
    df["full_name_normalizado"] = df["full_name"].apply(_normalize_name)

    # Converter campos numéricos
    for col in ["followers", "following", "posts"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda v: _safe_int(v))

    # Normalizar booleans restantes
    for col in ["is_business", "is_verified", "followed_by_viewer"]:
        if col in df.columns:
            df[col] = df[col].apply(_parse_bool_col)

    # Limpar telefone: concatenar código + número
    df["phone"] = df.get("phone", pd.Series("", index=df.index)).fillna("")
    df["phone_code"] = df.get("phone_code", pd.Series("", index=df.index)).fillna("")
    df["phone_full"] = df.apply(
        lambda r: (r["phone_code"] + r["phone"]).strip()
        if r["phone"] and r["phone"] != "nan"
        else "",
        axis=1,
    )

    # Limpar external_url e avatar_url
    for col in ["external_url", "avatar_url"]:
        df[col] = df.get(col, pd.Series("", index=df.index)).fillna("")
        df[col] = df[col].apply(
            lambda u: "" if str(u).strip().lower() in ("nan", "none", "0", "") else str(u).strip()
        )

    # Reset index
    df = df.reset_index(drop=True)

    return df, stats
