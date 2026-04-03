"""
Tests para el API de ExógenaDIAN.
Ejecutar: cd dian-proxy && python -m pytest tests/ -v
"""
import time
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app, _clean_nit, _build_response, RateLimiter, ProCredits


# ═══════════════════════════════════════════════════════════════
#  Unit tests — funciones puras
# ═══════════════════════════════════════════════════════════════

class TestCleanNit:
    def test_removes_dots(self):
        assert _clean_nit("800.197.268") == "800197268"

    def test_removes_spaces(self):
        assert _clean_nit(" 800197268 ") == "800197268"

    def test_removes_dv(self):
        assert _clean_nit("800197268-4") == "800197268"

    def test_strips_all(self):
        assert _clean_nit(" 800.197.268-4 ") == "800197268"

    def test_empty(self):
        assert _clean_nit("") == ""


class TestBuildResponse:
    def test_basic_fields(self):
        r = _build_response({"nit": "800197268", "razon_social": "TEST"})
        assert r["nit"] == "800197268"
        assert r["razon_social"] == "TEST"
        assert "timestamp" in r

    def test_calculates_dv(self):
        r = _build_response({"nit": "800197268"})
        assert r["dv"] is not None

    def test_defaults(self):
        r = _build_response({"nit": "123456"})
        assert r["error"] == ""
        assert r["razon_social"] == ""
        assert r["cached"] is False
        assert r["responsabilidades"] == []


class TestRateLimiter:
    def test_allows_first_request(self):
        rl = RateLimiter()
        allowed, remaining = rl.check("1.2.3.4")
        assert allowed is True
        assert remaining == 10

    def test_decrements_remaining(self):
        rl = RateLimiter()
        rl.consume("1.2.3.4")
        rl.consume("1.2.3.4")
        assert rl.get_remaining("1.2.3.4") == 8

    def test_blocks_after_limit(self):
        rl = RateLimiter()
        for _ in range(10):
            rl.consume("1.2.3.4")
        allowed, remaining = rl.check("1.2.3.4")
        assert allowed is False
        assert remaining == 0

    def test_different_ips_independent(self):
        rl = RateLimiter()
        for _ in range(10):
            rl.consume("1.1.1.1")
        allowed, _ = rl.check("2.2.2.2")
        assert allowed is True


class TestProCredits:
    def test_initial_credits(self):
        pc = ProCredits(monthly_limit=500)
        assert pc.get_remaining("PRO-TEST") == 500

    def test_consume_reduces(self):
        pc = ProCredits(monthly_limit=500)
        pc.consume("PRO-TEST", 10)
        assert pc.get_remaining("PRO-TEST") == 490

    def test_can_consume_check(self):
        pc = ProCredits(monthly_limit=5)
        pc.consume("PRO-TEST", 5)
        assert pc.can_consume("PRO-TEST", 1) is False

    def test_different_keys_independent(self):
        pc = ProCredits(monthly_limit=10)
        pc.consume("KEY-A", 10)
        assert pc.get_remaining("KEY-B") == 10


# ═══════════════════════════════════════════════════════════════
#  Integration tests — endpoints del API
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def transport():
    return ASGITransport(app=app)


@pytest.mark.asyncio
async def test_health_endpoint(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "circuit_breaker" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_remaining_endpoint(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/remaining")
    assert resp.status_code == 200
    data = resp.json()
    assert "remaining" in data
    assert "daily_limit" in data
    assert data["is_pro"] is False


@pytest.mark.asyncio
async def test_nit_invalid_returns_error(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/nit/123")  # too short
    assert resp.status_code == 200
    data = resp.json()
    assert "inválido" in data["error"].lower() or "invalido" in data["error"].lower()


@pytest.mark.asyncio
async def test_nit_valid_format(transport):
    """Un NIT válido debe retornar la estructura correcta (aunque no encuentre datos)."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/nit/800197268")
    assert resp.status_code == 200
    data = resp.json()
    assert data["nit"] == "800197268"
    assert "dv" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_bulk_empty_returns_400(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/nit/bulk", json={"nits": []})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_bulk_free_limit(transport):
    """Free tier: más de 10 NITs debe retornar 403."""
    nits = [str(100000 + i) for i in range(15)]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/nit/bulk", json={"nits": nits})
    assert resp.status_code == 403
    data = resp.json()
    assert "upgrade_required" in str(data)


@pytest.mark.asyncio
async def test_bulk_within_limit(transport):
    """Free tier: hasta 10 NITs debe funcionar."""
    nits = ["800197268", "900123456"]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/nit/bulk", json={"nits": nits})
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_security_headers(transport):
    """Verificar que los headers de seguridad estén presentes."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


@pytest.mark.asyncio
async def test_cors_headers(transport):
    """Verificar CORS para origin permitido."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.options(
            "/api/health",
            headers={
                "Origin": "https://exogenadian.com",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert "access-control-allow-origin" in resp.headers


@pytest.mark.asyncio
async def test_pro_validation_rejects_fake_key(transport):
    """Una clave PRO inventada no debe dar acceso PRO."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/remaining",
            headers={"X-Pro-Key": "FAKE-KEY-12345"},
        )
    data = resp.json()
    assert data["is_pro"] is False


@pytest.mark.asyncio
async def test_stats_endpoint(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "cache" in data
    assert "circuit_breaker" in data
