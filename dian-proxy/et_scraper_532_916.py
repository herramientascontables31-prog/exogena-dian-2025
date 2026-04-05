"""
Scraper incremental: artículos 532-916 del ET desde leyes.co
Agrega los nuevos artículos al et_articles.json existente.

Uso:
    python et_scraper_532_916.py
"""
import asyncio
import json
import logging
import re
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

BASE = "https://leyes.co/se_expide_el_estatuto_tributario_de_los_impuestos_administrados_por_la_direccion_general_de_impuestos_nacionales"
ARTICLES_FILE = Path(__file__).parent / "et_articles.json"

SUFIJOS = ["", "-1", "-2", "-3", "-4", "-5"]


def _extract_article(html: str, url: str) -> dict | None:
    """Extrae número, título y texto de un artículo desde el HTML."""
    soup = BeautifulSoup(html, "lxml")
    statya = soup.find("div", id="statya")
    if not statya:
        return None

    h1 = statya.find("h1") or soup.find("h1")
    if not h1:
        return None

    titulo_text = h1.get_text(strip=True)
    m = re.search(r"Art[íi]culo\s+([\d]+(?:o|[-]\d+)?(?:\s*bis)?)[.\s]*(.+)?", titulo_text, re.IGNORECASE)
    if not m:
        return None

    numero = m.group(1).rstrip("o").strip()
    titulo = (m.group(2) or "").strip().rstrip(".")

    for tag in statya.find_all(["script", "style"]):
        tag.decompose()

    article_text = statya.get_text(separator="\n", strip=True)
    lines = article_text.split("\n")
    clean_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "Estatuto Tributario de los Impuestos Administrados" in line:
            continue
        clean_lines.append(line)

    article_text = "\n".join(clean_lines)
    if len(article_text) < 15:
        return None

    return {
        "numero": numero,
        "titulo": titulo,
        "texto": article_text[:5000],
        "url": url,
    }


async def _fetch_one(client: httpx.AsyncClient, art_id: str, url: str) -> dict | None:
    try:
        resp = await client.get(url)
        if resp.status_code != 200:
            return None
        article = _extract_article(resp.text, url)
        if article and not article["numero"]:
            article["numero"] = art_id
        return article
    except Exception:
        return None


def _sort_key(numero: str) -> tuple:
    parts = numero.split("-")
    try:
        main = int(re.sub(r"[^\d]", "", parts[0]) or "0")
    except ValueError:
        main = 0
    suffix = parts[1] if len(parts) > 1 else ""
    try:
        suffix_num = int(suffix) if suffix else 0
    except ValueError:
        suffix_num = 99
    return (main, suffix_num)


async def scrape_532_916():
    # Cargar artículos existentes
    existing = json.loads(ARTICLES_FILE.read_text(encoding="utf-8"))
    existing_nums = {a["numero"] for a in existing}
    log.info("Artículos existentes: %d", len(existing))

    # Generar URLs solo para 532-916
    urls = []
    for num in range(532, 920):
        for sufijo in SUFIJOS:
            art_id = f"{num}{sufijo}" if sufijo else str(num)
            if art_id in existing_nums:
                continue
            if sufijo == "":
                urls.append((art_id, f"{BASE}/{num}o.htm"))
                urls.append((art_id, f"{BASE}/{num}.htm"))
            else:
                urls.append((art_id, f"{BASE}/{num}{sufijo}.htm"))

    log.info("URLs a probar: %d", len(urls))

    new_articles = {}

    async with httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        headers={"User-Agent": "ExogenaDIAN-ETScraper/1.0 (educational)"},
    ) as client:
        batch_size = 10
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            tasks = [_fetch_one(client, art_id, url) for art_id, url in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception) or result is None:
                    continue
                num = result["numero"]
                if num not in new_articles or len(result["texto"]) > len(new_articles[num]["texto"]):
                    new_articles[num] = result

            if (i // batch_size) % 20 == 0:
                log.info("Progreso: %d/%d URLs, %d nuevos artículos", i + len(batch), len(urls), len(new_articles))

            await asyncio.sleep(0.3)

    log.info("Nuevos artículos encontrados: %d", len(new_articles))

    # Merge
    all_articles = existing + list(new_articles.values())
    all_articles.sort(key=lambda a: _sort_key(a["numero"]))

    # Dedup
    seen = {}
    deduped = []
    for a in all_articles:
        if a["numero"] not in seen or len(a["texto"]) > len(seen[a["numero"]]["texto"]):
            seen[a["numero"]] = a
    deduped = sorted(seen.values(), key=lambda a: _sort_key(a["numero"]))

    ARTICLES_FILE.write_text(json.dumps(deduped, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("✓ Total guardado: %d artículos en %s", len(deduped), ARTICLES_FILE)
    return deduped


if __name__ == "__main__":
    start = time.time()
    result = asyncio.run(scrape_532_916())
    elapsed = time.time() - start
    print(f"\nCompletado: {len(result)} artículos totales en {elapsed:.0f}s")
