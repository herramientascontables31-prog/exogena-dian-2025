"""
Scraper del Estatuto Tributario colombiano desde leyes.co
Descarga cada artículo y lo guarda en et_articles.json

Uso:
    python et_scraper.py

Resultado: et_articles.json con estructura:
[
  {"numero": "1", "titulo": "Origen de la obligación sustancial", "texto": "...", "url": "..."},
  ...
]
"""
import asyncio
import json
import logging
import re
import sys
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

BASE = "https://leyes.co/se_expide_el_estatuto_tributario_de_los_impuestos_administrados_por_la_direccion_general_de_impuestos_nacionales"
INDEX_URL = "https://leyes.co/estatuto_tributario.htm"
OUTPUT = Path(__file__).parent / "et_articles.json"

# Sufijos conocidos del ET (artículos como 107-1, 240-1, etc.)
SUFIJOS = ["", "-1", "-2", "-3", "-4", "-5"]

# Rango principal de artículos del ET: 1 a 916
# Algunos artículos tienen el sufijo "o" en la URL (1o.htm, 2o.htm, etc.)
# Otros son directos (107.htm, 240.htm)


def _build_article_urls() -> list[tuple[str, str]]:
    """Genera lista de (numero_display, url) para todos los artículos posibles."""
    urls = []

    for num in range(1, 920):
        for sufijo in SUFIJOS:
            art_id = f"{num}{sufijo}"
            # leyes.co usa formato: 1o.htm para artículo 1, 107.htm para 107, 107-1.htm para 107-1
            # Probar ambos formatos para los primeros artículos
            if sufijo == "":
                # Formato con "o" (1o.htm) y sin (1.htm)
                urls.append((art_id, f"{BASE}/{num}o.htm"))
                urls.append((art_id, f"{BASE}/{num}.htm"))
            else:
                urls.append((art_id, f"{BASE}/{num}{sufijo}.htm"))

    # Artículos especiales conocidos
    special = ["57-1bis", "235-3", "235-4", "240-1", "259-1", "292-3", "292-4",
               "331", "332", "333", "334", "335", "336", "383", "388"]
    for s in special:
        urls.append((s, f"{BASE}/{s}.htm"))

    return urls


def _extract_article(html: str, url: str) -> dict | None:
    """Extrae número, título y texto de un artículo desde el HTML."""
    soup = BeautifulSoup(html, "lxml")

    # El contenido del artículo está en <div id="statya">
    statya = soup.find("div", id="statya")
    if not statya:
        return None

    # Extraer título del h1 dentro de statya (o global)
    h1 = statya.find("h1") or soup.find("h1")
    if not h1:
        return None

    titulo_text = h1.get_text(strip=True)
    numero = ""
    titulo = ""

    m = re.search(r"Art[íi]culo\s+([\d]+(?:o|[-]\d+)?(?:\s*bis)?)[.\s]*(.+)?", titulo_text, re.IGNORECASE)
    if m:
        numero = m.group(1).rstrip("o").strip()
        titulo = (m.group(2) or "").strip().rstrip(".")
    else:
        return None

    # Extraer texto solo del div#statya
    # Remover scripts/styles dentro
    for tag in statya.find_all(["script", "style"]):
        tag.decompose()

    # Obtener texto limpio del div#statya
    article_text = statya.get_text(separator="\n", strip=True)

    # Limpiar: remover la línea del título de la ley que se repite
    lines = article_text.split("\n")
    clean_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Saltar el encabezado de la ley y la línea del artículo
        if "Estatuto Tributario de los Impuestos Administrados" in line:
            continue
        if line.startswith("Artículo") and titulo and titulo[:20] in line:
            # Incluir esta línea (es el título del artículo con su texto)
            clean_lines.append(line)
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


async def _fetch_index(client: httpx.AsyncClient) -> list[tuple[str, str]]:
    """Intenta obtener la lista de artículos del índice oficial."""
    urls = []
    try:
        resp = await client.get(INDEX_URL)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            links = soup.find_all("a", href=True)
            for link in links:
                href = link["href"]
                if "/se_expide_el_estatuto_tributario" in href and href.endswith(".htm"):
                    text = link.get_text(strip=True)
                    m = re.match(r"Art[íi]culo\s+([\d\w\-]+)", text, re.IGNORECASE)
                    if m:
                        art_num = m.group(1).rstrip("o")
                        full_url = href if href.startswith("http") else f"https://leyes.co{href}"
                        urls.append((art_num, full_url))
            log.info("Índice: encontrados %d artículos", len(urls))
    except Exception as e:
        log.warning("No se pudo leer índice: %s", e)
    return urls


async def scrape_all():
    """Descarga todos los artículos del ET."""
    articles = {}  # numero -> article dict (dedup)

    async with httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        headers={"User-Agent": "ExogenaDIAN-ETScraper/1.0 (educational)"},
    ) as client:

        # Paso 1: intentar obtener URLs del índice
        log.info("Paso 1: Leyendo índice...")
        index_urls = await _fetch_index(client)

        # Paso 2: si el índice no dio suficientes, usar fuerza bruta
        if len(index_urls) < 100:
            log.info("Índice incompleto (%d). Generando URLs por fuerza bruta...", len(index_urls))
            all_urls = _build_article_urls()
        else:
            all_urls = index_urls

        log.info("Total URLs a probar: %d", len(all_urls))

        # Paso 3: descargar en lotes de 10 (respetar el servidor)
        batch_size = 10
        total = len(all_urls)
        fetched = 0
        errors = 0

        for i in range(0, total, batch_size):
            batch = all_urls[i:i + batch_size]
            tasks = []

            for art_id, url in batch:
                tasks.append(_fetch_one(client, art_id, url))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    errors += 1
                    continue
                if result is not None:
                    num = result["numero"]
                    # Dedup: quedarse con el que tenga más texto
                    if num not in articles or len(result["texto"]) > len(articles[num]["texto"]):
                        articles[num] = result
                        fetched += 1

            if (i // batch_size) % 20 == 0:
                log.info("Progreso: %d/%d URLs, %d artículos encontrados, %d errores",
                         i + len(batch), total, len(articles), errors)

            # Pausa entre lotes para no saturar
            await asyncio.sleep(0.3)

    # Ordenar por número
    sorted_articles = sorted(articles.values(), key=lambda a: _sort_key(a["numero"]))

    log.info("✓ Total artículos extraídos: %d", len(sorted_articles))

    # Guardar
    OUTPUT.write_text(json.dumps(sorted_articles, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("✓ Guardado en %s", OUTPUT)

    return sorted_articles


async def _fetch_one(client: httpx.AsyncClient, art_id: str, url: str) -> dict | None:
    """Descarga y parsea un artículo individual."""
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
    """Clave de ordenamiento para artículos (107 < 107-1 < 108)."""
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


if __name__ == "__main__":
    start = time.time()
    result = asyncio.run(scrape_all())
    elapsed = time.time() - start
    print(f"\nCompletado: {len(result)} artículos en {elapsed:.0f}s")
