"""
Genera embeddings para cada artículo del ET usando Gemini text-embedding-004.

Uso:
    python et_embeddings.py

Requiere:
    - GEMINI_API_KEY en .env o variable de entorno
    - et_articles.json (generado por et_scraper.py)

Resultado: et_data.json con artículos + embeddings (768 dims cada uno)
"""
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:batchEmbedContents"
SINGLE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent"

ARTICLES_FILE = Path(__file__).parent / "et_articles.json"
OUTPUT_FILE = Path(__file__).parent / "et_data.json"

# Gemini batch embedding soporta hasta 100 textos por request
BATCH_SIZE = 80


def _prepare_text(article: dict) -> str:
    """Prepara el texto para embedding: número + título + texto (truncado a 2000 chars)."""
    parts = []
    if article.get("numero"):
        parts.append(f"Artículo {article['numero']} del Estatuto Tributario.")
    if article.get("titulo"):
        parts.append(article["titulo"])
    if article.get("texto"):
        parts.append(article["texto"])
    text = " ".join(parts)
    # text-embedding-004 soporta hasta 2048 tokens (~8000 chars), truncar conservadoramente
    return text[:4000]


async def generate_embeddings():
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY no configurada. Ponla en .env o como variable de entorno.")
        sys.exit(1)

    if not ARTICLES_FILE.exists():
        print(f"ERROR: No se encuentra {ARTICLES_FILE}. Ejecuta primero: python et_scraper.py")
        sys.exit(1)

    articles = json.loads(ARTICLES_FILE.read_text(encoding="utf-8"))
    log.info("Cargados %d artículos de %s", len(articles), ARTICLES_FILE)

    # Si ya existe et_data.json parcial, cargar para continuar
    existing = {}
    if OUTPUT_FILE.exists():
        try:
            data = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
            for item in data.get("articles", []):
                if item.get("embedding"):
                    existing[item["numero"]] = item["embedding"]
            log.info("Encontrados %d embeddings existentes, continuando...", len(existing))
        except Exception:
            pass

    results = []
    pending = []
    for art in articles:
        if art["numero"] in existing:
            art["embedding"] = existing[art["numero"]]
            results.append(art)
        else:
            pending.append(art)

    log.info("Pendientes: %d artículos", len(pending))

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(0, len(pending), BATCH_SIZE):
            batch = pending[i:i + BATCH_SIZE]
            texts = [_prepare_text(art) for art in batch]

            try:
                embeddings = await _batch_embed(client, texts)

                for art, emb in zip(batch, embeddings):
                    art["embedding"] = emb
                    results.append(art)

                log.info("Batch %d/%d: %d embeddings generados",
                         i // BATCH_SIZE + 1,
                         (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE,
                         len(batch))

            except Exception as e:
                log.error("Error en batch %d: %s. Intentando uno por uno...", i // BATCH_SIZE + 1, e)
                # Fallback: uno por uno
                for art in batch:
                    try:
                        emb = await _single_embed(client, _prepare_text(art))
                        art["embedding"] = emb
                        results.append(art)
                    except Exception as e2:
                        log.error("Error artículo %s: %s", art["numero"], e2)
                        art["embedding"] = None
                        results.append(art)

            # Guardar progreso cada 5 batches
            if (i // BATCH_SIZE) % 5 == 0 and i > 0:
                _save(results)

            await asyncio.sleep(0.2)  # Rate limit

    _save(results)
    valid = sum(1 for r in results if r.get("embedding"))
    log.info("✓ Completado: %d/%d artículos con embedding", valid, len(results))


async def _batch_embed(client: httpx.AsyncClient, texts: list[str]) -> list[list[float]]:
    """Embedding en lote via Gemini API."""
    requests = [
        {"model": f"models/{EMBEDDING_MODEL}", "content": {"parts": [{"text": t}]}}
        for t in texts
    ]
    resp = await client.post(
        f"{EMBEDDING_URL}?key={GEMINI_API_KEY}",
        json={"requests": requests},
    )
    if resp.status_code != 200:
        raise Exception(f"API error {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    return [emb.get("values") or emb["embedding"]["values"] for emb in data["embeddings"]]


async def _single_embed(client: httpx.AsyncClient, text: str) -> list[float]:
    """Embedding individual via Gemini API."""
    resp = await client.post(
        f"{SINGLE_URL}?key={GEMINI_API_KEY}",
        json={
            "model": f"models/{EMBEDDING_MODEL}",
            "content": {"parts": [{"text": text}]},
        },
    )
    if resp.status_code != 200:
        raise Exception(f"API error {resp.status_code}: {resp.text[:300]}")

    return resp.json()["embedding"]["values"]


def _save(results: list[dict]):
    """Guarda resultados parciales/finales."""
    # Crear tabla de artículos válidos (para verificación post-respuesta)
    articles_index = {}
    for art in results:
        if art.get("numero"):
            articles_index[art["numero"]] = art.get("titulo", "")

    output = {
        "model": EMBEDDING_MODEL,
        "dimensions": 3072,
        "total_articles": len(results),
        "articles_index": articles_index,
        "articles": [
            {
                "numero": art["numero"],
                "titulo": art.get("titulo", ""),
                "texto": art.get("texto", ""),
                "embedding": art.get("embedding"),
                "url": art.get("url", ""),
            }
            for art in results
        ],
    }
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8")
    log.info("Guardado parcial: %d artículos en %s", len(results), OUTPUT_FILE)


if __name__ == "__main__":
    start = time.time()
    asyncio.run(generate_embeddings())
    elapsed = time.time() - start
    print(f"\nCompletado en {elapsed:.0f}s")
