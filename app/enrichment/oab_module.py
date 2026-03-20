"""
oab_module.py — Consulta CNA (API pública OAB).
Busca o advogado pelo nome, retorna dados de inscrição e tempo de atividade.
"""

import os
import re
import time
import datetime
import requests
from unidecode import unidecode

OAB_API_URL = "https://cna.oab.org.br/api/advogados"
DELAY = float(os.getenv("DELAY_OAB", "1.0"))

_session = requests.Session()
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; OABLeadQualifier/1.0)",
    "Accept": "application/json",
})


def _query_oab(nome: str, uf: str = "") -> list[dict]:
    """Faz a requisição ao CNA e retorna lista de resultados."""
    params = {"nome": nome}
    if uf:
        params["uf"] = uf.upper()
    try:
        resp = _session.get(OAB_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # A API retorna {"Data": [...]} ou diretamente uma lista
        if isinstance(data, dict):
            return data.get("Data", []) or data.get("data", [])
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def _calc_years_active(data_inscricao: str) -> float | None:
    """Calcula anos desde a data de inscrição (formato YYYY-MM-DD ou DD/MM/YYYY)."""
    if not data_inscricao:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.datetime.strptime(data_inscricao[:len(fmt)], fmt)
            delta = datetime.datetime.now() - dt
            return round(delta.days / 365.25, 1)
        except ValueError:
            continue
    return None


def _pick_best_result(results: list[dict], nome_buscado: str) -> dict | None:
    """
    Dentre os resultados, tenta encontrar o mais relevante pelo nome.
    Prioriza situação ATIVO.
    """
    if not results:
        return None

    nome_norm = unidecode(nome_buscado).upper()

    # Preferir ATIVO
    ativos = [r for r in results if str(r.get("Situacao", "")).upper() == "ATIVO"]
    candidatos = ativos if ativos else results

    # Tentar match de nome
    for r in candidatos:
        api_nome = unidecode(str(r.get("Nome", ""))).upper()
        # Verifica se ao menos 2 palavras do nome buscado estão no resultado
        palavras = [p for p in nome_norm.split() if len(p) > 2]
        matches = sum(1 for p in palavras if p in api_nome)
        if matches >= 2:
            return r

    # Fallback: primeiro candidato
    return candidatos[0] if candidatos else None


def lookup_oab(full_name: str, city: str = "") -> dict:
    """
    Busca dados OAB para o advogado.

    Returns:
        {
            oab_numero: str,
            oab_seccional: str,
            oab_subsecao: str,
            oab_situacao: str,        # ATIVO | SUSPENSO | CANCELADO | ''
            oab_tipo: str,
            oab_data_inscricao: str,
            oab_anos_ativo: float | None,
            oab_encontrado: bool,
        }
    """
    empty = {
        "oab_numero": "",
        "oab_seccional": "",
        "oab_subsecao": "",
        "oab_situacao": "",
        "oab_tipo": "",
        "oab_data_inscricao": "",
        "oab_anos_ativo": None,
        "oab_encontrado": False,
    }

    if not full_name or not full_name.strip():
        return empty

    nome_clean = full_name.strip()

    # Tentar com nome original
    results = _query_oab(nome_clean)
    time.sleep(DELAY)

    # Fallback sem acentos
    if not results:
        nome_ascii = unidecode(nome_clean)
        if nome_ascii != nome_clean:
            results = _query_oab(nome_ascii)
            time.sleep(DELAY)

    result = _pick_best_result(results, nome_clean)
    if not result:
        return empty

    data_inscricao = str(result.get("DataInscricao", "") or result.get("data_inscricao", ""))
    anos_ativo = _calc_years_active(data_inscricao)

    return {
        "oab_numero": str(result.get("Numero", "") or result.get("numero", "")),
        "oab_seccional": str(result.get("UfInscricao", "") or result.get("uf", "")),
        "oab_subsecao": str(result.get("Subsecao", "") or result.get("subsecao", "")),
        "oab_situacao": str(result.get("Situacao", "") or result.get("situacao", "")).upper(),
        "oab_tipo": str(result.get("TipoInscricao", "") or result.get("tipo", "")),
        "oab_data_inscricao": data_inscricao,
        "oab_anos_ativo": anos_ativo,
        "oab_encontrado": True,
    }
