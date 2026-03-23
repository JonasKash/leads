"""
rescore_leads.py — Reprocessa o score de todos os leads já salvos.
Roda UMA VEZ fora do Streamlit para corrigir leads com score=0.

Uso:
    python rescore_leads.py
"""

import sys
import json
import sqlite3
from pathlib import Path

# Ajustar path para importar os módulos do app
sys.path.insert(0, str(Path(__file__).parent / "app"))

from scoring.engine import calcular_score

DATA_DIR = Path(__file__).parent / "data"


def rescore_from_json():
    json_path = DATA_DIR / "crm.json"
    if not json_path.exists():
        print("crm.json não encontrado.")
        return False

    with open(json_path, encoding="utf-8") as f:
        leads = json.load(f)

    print(f"Reprocessando {len(leads)} leads do crm.json...")
    rescored = []
    for lead in leads:
        # Garantir campos mínimos para o scorer
        lead.setdefault("oab_situacao", "")
        lead.setdefault("oab_anos_ativo", None)
        lead.setdefault("cnpj_numero", "")
        lead.setdefault("cnpj_situacao", "")
        lead.setdefault("cnpj_cnae_juridico", False)
        lead.setdefault("site_encontrado", False)
        lead.setdefault("has_fb_pixel", False)
        lead.setdefault("has_ga", False)
        lead.setdefault("gmb_encontrado", False)
        lead.setdefault("gmb_reviews", 0)
        lead.setdefault("has_link", bool(lead.get("external_url", "").strip()))
        lead.setdefault("cta_sem_link", False)

        rescored_lead = calcular_score(lead)
        rescored.append(rescored_lead)

    # Salvar de volta
    tmp = json_path.with_suffix(".tmp.json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rescored, f, ensure_ascii=False, indent=2, default=str)
    tmp.replace(json_path)

    scores = [l["score"] for l in rescored]
    quentes = sum(1 for s in scores if s >= 70)
    mornos = sum(1 for s in scores if 45 <= s < 70)
    frios = sum(1 for s in scores if s < 45)
    print(f"✅ Concluído! Distribuição:")
    print(f"   🔥 Quentes (≥70): {quentes}")
    print(f"   🟡 Mornos (45-69): {mornos}")
    print(f"   ❄️  Frios (<45): {frios}")
    print(f"   Score médio: {sum(scores)/len(scores):.1f}")
    return True


def rescore_from_sqlite():
    db_path = DATA_DIR / "crm.db"
    if not db_path.exists():
        print("crm.db não encontrado.")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute("SELECT username, data, closer FROM leads").fetchall()
    except Exception as e:
        print(f"Erro ao ler SQLite: {e}")
        return False

    print(f"Reprocessando {len(rows)} leads do crm.db...")
    rescored = []
    for username, data_json, closer in rows:
        lead = json.loads(data_json)
        lead["closer"] = closer

        # Garantir campos mínimos
        lead.setdefault("oab_situacao", "")
        lead.setdefault("oab_anos_ativo", None)
        lead.setdefault("cnpj_numero", "")
        lead.setdefault("cnpj_situacao", "")
        lead.setdefault("cnpj_cnae_juridico", False)
        lead.setdefault("site_encontrado", False)
        lead.setdefault("has_fb_pixel", False)
        lead.setdefault("has_ga", False)
        lead.setdefault("gmb_encontrado", False)
        lead.setdefault("gmb_reviews", 0)
        lead.setdefault("has_link", bool(lead.get("external_url", "").strip()))
        lead.setdefault("cta_sem_link", False)

        rescored_lead = calcular_score(lead)
        rescored.append(rescored_lead)

    conn.close()

    # Salvar como JSON (novo formato)
    json_path = DATA_DIR / "crm.json"
    tmp = json_path.with_suffix(".tmp.json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rescored, f, ensure_ascii=False, indent=2, default=str)
    tmp.replace(json_path)

    scores = [l["score"] for l in rescored]
    quentes = sum(1 for s in scores if s >= 70)
    mornos = sum(1 for s in scores if 45 <= s < 70)
    frios = sum(1 for s in scores if s < 45)
    print(f"✅ Concluído! Distribuição:")
    print(f"   🔥 Quentes (≥70): {quentes}")
    print(f"   🟡 Mornos (45-69): {mornos}")
    print(f"   ❄️  Frios (<45): {frios}")
    print(f"   Score médio: {sum(scores)/len(scores):.1f}")
    return True


if __name__ == "__main__":
    print("=== Rescore de Leads ===")
    if not rescore_from_json():
        rescore_from_sqlite()
    print("\nReinicie o Streamlit para ver os resultados atualizados.")
