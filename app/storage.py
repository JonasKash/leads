"""
storage.py — Persistência local com SQLite.
Simples: grava em data/crm.db automaticamente. Sem configurações, sem nuvem.
"""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "crm.db"
DB_PATH.parent.mkdir(exist_ok=True, parents=True)


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            username   TEXT PRIMARY KEY,
            data       TEXT NOT NULL,
            closer     TEXT NOT NULL DEFAULT '',
            score      INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.commit()
    return c


def add_leads(novos: list[dict]) -> int:
    """
    Acumula leads novos no banco.
    - Se o username já existe: atualiza dados mas MANTÉM o closer atual.
    - Se é novo: insere com closer vazio.
    Retorna quantos leads foram adicionados/atualizados.
    """
    c = _conn()
    closer_existente = {
        row[0]: row[1]
        for row in c.execute("SELECT username, closer FROM leads")
    }

    count = 0
    for lead in novos:
        username = lead.get("username", "")
        if not username:
            continue
        # Preservar closer se já existia
        closer = closer_existente.get(username, lead.get("closer", ""))
        lead_final = {**lead, "closer": closer}
        score = int(lead.get("score", 0))

        c.execute("""
            INSERT INTO leads (username, data, closer, score, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(username) DO UPDATE SET
                data       = excluded.data,
                score      = excluded.score,
                updated_at = datetime('now')
        """, (username, json.dumps(lead_final, ensure_ascii=False, default=str), closer, score))
        count += 1

    c.commit()
    c.close()
    return count


def load_leads() -> list[dict]:
    """Carrega todos os leads ordenados por score desc. Migra crm.json se SQLite vazio."""
    c = _conn()
    rows = c.execute("SELECT data, closer FROM leads ORDER BY score DESC").fetchall()

    # Migrar dados do crm.json legado se o banco estiver vazio
    if not rows:
        json_path = DB_PATH.parent / "crm.json"
        if json_path.exists():
            try:
                with open(json_path, encoding="utf-8") as f:
                    legado = json.load(f)
                if legado:
                    c.close()
                    add_leads(legado)
                    c = _conn()
                    rows = c.execute(
                        "SELECT data, closer FROM leads ORDER BY score DESC"
                    ).fetchall()
            except Exception:
                pass

    c.close()
    leads = []
    for data_json, closer in rows:
        lead = json.loads(data_json)
        lead["closer"] = closer
        leads.append(lead)
    return leads


def update_closer(username: str, closer: str) -> None:
    """Atualiza o closer de um lead específico."""
    c = _conn()
    c.execute(
        "UPDATE leads SET closer = ?, updated_at = datetime('now') WHERE username = ?",
        (closer, username),
    )
    row = c.execute("SELECT data FROM leads WHERE username = ?", (username,)).fetchone()
    if row:
        lead = json.loads(row[0])
        lead["closer"] = closer
        c.execute("UPDATE leads SET data = ? WHERE username = ?",
                  (json.dumps(lead, ensure_ascii=False, default=str), username))
    c.commit()
    c.close()


def total_leads() -> int:
    c = _conn()
    n = c.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    c.close()
    return n
