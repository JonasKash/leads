"""
storage.py — Persistência híbria: Vercel Postgres (Cloud) ou JSON (Local).

Lógica:
  - Se 'POSTGRES_URL' estiver nas variáveis de ambiente → Usa Postgres (Vercel)
  - Caso contrário → Usa JSON local (Desenvolvimento local)
"""

import os
import json
import psycopg2
from pathlib import Path
from psycopg2.extras import DictCursor, execute_values

# Configuração local
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True, parents=True)
DB_PATH_JSON = DATA_DIR / "crm.json"

# Configuração Postgres (Vercel injeta POSTGRES_URL)
POSTGRES_URL = os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL")


def _get_conn():
    """Retorna uma conexão com Postgres ou None se não configurado."""
    if not POSTGRES_URL:
        return None
    try:
        # psycogp2 entende o formato 'postgres://...' do Vercel
        conn = psycopg2.connect(POSTGRES_URL, sslmode="require")
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao Postgres: {e}")
        return None


def _init_db():
    """Cria a tabela no Postgres se não existir."""
    conn = _get_conn()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    username   TEXT PRIMARY KEY,
                    data       JSONB NOT NULL,
                    closer     TEXT NOT NULL DEFAULT '',
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()
    finally:
        conn.close()


# --- OPERAÇÕES ---

def save_leads(leads: list[dict]) -> None:
    """Salva leads no Postgres (Cloud) ou JSON (Local)."""
    conn = _get_conn()
    if conn:
        try:
            # Pegar closers atuais do Postgres para não perdê-los no re-upload
            with conn.cursor() as cur:
                cur.execute("SELECT username, closer FROM leads")
                existentes = {u: c for u, c in cur.fetchall()}

            # Preparar dados para insert massivo (Upsert)
            values = []
            for lead in leads:
                username = lead.get("username", "")
                closer = lead.get("closer") or existentes.get(username, "") or ""
                lead_final = {**lead, "closer": closer}
                values.append((username, json.dumps(lead_final), closer))

            with conn.cursor() as cur:
                execute_values(cur, """
                    INSERT INTO leads (username, data, closer)
                    VALUES %s
                    ON CONFLICT (username) DO UPDATE SET
                        data = EXCLUDED.data,
                        closer = EXCLUDED.closer,
                        updated_at = EXCLUDED.updated_at
                """, values)
            conn.commit()
        finally:
            conn.close()
    else:
        # Fallback para JSON local
        existentes = {l.get("username", ""): l.get("closer", "") for l in _load_json()}
        leads_finais = []
        for lead in leads:
            username = lead.get("username", "")
            closer = lead.get("closer") or existentes.get(username, "") or ""
            leads_finais.append({**lead, "closer": closer})
        _save_json(leads_finais)


def load_leads() -> list[dict] | None:
    """Carrega leads do Postgres ou JSON."""
    conn = _get_conn()
    if conn:
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT data, closer FROM leads
                    ORDER BY (data->>'score')::int DESC NULLS LAST
                """)
                rows = cur.fetchall()
            if not rows:
                # Tentar migrar do JSON se banco estiver vazio no primeiro acesso
                local = _load_json()
                if local:
                    save_leads(local)
                    return load_leads()
                return None

            leads = []
            for row in rows:
                lead = row['data']
                lead['closer'] = row['closer']
                leads.append(lead)
            return leads
        finally:
            conn.close()
    else:
        leads = _load_json()
        if leads:
            leads.sort(key=lambda l: int(l.get("score", 0)), reverse=True)
            return leads
        return None


def update_closer(username: str, closer: str) -> None:
    """Atualiza o closer de um lead específico."""
    conn = _get_conn()
    if conn:
        try:
            with conn.cursor() as cur:
                # Atualiza coluna e extrai JSON para atualizar campo interno
                cur.execute("SELECT data FROM leads WHERE username = %s", (username,))
                row = cur.fetchone()
                if row:
                    lead = row[0]
                    lead["closer"] = closer
                    cur.execute("""
                        UPDATE leads SET
                            closer = %s,
                            data = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE username = %s
                    """, (closer, json.dumps(lead), username))
            conn.commit()
        finally:
            conn.close()
    else:
        leads = _load_json()
        for lead in leads:
            if lead.get("username") == username:
                lead["closer"] = closer
                break
        _save_json(leads)


def total_leads() -> int:
    conn = _get_conn()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM leads")
                return cur.fetchone()[0]
        finally:
            conn.close()
    return len(_load_json())


# --- HELPERS JSON ---

def _load_json() -> list[dict]:
    if not DB_PATH_JSON.exists(): return []
    try:
        with open(DB_PATH_JSON, encoding="utf-8") as f:
            return json.load(f)
    except: return []

def _save_json(leads: list[dict]):
    with open(DB_PATH_JSON, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2, default=str)

# Iniciar banco no cloud automaticamente se possível
if POSTGRES_URL:
    try:
        _init_db()
    except:
        pass
