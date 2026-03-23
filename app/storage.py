"""
storage.py — Persistência Cloud com Supabase API (HTTP Browser-safe).

Compatível com Pyodide/Stlite (Vercel Browser-based).
Usa apenas Requests para falar com a REST API do Supabase.
"""

import os
import json
import requests
from pathlib import Path

# Configuração local
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True, parents=True)
DB_PATH_JSON = DATA_DIR / "crm.json"

# Configuração Supabase (Vercel ou .env)
# O Vercel injeta estes nomes se você instalou a integração
SURL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
SKEY = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_ANON_KEY")

HEADERS = {
    "apikey": SKEY,
    "Authorization": f"Bearer {SKEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}


def _get_api_url():
    if not SURL: return None
    # Mesa rounting: se a URL terminar com / apenas concatena
    base = SURL.rstrip('/')
    return f"{base}/rest/v1/leads"


def save_leads(leads: list[dict]) -> None:
    """Salva leads no Supabase (Cloud) via API REST."""
    url = _get_api_url()
    if not url:
        # Fallback local se não houver Supabase configurado
        _save_json(leads)
        return

    # Pegar closers atuais do Supabase para não perder
    try:
        resp = requests.get(f"{url}?select=username,closer", headers=HEADERS)
        existentes = {i['username']: i['closer'] for i in resp.json()} if resp.status_code == 200 else {}
    except: existentes = {}

    # Preparar dados para Upsert
    payload = []
    for lead in leads:
        username = lead.get("username", "")
        closer = lead.get("closer") or existentes.get(username, "") or ""
        lead_final = {**lead, "closer": closer}
        payload.append({
            "username": username,
            "data": lead_final, # o Supabase aceita JSON direto na coluna JSONB
            "closer": closer,
            "updated_at": "now()"
        })

    try:
        # Upsert: se o username existir, ele ignora ou sobrescreve conforme config
        # Para PostgREST (Supabase), usamos este header para Upsert:
        h = {**HEADERS, "Prefer": "resolution=merge-duplicates"}
        requests.post(url, json=payload, headers=h)
    except Exception as e:
        print(f"Erro ao salvar no Supabase: {e}")
        _save_json(leads)


def load_leads() -> list[dict] | None:
    """Carrega leads do Supabase ou JSON."""
    url = _get_api_url()
    if url:
        try:
            # Query: ordenar por score que está dentro do JSON 'data'
            # O Supabase REST API (PostgREST) aceita ->> para JSON
            target = f"{url}?select=data,closer&order=data->>score.desc.nullslast"
            resp = requests.get(target, headers=HEADERS)
            if resp.status_code == 200:
                rows = resp.json()
                if not rows:
                    # Tentar migrar se Supabase estiver vazio (uma única vez)
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
        except: pass

    # Fallback JSON
    l = _load_json()
    if l: l.sort(key=lambda x: int(x.get("score", 0)), reverse=True)
    return l if l else None


def update_closer(username: str, closer: str) -> None:
    """Atualiza o closer de um lead via PATCH."""
    url = _get_api_url()
    if url:
        try:
            # Pegar o lead atual para manter consistência no JSON
            resp = requests.get(f"{url}?username=eq.{username}", headers=HEADERS)
            if resp.status_code == 200 and resp.json():
                lead = resp.json()[0]['data']
                lead['closer'] = closer
                
                # Update (PATCH)
                requests.patch(
                    f"{url}?username=eq.{username}",
                    json={"closer": closer, "data": lead, "updated_at": "now()"},
                    headers=HEADERS
                )
                return
        except: pass

    # Fallback JSON
    leads = _load_json()
    for l in leads:
        if l.get("username") == username:
            l["closer"] = closer
            break
    _save_json(leads)


def total_leads() -> int:
    url = _get_api_url()
    if url:
        try:
            # Header para contagem rápida
            h = {**HEADERS, "Prefer": "count=exact"}
            resp = requests.head(url, headers=h)
            count = resp.headers.get("Content-Range")
            if count: return int(count.split('/')[-1])
        except: pass
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
