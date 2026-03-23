"""
storage.py — Persistência de leads em SQLite local.

SQLite persiste no disco automaticamente — sem git push, sem sessões perdidas.
O arquivo data/crm.db é criado na primeira execução e mantido entre reinícios.

Fluxo:
  1. Admin faz upload do XLSX → leads processados → save_leads() → grava no banco
  2. Closers abrem o app → load_leads() → carrega do banco (com assignments preservados)
  3. Closer atribui lead → update_closer() → atualiza só aquele registro no banco
  4. Tudo persiste automaticamente — zero git push necessário para dados
"""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "crm.db"
DB_PATH.parent.mkdir(exist_ok=True, parents=True)


def _conn() -> sqlite3.Connection:
    """Abre conexão com WAL mode (leitura/escrita concorrente segura)."""
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    c.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            username   TEXT PRIMARY KEY,
            data       TEXT NOT NULL,
            closer     TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.commit()
    return c


def save_leads(leads: list[dict]) -> None:
    """
    Salva batch de leads no banco.
    Preserva o campo 'closer' de leads que já existiam no banco.
    """
    c = _conn()
    # Recuperar assignments existentes antes de qualquer escrita
    existentes = {
        row[0]: row[1]
        for row in c.execute("SELECT username, closer FROM leads")
    }

    c.execute("DELETE FROM leads")
    for lead in leads:
        username = lead.get("username", "")
        # Preservar assignment: prioridade: (1) lead já tem closer, (2) banco tinha, (3) vazio
        closer = lead.get("closer") or existentes.get(username, "") or ""
        lead_final = {**lead, "closer": closer}
        c.execute(
            "INSERT INTO leads (username, data, closer) VALUES (?, ?, ?)",
            (username, json.dumps(lead_final, ensure_ascii=False, default=str), closer),
        )
    c.commit()
    c.close()


def load_leads() -> list[dict] | None:
    """Carrega todos os leads do banco. Retorna None se vazio."""
    c = _conn()
    rows = c.execute(
        "SELECT data, closer FROM leads ORDER BY CAST(json_extract(data,'$.score') AS INTEGER) DESC"
    ).fetchall()
    c.close()

    if not rows:
        # Tentar migrar do JSON legado se existir
        return _migrar_json_legado()

    leads = []
    for data_json, closer in rows:
        lead = json.loads(data_json)
        lead["closer"] = closer   # valor do banco é sempre o mais atualizado
        leads.append(lead)
    return leads


def update_closer(username: str, closer: str) -> None:
    """
    Atualiza o closer de UM lead específico.
    Chamado a cada atribuição/devolução — muito mais eficiente que reescrever tudo.
    """
    c = _conn()
    # Atualizar coluna closer
    c.execute(
        "UPDATE leads SET closer = ?, updated_at = datetime('now') WHERE username = ?",
        (closer, username),
    )
    # Atualizar também o JSON para manter consistência
    row = c.execute("SELECT data FROM leads WHERE username = ?", (username,)).fetchone()
    if row:
        lead = json.loads(row[0])
        lead["closer"] = closer
        c.execute(
            "UPDATE leads SET data = ? WHERE username = ?",
            (json.dumps(lead, ensure_ascii=False, default=str), username),
        )
    c.commit()
    c.close()


def total_leads() -> int:
    """Retorna o total de leads no banco (útil para verificação rápida)."""
    c = _conn()
    count = c.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    c.close()
    return count


def _migrar_json_legado() -> list[dict] | None:
    """Migra automaticamente do leads.json antigo para SQLite (executa uma vez)."""
    json_path = DB_PATH.parent / "leads.json"
    if not json_path.exists():
        return None
    try:
        with open(json_path, encoding="utf-8") as f:
            leads = json.load(f)
        if leads:
            save_leads(leads)
            # Renomear arquivo migrado para não reprocessar
            json_path.rename(json_path.with_suffix(".migrated.json"))
            return load_leads()
    except Exception:
        pass
    return None
