"""
storage.py — Persistência de leads em JSON fixo no projeto.

Fluxo:
  1. Você processa os leads localmente.
  2. Clica em "Salvar para equipe" → grava data/leads.json.
  3. git push → deploy atualiza.
  4. Equipe abre a URL → carrega leads.json automaticamente.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

LEADS_FILE = DATA_DIR / "leads.json"


def save_leads(leads: list[dict]) -> None:
    """Salva os leads no arquivo fixo do projeto."""
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, default=str, indent=2)


def load_leads() -> list[dict] | None:
    """Carrega os leads salvos. Retorna None se o arquivo não existir."""
    if not LEADS_FILE.exists():
        return None
    with open(LEADS_FILE, encoding="utf-8") as f:
        return json.load(f)
