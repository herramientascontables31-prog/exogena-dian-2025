"""
ExógenaDIAN — Backend Proxy para Consulta de NIT en DIAN MUISCA
FastAPI + Playwright + CapSolver + Caché + Rate Limiting + Circuit Breaker

Límites:
  GRATIS: 3 consultas DIAN/día por IP + listas offline hasta 10 NITs
  PRO:    Ilimitado, masivo hasta 2,000 NITs por consulta, Excel export

Endpoints:
  GET  /api/nit/{nit}         — Consulta individual
  POST /api/nit/bulk          — Consulta masiva (PRO: hasta 2,000)
  GET  /api/health            — Health check + estado circuit breaker
  GET  /api/stats             — Estadísticas
"""
import asyncio
import csv
import io
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cache import get_cache
from dian_scraper import consultar_dian, circuit_breaker
from fallback import consultar_fallback, _calc_dv

logger = logging.getLogger("exogenadian")

load_dotenv()

# ─── Config ───
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://exogenadian.com").split(",")
CACHE_TTL_DAYS = int(os.getenv("CACHE_TTL_DAYS", "7"))
PORT = int(os.getenv("PORT", "8080"))

# Claves PRO — se validan contra Google Sheet (misma fuente que el frontend Streamlit)
PRO_KEYS_URL = os.getenv(
    "PRO_KEYS_URL",
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vQc7cTur8DOZ_Kqkpqf7WmbzFT4im5efh0gYzIix4HE9pYp5B24OSDaOCKWjuU5YVXAMZeMGYkVE1eH/pub?gid=0&single=true&output=csv",
)

# Límites
FREE_DIAN_QUERIES_PER_DAY = 10
FREE_MAX_BULK = 10
PRO_MAX_BULK = 2000
PRO_DIAN_CREDITS_PER_MONTH = 500  # Consultas DIAN en vivo incluidas con PRO

# ─── Lifespan ───
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app):
    yield
    cache.flush()


# ─── App ───
app = FastAPI(
    title="ExógenaDIAN — Consulta NIT API",
    description="Proxy para consultar NITs contra el portal MUISCA de la DIAN",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Pro-Key"],
)


from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


app.add_middleware(SecurityHeadersMiddleware)

cache = get_cache(CACHE_TTL_DAYS)


# ═══════════════════════════════════════════════════════════════
#  RATE LIMITER (por IP, resets diario)
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
        """Consumir 1 consulta para esta IP."""
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


# ═══════════════════════════════════════════════════════════════
#  CRÉDITOS PRO (consultas DIAN mensuales)
# ═══════════════════════════════════════════════════════════════

class ProCredits:
    """Controla créditos de consultas DIAN por clave PRO, reset mensual."""
    def __init__(self, monthly_limit: int = 500):
        self.monthly_limit = monthly_limit
        self.usage: dict[str, dict] = defaultdict(lambda: {"count": 0, "month": ""})

    def _month(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def get_remaining(self, key: str) -> int:
        month = self._month()
        entry = self.usage[key]
        if entry["month"] != month:
            return self.monthly_limit
        return max(0, self.monthly_limit - entry["count"])

    def consume(self, key: str, amount: int = 1):
        month = self._month()
        entry = self.usage[key]
        if entry["month"] != month:
            entry["count"] = 0
            entry["month"] = month
        entry["count"] += amount

    def can_consume(self, key: str, amount: int = 1) -> bool:
        return self.get_remaining(key) >= amount


pro_credits = ProCredits(PRO_DIAN_CREDITS_PER_MONTH)

# Cache de claves PRO validadas (clave → timestamp de última verificación)
pro_keys_valid: dict[str, float] = {}
# Cache del set completo de claves activas del Sheet
_pro_keys_set: set[str] = set()
_pro_keys_set_ts: float = 0.0
PRO_KEY_CACHE_TTL = 300  # 5 minutos, igual que Streamlit


async def _fetch_pro_keys() -> set[str]:
    """Descargar claves PRO activas desde Google Sheet (misma fuente que Streamlit)."""
    global _pro_keys_set, _pro_keys_set_ts
    now = time.time()
    if _pro_keys_set and (now - _pro_keys_set_ts) < PRO_KEY_CACHE_TTL:
        return _pro_keys_set
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(PRO_KEYS_URL)
            resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text))
        keys = set()
        for row in reader:
            # Normalizar headers (strip + lower)
            row = {k.strip().lower(): v.strip() for k, v in row.items()}
            clave = row.get("clave", "")
            estado = row.get("estado", "").lower()
            if clave and clave.lower() != "nan" and estado in ("activo", "si", "sí", "1", "true"):
                keys.add(clave)
        _pro_keys_set = keys
        _pro_keys_set_ts = now
        logger.info("PRO keys refreshed: %d active keys", len(keys))
        return keys
    except Exception as e:
        logger.warning("Failed to fetch PRO keys from Sheet: %s", e)
        # Si falla, usar cache anterior si existe
        if _pro_keys_set:
            return _pro_keys_set
        return set()


async def is_pro(key: str | None) -> bool:
    """Verificar si una clave PRO es válida contra Google Sheet."""
    if not key or not key.strip():
        return False
    key = key.strip()
    # Cache local rápido
    if key in pro_keys_valid:
        if time.time() - pro_keys_valid[key] < PRO_KEY_CACHE_TTL:
            return True
    # Validar contra Sheet
    valid_keys = await _fetch_pro_keys()
    if key in valid_keys:
        pro_keys_valid[key] = time.time()
        return True
    # Limpiar de cache si ya no es válida
    pro_keys_valid.pop(key, None)
    return False


# ─── Models ───
class BulkRequest(BaseModel):
    nits: list[str]
    pro_key: str = ""


class NITResponse(BaseModel):
    nit: str
    dv: int | str | None = None
    razon_social: str = ""
    estado_rut: str = ""
    tipo_persona: str = ""
    responsabilidades: list[str] = []
    direccion: str = ""
    departamento: str = ""
    municipio: str = ""
    fuente: str = ""
    cached: bool = False
    error: str = ""
    timestamp: str = ""


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
    return {
        "nit": nit,
        "dv": raw.get("dv") or _calc_dv(nit),
        "razon_social": raw.get("razon_social", ""),
        "estado_rut": raw.get("estado_rut", ""),
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
    """Flujo completo: caché → DIAN → fallback."""
    nit = _clean_nit(nit)
    if not nit or not nit.isdigit() or len(nit) < 6 or len(nit) > 15:
        return _build_response({"nit": nit, "error": "NIT inválido (debe tener 6-15 dígitos)"})

    # 1. Caché
    cached = cache.get(nit)
    if cached:
        return _build_response(cached)

    # 2. DIAN MUISCA (si permitido)
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
        return _build_response({"nit": nit, "error": "No se pudo consultar este NIT. Intenta de nuevo.", "fuente": "Error"})


# ═══════════════════════════════════════════════════════════════
#  ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/nit/{nit}")
async def consultar_nit_individual(
    nit: str,
    request: Request,
    x_pro_key: str | None = Header(None),
):
    """
    Consultar un NIT individual.
    Gratis: 3 consultas DIAN/día. PRO: ilimitado.
    Siempre retorna al menos DV + cruce offline.
    """
    ip = _get_client_ip(request)
    user_is_pro = await is_pro(x_pro_key)

    if user_is_pro:
        # PRO: consulta completa sin límite
        return await _consultar_nit(nit, use_dian=True)
    else:
        # Free: verificar límite diario
        allowed, remaining = rate_limiter.check(ip)
        if allowed:
            rate_limiter.consume(ip)
            result = await _consultar_nit(nit, use_dian=True)
            result["_free_remaining"] = remaining - 1
            return result
        else:
            # Límite alcanzado: solo fallback (sin DIAN)
            result = await _consultar_nit(nit, use_dian=False)
            result["_free_remaining"] = 0
            result["_limit_reached"] = True
            return result


@app.post("/api/nit/bulk")
async def consultar_nit_masivo(req: BulkRequest, request: Request):
    """
    Consulta masiva de NITs.
    Gratis: máximo 10 NITs, solo offline.
    PRO: hasta 2,000 NITs. DIAN en vivo usa créditos mensuales (500/mes incluidos).
    Flujo PRO: caché → listas/fallback → DIAN (solo los no encontrados, gasta créditos).
    """
    user_is_pro = await is_pro(req.pro_key)

    if not req.nits:
        raise HTTPException(status_code=400, detail="Lista de NITs vacía")

    max_allowed = PRO_MAX_BULK if user_is_pro else FREE_MAX_BULK

    if len(req.nits) > max_allowed:
        if user_is_pro:
            raise HTTPException(status_code=400, detail=f"Máximo {PRO_MAX_BULK} NITs por consulta")
        else:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": f"Plan gratuito: máximo {FREE_MAX_BULK} NITs. Activa PRO para consultar hasta {PRO_MAX_BULK}.",
                    "upgrade_required": True,
                    "free_limit": FREE_MAX_BULK,
                    "pro_limit": PRO_MAX_BULK,
                },
            )

    # Deduplicar y limpiar
    clean_nits = list(dict.fromkeys(_clean_nit(n) for n in req.nits if _clean_nit(n)))

    results = []
    pending_offline = []

    # Fase 1: buscar en caché
    for nit in clean_nits:
        cached = cache.get(nit)
        if cached:
            results.append(_build_response(cached))
        else:
            pending_offline.append(nit)

    # Fase 2: consultar faltantes por fallback offline (gratis, no gasta créditos)
    pending_dian = []
    if pending_offline:
        semaphore = asyncio.Semaphore(10)

        async def _offline(nit):
            async with semaphore:
                return await _consultar_nit(nit, use_dian=False)

        offline_results = await asyncio.gather(*[_offline(n) for n in pending_offline])
        for r in offline_results:
            if r.get("razon_social"):
                results.append(r)
            else:
                pending_dian.append(r["nit"])

    # Fase 3: PRO — consultar DIAN en vivo los que no se encontraron (gasta créditos)
    dian_consulted = 0
    if user_is_pro and pending_dian:
        credits_available = pro_credits.get_remaining(req.pro_key)
        # Limitar a créditos disponibles
        nits_for_dian = pending_dian[:credits_available]
        skipped = pending_dian[credits_available:]

        if nits_for_dian:
            semaphore = asyncio.Semaphore(3)

            async def _dian(nit):
                async with semaphore:
                    return await _consultar_nit(nit, use_dian=True)

            dian_results = await asyncio.gather(*[_dian(n) for n in nits_for_dian])
            results.extend(dian_results)
            dian_consulted = len(nits_for_dian)
            pro_credits.consume(req.pro_key, dian_consulted)

        # Los que no se pudieron consultar por falta de créditos
        for nit in skipped:
            results.append(_build_response({
                "nit": nit,
                "dv": _calc_dv(nit),
                "error": "Sin créditos DIAN disponibles este mes",
                "fuente": "Sin créditos",
            }))
    elif not user_is_pro and pending_dian:
        # Free: agregar los no encontrados sin DIAN
        for nit in pending_dian:
            results.append(_build_response({
                "nit": nit,
                "dv": _calc_dv(nit),
                "fuente": "No encontrado (activa PRO para consultar DIAN)",
            }))

    credits_remaining = pro_credits.get_remaining(req.pro_key) if user_is_pro else 0

    return {
        "total": len(results),
        "cached": sum(1 for r in results if r.get("cached")),
        "dian_consulted": dian_consulted,
        "credits_remaining": credits_remaining,
        "is_pro": user_is_pro,
        "results": results,
    }


@app.get("/api/remaining")
async def get_remaining(request: Request, x_pro_key: str | None = Header(None)):
    """Consultar cuántas consultas DIAN quedan (gratis por día, PRO por mes)."""
    ip = _get_client_ip(request)
    user_is_pro = await is_pro(x_pro_key)
    result = {
        "remaining": rate_limiter.get_remaining(ip),
        "daily_limit": FREE_DIAN_QUERIES_PER_DAY,
        "is_pro": user_is_pro,
    }
    if user_is_pro:
        result["credits_remaining"] = pro_credits.get_remaining(x_pro_key)
        result["credits_monthly"] = PRO_DIAN_CREDITS_PER_MONTH
    return result


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
async def stats():
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
