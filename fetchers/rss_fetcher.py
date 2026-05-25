"""
Fetcher RSS — coleta artigos e newsletters das fontes configuradas.
Suporta feeds Atom e RSS 2.0.
"""

import asyncio
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime


async def fetch_rss_sources(sources: list[dict], max_per_source: int = 5) -> list[dict]:
    """Coleta RSS de todas as fontes em paralelo."""
    async with httpx.AsyncClient(
        timeout=20,
        follow_redirects=True,
        headers={"User-Agent": "MorningDigestBot/1.0 (research aggregator)"},
    ) as client:
        tasks = [_fetch_one(client, src, max_per_source) for src in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    items = []
    for r in results:
        if not isinstance(r, Exception):
            items.extend(r)
    return items


async def _fetch_one(client: httpx.AsyncClient, source: dict, max_items: int) -> list[dict]:
    try:
        resp = await client.get(source["url"])
        resp.raise_for_status()
        return _parse_feed(resp.text, source, max_items)
    except Exception as exc:
        return []  # Feed indisponível — ignora silenciosamente


def _parse_feed(xml_text: str, source: dict, max_items: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    # Detecta se é Atom ou RSS
    tag = root.tag.lower()
    if "feed" in tag:
        return _parse_atom(root, source, max_items, cutoff)
    else:
        return _parse_rss2(root, source, max_items, cutoff)


def _parse_atom(root: ET.Element, source: dict, max_items: int, cutoff: datetime) -> list[dict]:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = []
    for entry in root.findall("atom:entry", ns)[:max_items * 2]:
        published_str = (
            entry.findtext("atom:published", None, ns)
            or entry.findtext("atom:updated", None, ns)
            or ""
        )
        pub = _parse_date(published_str)
        if pub and pub < cutoff:
            continue

        link_el = entry.find("atom:link[@rel='alternate']", ns) or entry.find("atom:link", ns)
        url = link_el.get("href", "") if link_el is not None else ""

        summary_el = entry.find("atom:summary", ns) or entry.find("atom:content", ns)
        summary = _strip_html(summary_el.text or "") if summary_el is not None else ""

        items.append(_make_item(source, entry.findtext("atom:title", "", ns), summary, url, pub))
        if len(items) >= max_items:
            break
    return items


def _parse_rss2(root: ET.Element, source: dict, max_items: int, cutoff: datetime) -> list[dict]:
    items = []
    for item in root.findall(".//item")[:max_items * 2]:
        pub = _parse_date(item.findtext("pubDate", ""))
        if pub and pub < cutoff:
            continue

        desc = _strip_html(item.findtext("description", ""))
        items.append(_make_item(
            source,
            item.findtext("title", ""),
            desc,
            item.findtext("link", ""),
            pub,
        ))
        if len(items) >= max_items:
            break
    return items


def _make_item(source: dict, title: str, description: str, url: str, pub) -> dict:
    return {
        "source": source["name"],
        "category": source.get("category", "news"),
        "type": "article",
        "title": (title or "").strip().replace("\n", " ")[:200],
        "abstract": (description or "").strip()[:600],
        "authors": "",
        "url": url.strip(),
        "published": pub.strftime("%Y-%m-%d") if pub else "unknown",
    }


def _parse_date(date_str: str):
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str).astimezone(timezone.utc)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return None


def _strip_html(text: str) -> str:
    """Remove tags HTML do texto."""
    import re
    clean = re.sub(r"<[^>]+>", " ", text or "")
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:600]
