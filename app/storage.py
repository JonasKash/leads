"""
storage.py — Persistência de leads em JSON local.

Substituição do SQLite por JSON puro para compatibilidade com
Streamlit Cloud e ambientes Pyodide que não incluem sqlite3.

Fluxo:
  1. Admin faz upload do XLSX → leads processados → save_leads() → grava no arquivo
  2. Closers abrem o app → load_leads() → carrega do arquivo (com assignments preservados)
  3. Closer atribui lead → update_closer() → carrega, atualiza e salva
  4. Tudo persiste automaticamente — zero git push necessário para dados
"""

import json
import os
import tempfile
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True, parents=True)
DB_PATH = DATA_DIR / "crm.json"


def _load_raw() -> list[dict]:
    """Lê o arquivo JSON. Retorna lista vazia se não existir ou corrompido."""
    if not DB_PATH.exists():
        return []
    try:
        with open(DB_PATH, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_raw(leads: list[dict]) -> None:
    """Grava a lista de leads no arquivo JSON de forma atômica."""
    tmp_path = DB_PATH.with_suffix(".tmp.json")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(leads, f, ensure_ascii=False, indent=2, default=str)
        # Substituição atômica (funciona no Windows e Linux)
        tmp_path.replace(DB_PATH)
    except OSError:
        # Fallback: escrita direta
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(leads, f, ensure_ascii=False, indent=2, default=str)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def save_leads(leads: list[dict]) -> None:
    """
    Salva batch de leads no arquivo.
    Preserva o campo 'closer' de leads que já existiam.
    """
    # Recuperar assignments existentes antes de sobrescrever
    existentes = {
        lead.get("username", ""): lead.get("closer", "")
        for lead in _load_raw()
    }

    leads_finais = []
    for lead in leads:
        username = lead.get("username", "")
        closer = lead.get("closer") or existentes.get(username, "") or ""
        leads_finais.append({**lead, "closer": closer})

    _save_raw(leads_finais)


def load_leads() -> list[dict] | None:
    """Carrega todos os leads. Retorna None se vazio."""
    leads = _load_raw()
    if not leads:
        return _migrar_sqlite_legado()

    # Ordenar por score decrescente (igual ao comportamento anterior do SQLite)
    try:
        leads.sort(key=lambda l: int(l.get("score", 0)), reverse=True)
    except (ValueError, TypeError):
        pass

    return leads if leads else None


def update_closer(username: str, closer: str) -> None:
    """
    Atualiza o closer de UM lead específico.
    Chamado a cada atribuição/devolução — lê, atualiza, salva.
    """
    leads = _load_raw()
    for lead in leads:
        if lead.get("username") == username:
            lead["closer"] = closer
            break
    _save_raw(leads)


def total_leads() -> int:
    """Retorna o total de leads (útil para verificação rápida)."""
    return len(_load_raw())


def _migrar_sqlite_legado() -> list[dict] | None:
    """
    Tenta migrar dados do SQLite legado (crm.db) para JSON,
    caso o sqlite3 esteja disponível no ambiente.
    """
    db_path = DATA_DIR / "crm.db"
    if not db_path.exists():
        # Tentar migrar do leads.json antigo
        return _migrar_json_legado()

    try:
        import sqlite3
        c = sqlite3.connect(str(db_path))
        rows = c.execute(
            "SELECT data, closer FROM leads ORDER BY CAST(json_extract(data,'$.score') AS INTEGER) DESC"
        ).fetchall()
        c.close()

        if not rows:
            return _migrar_json_legado()

        leads = []
        for data_json, closer in rows:
            lead = json.loads(data_json)
            lead["closer"] = closer
            leads.append(lead)

        # Migrar para o novo formato JSON
        _save_raw(leads)
        return leads
    except Exception:
        return _migrar_json_legado()


def _migrar_json_legado() -> list[dict] | None:
    """Migra automaticamente do leads.json antigo (executa uma vez)."""
    json_path = DATA_DIR / "leads.json"
    if not json_path.exists():
        return None
    try:
        with open(json_path, encoding="utf-8") as f:
            leads = json.load(f)
        if leads:
            save_leads(leads)
            json_path.rename(json_path.with_suffix(".migrated.json"))
            return load_leads()
    except Exception:
        pass
    return None
