"""
Fetcher para o ArXiv — usa a API de pesquisa oficial.
Busca papers mais recentes em cs.AI, cs.LG, cs.CL e quant-ph.
"""

import asyncio
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone


ARXIV_API = "https://export.arxiv.org/api/query"


async def fetch_arxiv(queries: list[str], max_per_query: int = 3) -> list[dict]:
    """
    Busca papers do ArXiv para cada categoria.
    Retorna apenas papers das últimas 24h.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [_fetch_category(client, q, max_per_query) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    items = []
    for r in results:
        if isinstance(r, Exception):
            continue
        items.extend(r)

    return items


async def _fetch_category(client: httpx.AsyncClient, query: str, max_results: int) -> list[dict]:
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    resp = await client.get(ARXIV_API, params=params)
    resp.raise_for_status()
    return _parse_arxiv_xml(resp.text, query)


def _parse_arxiv_xml(xml_text: str, category: str) -> list[dict]:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml_text)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=96)

    items = []
    for entry in root.findall("atom:entry", ns):
        published_str = entry.findtext("atom:published", "", ns)
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except Exception:
            continue

        if published < cutoff:
            continue

        # Autores
        authors = [
            a.findtext("atom:name", "", ns)
            for a in entry.findall("atom:author", ns)
        ]

        # Link do paper
        link = ""
        for link_el in entry.findall("atom:link", ns):
            if link_el.get("rel") == "alternate":
                link = link_el.get("href", "")
                break

        items.append({
            "source": "ArXiv",
            "category": category,
            "type": "paper",
            "title": (entry.findtext("atom:title", "", ns) or "").strip().replace("\n", " "),
            "abstract": (entry.findtext("atom:summary", "", ns) or "").strip().replace("\n", " ")[:800],
            "authors": ", ".join(authors[:4]),
            "url": link,
            "published": published.strftime("%Y-%m-%d"),
        })

    return items
