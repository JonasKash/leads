"""
site_checker.py — Verifica site do advogado, detecta pixels de rastreamento
e obtém score de PageSpeed.
"""

import os
import re
import time
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "")
DELAY_GOOGLE = float(os.getenv("DELAY_GOOGLE", "1.2"))
DELAY_PAGESPEED = float(os.getenv("DELAY_PAGESPEED", "0.5"))

_session = requests.Session()
_session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
})

# Padrões de rastreamento
PIXEL_FB_RE = re.compile(r"fbq\s*\(|facebook\.net/en_US/fbevents\.js", re.IGNORECASE)
GA_RE = re.compile(r"gtag\s*\(|UA-\d{4,}-\d|G-[A-Z0-9]{8,}|GTM-[A-Z0-9]{4,}", re.IGNORECASE)
GADS_RE = re.compile(r"AW-\d{7,}", re.IGNORECASE)


def _google_cse_search(query: str) -> str:
    """Faz uma busca no Google CSE e retorna a primeira URL encontrada."""
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        return ""
    try:
        resp = _session.get(
            "https://www.googleapis.com/customsearch/v1",
            params={"key": GOOGLE_API_KEY, "cx": GOOGLE_CSE_ID, "q": query, "num": 1},
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return items[0]["link"] if items else ""
    except Exception:
        return ""
    finally:
        time.sleep(DELAY_GOOGLE)


def _fetch_html(url: str) -> str:
    """Busca o HTML de uma URL com timeout."""
    try:
        resp = _session.get(url, timeout=12, allow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return ""


def _detect_pixels(html: str) -> dict:
    """Detecta pixels de rastreamento no HTML."""
    return {
        "has_fb_pixel": bool(PIXEL_FB_RE.search(html)),
        "has_ga": bool(GA_RE.search(html)),
        "has_google_ads": bool(GADS_RE.search(html)),
    }


def _get_pagespeed_score(url: str) -> int | None:
    """Obtém o score de PageSpeed Mobile via API do Google."""
    if not GOOGLE_API_KEY:
        return None
    try:
        resp = _session.get(
            "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
            params={"url": url, "strategy": "mobile", "key": GOOGLE_API_KEY},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        score = (
            data.get("lighthouseResult", {})
            .get("categories", {})
            .get("performance", {})
            .get("score")
        )
        return int(score * 100) if score is not None else None
    except Exception:
        return None
    finally:
        time.sleep(DELAY_PAGESPEED)


def check_site(external_url: str, full_name: str = "", city: str = "") -> dict:
    """
    Verifica o site do advogado. Se não tiver external_url, busca via Google CSE.

    Returns:
        {
            site_url: str,
            site_encontrado: bool,
            has_fb_pixel: bool,
            has_ga: bool,
            has_google_ads: bool,
            pagespeed_score: int | None,
            digital_score: int,       # 0-100 score de presença digital
        }
    """
    empty = {
        "site_url": "",
        "site_encontrado": False,
        "has_fb_pixel": False,
        "has_ga": False,
        "has_google_ads": False,
        "pagespeed_score": None,
        "digital_score": 0,
    }

    url = external_url.strip() if external_url else ""

    # Tentar encontrar via Google CSE se não tiver URL
    if not url and GOOGLE_API_KEY:
        query = f'"{full_name}" advogado site'
        if city:
            query += f" {city}"
        url = _google_cse_search(query)

    if not url:
        return empty

    # Garantir protocolo
    if not url.startswith("http"):
        url = "https://" + url

    html = _fetch_html(url)
    if not html:
        return {**empty, "site_url": url}

    pixels = _detect_pixels(html)
    pagespeed = _get_pagespeed_score(url)

    # Calcular digital_score (0-100)
    score = 30  # base: tem site
    if pixels["has_fb_pixel"]:
        score += 25
    if pixels["has_ga"]:
        score += 20
    if pixels["has_google_ads"]:
        score += 15
    if pagespeed is not None:
        score += min(10, pagespeed // 10)

    return {
        "site_url": url,
        "site_encontrado": True,
        "has_fb_pixel": pixels["has_fb_pixel"],
        "has_ga": pixels["has_ga"],
        "has_google_ads": pixels["has_google_ads"],
        "pagespeed_score": pagespeed,
        "digital_score": min(score, 100),
    }
