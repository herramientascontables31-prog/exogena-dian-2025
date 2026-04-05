"""
Módulo de búsqueda semántica sobre el Estatuto Tributario.
Carga embeddings en memoria al inicio y busca por coseno.

Uso en ia.py:
    from et_search import et_engine
    results = await et_engine.search("retención en la fuente honorarios", top_k=5)
"""
import json
import logging
import os
import re
from pathlib import Path

import httpx
import numpy as np

logger = logging.getLogger("exogenadian.et_search")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
EMBEDDING_MODEL = "gemini-embedding-001"
EMBED_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent"
ET_DATA_FILE = Path(__file__).parent / "et_data.json"
# Formato comprimido (preferido)
ET_NPZ_FILE = Path(__file__).parent / "et_embeddings.npz"
ET_META_FILE = Path(__file__).parent / "et_articles_meta.json"


class ETSearchEngine:
    """Motor de búsqueda semántica sobre artículos del ET."""

    def __init__(self):
        self._loaded = False
        self._articles: list[dict] = []
        self._embeddings: np.ndarray | None = None
        self._articles_index: dict[str, str] = {}  # numero -> titulo

    def load(self):
        """Carga embeddings en memoria. Prefiere formato comprimido (.npz + meta)."""
        if self._loaded:
            return

        try:
            if ET_NPZ_FILE.exists() and ET_META_FILE.exists():
                self._load_compressed()
            elif ET_DATA_FILE.exists():
                self._load_legacy()
            else:
                logger.warning("No hay datos del ET. RAG deshabilitado. Ejecuta et_scraper.py + et_embeddings.py + et_compress.py")
                return
        except Exception as e:
            logger.error("Error cargando datos del ET: %s", e)

    def _load_compressed(self):
        """Carga desde formato comprimido: npz (embeddings) + json (metadata)."""
        meta = json.loads(ET_META_FILE.read_text(encoding="utf-8"))
        self._articles_index = meta.get("articles_index", {})
        self._articles = meta.get("articles", [])

        # Cargar embeddings float16 → float32 para cálculo
        npz = np.load(ET_NPZ_FILE)
        self._embeddings = npz["embeddings"].astype(np.float32)

        # Normalizar
        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        self._embeddings = self._embeddings / norms

        self._loaded = True
        logger.info("ET Search cargado (comprimido): %d artículos (%d dims)",
                    len(self._articles), self._embeddings.shape[1])

    def _load_legacy(self):
        """Carga desde et_data.json (formato original con embeddings inline)."""
        data = json.loads(ET_DATA_FILE.read_text(encoding="utf-8"))
        articles = data.get("articles", [])
        self._articles_index = data.get("articles_index", {})

        valid = [a for a in articles if a.get("embedding") and len(a["embedding"]) > 0]
        if not valid:
            logger.warning("No hay embeddings válidos en et_data.json")
            return

        self._articles = valid
        self._embeddings = np.array([a["embedding"] for a in valid], dtype=np.float32)

        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        self._embeddings = self._embeddings / norms

        self._loaded = True
        logger.info("ET Search cargado (legacy): %d artículos (%d dims)",
                    len(self._articles), self._embeddings.shape[1])

    @property
    def is_available(self) -> bool:
        return self._loaded and self._embeddings is not None

    @property
    def articles_index(self) -> dict[str, str]:
        """Devuelve diccionario numero->titulo de todos los artículos del ET."""
        return self._articles_index

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Busca artículos del ET relevantes para la consulta.
        Retorna lista de dicts con: numero, titulo, texto, score, url
        """
        if not self.is_available:
            return []

        if not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY no disponible para generar embedding de consulta")
            return []

        try:
            # Generar embedding de la consulta
            query_emb = await self._embed_query(query)
            if query_emb is None:
                return []

            # Normalizar
            query_vec = np.array(query_emb, dtype=np.float32)
            norm = np.linalg.norm(query_vec)
            if norm > 0:
                query_vec = query_vec / norm

            # Coseno = dot product (ya normalizado)
            scores = self._embeddings @ query_vec

            # Top-k
            top_indices = np.argsort(scores)[-top_k:][::-1]

            results = []
            for idx in top_indices:
                art = self._articles[idx]
                score = float(scores[idx])
                if score < 0.3:  # Threshold mínimo de relevancia
                    continue
                results.append({
                    "numero": art["numero"],
                    "titulo": art.get("titulo", ""),
                    "texto": art.get("texto", "")[:2000],  # Truncar para el prompt
                    "score": round(score, 4),
                    "url": art.get("url", ""),
                })

            return results

        except Exception as e:
            logger.error("Error en búsqueda semántica: %s", e)
            return []

    async def _embed_query(self, text: str) -> list[float] | None:
        """Genera embedding para una consulta."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{EMBED_URL}?key={GEMINI_API_KEY}",
                    json={
                        "model": f"models/{EMBEDDING_MODEL}",
                        "content": {"parts": [{"text": text}]},
                    },
                )
                if resp.status_code != 200:
                    logger.error("Embedding API error %s: %s", resp.status_code, resp.text[:200])
                    return None
                return resp.json()["embedding"]["values"]
        except Exception as e:
            logger.error("Error generando embedding de consulta: %s", e)
            return None

    def validate_articles(self, text: str) -> list[dict]:
        """
        Extrae artículos citados en un texto y valida si existen en el ET.
        Retorna lista de dicts: {numero, titulo, verificado}
        """
        # Patrones: "Art. 107", "Artículo 107", "Art. 107-1", "Art 240 ET"
        pattern = r'(?:Art[íi]culo|Art)\.?\s*(\d+(?:-\d+)?(?:\s*bis)?)'
        matches = re.findall(pattern, text, re.IGNORECASE)

        # Dedup manteniendo orden
        seen = set()
        results = []
        for match in matches:
            num = match.strip()
            if num in seen:
                continue
            seen.add(num)

            if num in self._articles_index:
                results.append({
                    "numero": num,
                    "titulo": self._articles_index[num],
                    "verificado": True,
                })
            else:
                results.append({
                    "numero": num,
                    "titulo": "",
                    "verificado": False,
                })

        return results


# Singleton global
et_engine = ETSearchEngine()
