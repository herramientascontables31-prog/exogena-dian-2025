"""
Comprime et_data.json en dos archivos más pequeños:
- et_embeddings.npz: embeddings en float16 comprimido (~5MB vs 50MB)
- et_articles_meta.json: texto y metadatos sin embeddings (~2MB)

Uso:
    python et_compress.py
"""
import json
import logging
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

BASE = Path(__file__).parent
ET_DATA = BASE / "et_data.json"
OUT_NPZ = BASE / "et_embeddings.npz"
OUT_META = BASE / "et_articles_meta.json"


def compress():
    data = json.loads(ET_DATA.read_text(encoding="utf-8"))
    articles = data.get("articles", [])
    articles_index = data.get("articles_index", {})

    log.info("Cargados %d artículos", len(articles))

    # Separar embeddings y metadata
    valid_articles = []
    embeddings = []
    for art in articles:
        emb = art.get("embedding")
        if emb and len(emb) > 0:
            valid_articles.append({
                "numero": art["numero"],
                "titulo": art.get("titulo", ""),
                "texto": art.get("texto", ""),
                "url": art.get("url", ""),
            })
            embeddings.append(emb)

    log.info("Artículos válidos con embedding: %d", len(valid_articles))

    # Guardar embeddings como float16 comprimido
    emb_array = np.array(embeddings, dtype=np.float16)
    np.savez_compressed(OUT_NPZ, embeddings=emb_array)
    log.info("Embeddings guardados: %s (dims: %s)", OUT_NPZ, emb_array.shape)

    # Guardar metadata
    meta = {
        "model": data.get("model", "gemini-embedding-001"),
        "dimensions": data.get("dimensions", 3072),
        "total_articles": len(valid_articles),
        "articles_index": articles_index,
        "articles": valid_articles,
    }
    OUT_META.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    log.info("Metadata guardada: %s", OUT_META)

    # Tamaños
    import os
    orig = os.path.getsize(ET_DATA) / 1024 / 1024
    npz = os.path.getsize(OUT_NPZ) / 1024 / 1024
    meta_size = os.path.getsize(OUT_META) / 1024 / 1024
    log.info("Tamaños: original=%.1fMB → embeddings=%.1fMB + meta=%.1fMB = %.1fMB total (%.0f%% reducción)",
             orig, npz, meta_size, npz + meta_size, (1 - (npz + meta_size) / orig) * 100)


if __name__ == "__main__":
    compress()
