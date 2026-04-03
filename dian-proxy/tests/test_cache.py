"""Tests para el sistema de caché de NIT."""
import time
from unittest.mock import patch

from cache import NITCache


class TestNITCache:
    def setup_method(self):
        self.cache = NITCache(ttl_days=1)
        self.cache.data = {}  # Start clean

    def test_set_and_get(self):
        self.cache.set("800197268", {"razon_social": "TEST S.A.S", "fuente": "DIAN"})
        result = self.cache.get("800197268")
        assert result is not None
        assert result["razon_social"] == "TEST S.A.S"
        assert result["cached"] is True

    def test_get_nonexistent_returns_none(self):
        assert self.cache.get("999999999") is None

    def test_strips_nit(self):
        self.cache.set(" 800197268 ", {"razon_social": "TEST"})
        assert self.cache.get("800197268") is not None

    def test_expired_returns_none(self):
        self.cache.set("800197268", {"razon_social": "TEST"})
        # Forzar expiración
        self.cache.data["800197268"]["_cached_at"] = time.time() - 200000
        assert self.cache.get("800197268") is None

    def test_internal_fields_excluded(self):
        self.cache.set("800197268", {"razon_social": "TEST"})
        result = self.cache.get("800197268")
        assert "_cached_at" not in result

    def test_stats(self):
        self.cache.set("111111", {"razon_social": "A"})
        self.cache.set("222222", {"razon_social": "B"})
        stats = self.cache.stats()
        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 2

    def test_stats_expired_entries(self):
        self.cache.set("111111", {"razon_social": "A"})
        self.cache.data["111111"]["_cached_at"] = 0  # Expired
        self.cache.set("222222", {"razon_social": "B"})
        stats = self.cache.stats()
        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 1


class TestDVCalculation:
    """Verificar cálculo del dígito de verificación DIAN."""

    def test_dv_known_values(self):
        from fallback import _calc_dv
        # DIAN: 800197268-4
        assert _calc_dv("800197268") == 4
        # Cuantías menores
        assert _calc_dv("222222222") in range(0, 10)  # Any valid DV

    def test_dv_deterministic(self):
        from fallback import _calc_dv
        dv1 = _calc_dv("900123456")
        dv2 = _calc_dv("900123456")
        assert dv1 == dv2
