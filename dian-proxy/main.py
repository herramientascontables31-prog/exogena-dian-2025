"""
ExógenaDIAN — Backend Proxy para Consulta de NIT en DIAN MUISCA
FastAPI + Playwright + CapSolver + Caché + Rate Limiting + Circuit Breaker

Límites:
  10 consultas DIAN/día por IP (gratis, sin PRO)

Endpoints:
  GET  /api/nit/{nit}         — Consulta individual
  GET  /api/remaining         — Consultas restantes hoy
  GET  /api/health            — Health check + estado circuit breaker
  GET  /api/stats             — Estadísticas
"""
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from cache import get_cache
from dian_scraper import consultar_dian, circuit_breaker
from fallback import consultar_fallback, _calc_dv

logger = logging.getLogger("exogenadian")

load_dotenv()

# ─── Config ───
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://exogenadian.com").split(",")
CACHE_TTL_DAYS = int(os.getenv("CACHE_TTL_DAYS", "30"))
PORT = int(os.getenv("PORT", "8080"))
STATS_API_KEY = os.getenv("STATS_API_KEY", "")
FREE_DIAN_QUERIES_PER_DAY = 10

# ─── Lifespan ───
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app):
    # Cargar motor de búsqueda semántica del ET (RAG)
    from et_search import et_engine
    et_engine.load()
    yield
    cache.flush()


# ─── App ───
app = FastAPI(
    title="ExógenaDIAN — Consulta NIT API",
    description="Proxy para consultar NITs contra el portal MUISCA de la DIAN",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Device-Id", "X-Pro-Key"],
)

# ─── Chat router ───
from chat import router as chat_router
app.include_router(chat_router)

# ─── IA router (ExógenaDIAN IA) ───
from ia import router as ia_router
app.include_router(ia_router)


from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://www.googletagmanager.com https://checkout.wompi.co; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://exogenadian.com https://*.run.app https://api.anthropic.com; "
            "frame-src https://checkout.wompi.co"
        )
        return response


app.add_middleware(SecurityHeadersMiddleware)

cache = get_cache(CACHE_TTL_DAYS)


# ═══════════════════════════════════════════════════════════════
#  RATE LIMITER (por IP, reset diario)
# ═══════════════════════════════════════════════════════════════

class RateLimiter:
    def __init__(self):
        self.usage: dict[str, dict] = defaultdict(lambda: {"count": 0, "date": ""})

    def _today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def check(self, ip: str) -> tuple[bool, int]:
        """Verificar si la IP puede hacer consulta. Retorna (permitido, restantes)."""
        today = self._today()
        entry = self.usage[ip]
        if entry["date"] != today:
            entry["count"] = 0
            entry["date"] = today
        remaining = FREE_DIAN_QUERIES_PER_DAY - entry["count"]
        return remaining > 0, max(0, remaining)

    def consume(self, ip: str):
        today = self._today()
        entry = self.usage[ip]
        if entry["date"] != today:
            entry["count"] = 0
            entry["date"] = today
        entry["count"] += 1

    def get_remaining(self, ip: str) -> int:
        today = self._today()
        entry = self.usage[ip]
        if entry["date"] != today:
            return FREE_DIAN_QUERIES_PER_DAY
        return max(0, FREE_DIAN_QUERIES_PER_DAY - entry["count"])


rate_limiter = RateLimiter()


# ─── Helpers ───
def _clean_nit(nit: str) -> str:
    return nit.strip().replace(".", "").replace(" ", "").split("-")[0]


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _build_response(raw: dict) -> dict:
    nit = str(raw.get("nit", ""))
    estado = raw.get("estado_rut", "")
    # Si el estado viene de una fuente no oficial (fallback), no mostrarlo
    # para evitar mostrar "CANCELADO" erróneamente
    if raw.get("_estado_no_oficial"):
        estado = ""
    return {
        "nit": nit,
        "dv": raw.get("dv") or _calc_dv(nit),
        "razon_social": raw.get("razon_social", ""),
        "estado_rut": estado,
        "tipo_persona": raw.get("tipo_persona", ""),
        "responsabilidades": raw.get("responsabilidades", []),
        "direccion": raw.get("direccion", raw.get("dir", "")),
        "departamento": raw.get("departamento", raw.get("dp", "")),
        "municipio": raw.get("municipio", raw.get("mp", "")),
        "fuente": raw.get("fuente", ""),
        "cached": raw.get("cached", False),
        "error": raw.get("error", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def _consultar_nit(nit: str, use_dian: bool = True) -> dict:
    """Flujo completo: caché -> DIAN -> fallback."""
    nit = _clean_nit(nit)
    if not nit or not nit.isdigit() or len(nit) < 6 or len(nit) > 15:
        return _build_response({"nit": nit, "error": "NIT inválido (debe tener 6-15 dígitos)"})

    # 1. Caché
    cached = cache.get(nit)
    if cached:
        return _build_response(cached)

    # 2. DIAN MUISCA
    if use_dian:
        try:
            dian_result = await consultar_dian(nit)
            if dian_result and not dian_result.get("error") and not dian_result.get("_circuit_open"):
                dian_result["dv"] = _calc_dv(nit)
                cache.set(nit, dian_result)
                return _build_response(dian_result)
        except Exception as e:
            logger.warning("DIAN query failed for %s: %s", nit, e)

    # 3. Fallback (RUES, datos.gov.co, Einforma, web)
    try:
        fb_result = await consultar_fallback(nit)
        if fb_result and fb_result.get("razon_social"):
            cache.set(nit, fb_result)
        return _build_response(fb_result)
    except Exception as e:
        logger.error("Fallback failed for %s: %s", nit, e)
        return _build_response({"nit": nit, "error": "No se pudo consultar este NIT.", "fuente": "Error"})


# ═══════════════════════════════════════════════════════════════
#  ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/nit/{nit}")
async def consultar_nit_individual(nit: str, request: Request):
    """
    Consultar un NIT individual.
    10 consultas DIAN/día por IP. Siempre retorna DV + cruce offline.
    """
    ip = _get_client_ip(request)
    allowed, remaining = rate_limiter.check(ip)

    if allowed:
        rate_limiter.consume(ip)
        result = await _consultar_nit(nit, use_dian=True)
        result["_free_remaining"] = remaining - 1
        return result
    else:
        # Límite alcanzado: solo fallback (sin DIAN en vivo)
        result = await _consultar_nit(nit, use_dian=False)
        result["_free_remaining"] = 0
        result["_limit_reached"] = True
        return result


@app.get("/api/remaining")
async def get_remaining(request: Request):
    """Consultar cuántas consultas DIAN quedan hoy."""
    ip = _get_client_ip(request)
    return {
        "remaining": rate_limiter.get_remaining(ip),
        "daily_limit": FREE_DIAN_QUERIES_PER_DAY,
    }


@app.get("/api/health")
async def health_check():
    """Health check + estado del circuit breaker."""
    cb_status = circuit_breaker.get_status()
    dian_ok = cb_status["state"] != "OPEN"
    return {
        "status": "ok" if dian_ok else "degraded",
        "dian_available": dian_ok,
        "circuit_breaker": cb_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cache": cache.stats(),
    }


@app.get("/api/stats")
async def stats(request: Request):
    # Proteger con API key — enviar como header X-Stats-Key
    key = request.headers.get("x-stats-key", "")
    if not STATS_API_KEY or key != STATS_API_KEY:
        return {"error": "Unauthorized", "detail": "API key requerida en header X-Stats-Key"}
    from captcha_solver import get_balance
    try:
        balance = await get_balance()
    except Exception:
        balance = -1
    return {
        "cache": cache.stats(),
        "capsolver_balance": balance,
        "circuit_breaker": circuit_breaker.get_status(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
