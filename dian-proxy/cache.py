"""
Caché in-memory con TTL para resultados de consulta NIT.
Persiste a disco como JSON para sobrevivir reinicios.
"""
import json
import os
import time
from pathlib import Path

CACHE_FILE = Path(__file__).parent / "cache_data.json"
DEFAULT_TTL = 30 * 24 * 3600  # 30 días en segundos


class NITCache:
    def __init__(self, ttl_days: int = 7):
        self.ttl = ttl_days * 24 * 3600
        self.data: dict[str, dict] = {}
        self._load()

    def _load(self):
        """Cargar caché desde disco al iniciar."""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                # Filtrar entradas expiradas al cargar
                now = time.time()
                self.data = {
                    k: v for k, v in raw.items()
                    if now - v.get("_cached_at", 0) < self.ttl
                }
            except (json.JSONDecodeError, OSError):
                self.data = {}

    def _save(self):
        """Persistir caché a disco."""
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=None)
        except OSError:
            pass  # En Cloud Run el disco es efímero, no es crítico

    def get(self, nit: str) -> dict | None:
        """Obtener resultado cacheado. Retorna None si no existe o expiró."""
        nit = str(nit).strip()
        entry = self.data.get(nit)
        if not entry:
            return None
        if time.time() - entry.get("_cached_at", 0) > self.ttl:
            del self.data[nit]
            return None
        result = {k: v for k, v in entry.items() if not k.startswith("_")}
        result["cached"] = True
        return result

    def set(self, nit: str, result: dict):
        """Guardar resultado en caché."""
        nit = str(nit).strip()
        entry = {**result, "_cached_at": time.time()}
        self.data[nit] = entry
        # Persistir cada 10 escrituras para no escribir en cada request
        if len(self.data) % 10 == 0:
            self._save()

    def flush(self):
        """Forzar escritura a disco."""
        self._save()

    def stats(self) -> dict:
        """Estadísticas del caché."""
        now = time.time()
        valid = sum(1 for v in self.data.values() if now - v.get("_cached_at", 0) < self.ttl)
        return {"total_entries": len(self.data), "valid_entries": valid}


# Singleton
_cache_instance: NITCache | None = None


def get_cache(ttl_days: int = 7) -> NITCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = NITCache(ttl_days)
    return _cache_instance
