"""
Fetcher para Papers with Code (paperswithcode.com).
Usa a API pública para pegar os papers mais recentes com código disponível.
"""

import asyncio
import httpx
from datetime import datetime, timedelta, timezone


PWC_API = "https://paperswithcode.com/api/v1/papers/"


async def fetch_web_sources(max_items: int = 5) -> list[dict]:
    """Busca papers recentes com código no Papers with Code."""
    params = {
        "ordering": "-published",
        "page_size": max_items,
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(PWC_API, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=96)
    items = []

    for paper in (data.get("results") or [])[:max_items]:
        pub_str = paper.get("published", "") or ""
        try:
            pub = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        except Exception:
            pub = None

        if pub and pub < cutoff:
            continue

        items.append({
            "source": "Papers with Code",
            "category": "paper",
            "type": "paper",
            "title": paper.get("title", "").strip(),
            "abstract": (paper.get("abstract") or "").strip()[:700],
            "authors": ", ".join((paper.get("authors") or [])[:4]),
            "url": paper.get("url_pdf") or f"https://paperswithcode.com/paper/{paper.get('id','')}",
            "published": pub.strftime("%Y-%m-%d") if pub else "unknown",
            "has_code": True,
        })

    return items
