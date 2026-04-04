"""
ExógenaDIAN — Chat endpoint: "Exa", asistente contable IA
Anthropic API con prompt caching + streaming SSE.

Features:
  - Prompt caching (90% cheaper on system prompt)
  - Rate limit: 20 msgs/hora por IP
  - Cost tracker: acumula gasto mensual, alerta al 80%, bloquea al 100%
  - Budget: configurable via CHAT_MONTHLY_BUDGET (default $5 USD)
"""
import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("exogenadian.chat")

router = APIRouter(prefix="/api/chat", tags=["chat"])

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CHAT_MODEL = os.getenv("CHAT_MODEL", "claude-sonnet-4-20250514")
CHAT_MAX_TOKENS = int(os.getenv("CHAT_MAX_TOKENS", "800"))
CHAT_RATE_LIMIT = int(os.getenv("CHAT_RATE_LIMIT", "20"))  # msgs/hora
WHATSAPP_URL = os.getenv("WHATSAPP_URL", "https://wa.me/573054559574")
CHAT_MONTHLY_BUDGET = float(os.getenv("CHAT_MONTHLY_BUDGET", "5.0"))  # USD
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "soporte@exogenadian.com")
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")  # Google Apps Script URL

# Precios Sonnet (USD por millón de tokens)
PRICE_INPUT = 3.0
PRICE_CACHED_INPUT = 0.30
PRICE_OUTPUT = 15.0

BASE = "https://exogenadian.com"

SYSTEM_BLOCKS = [
    {
        "type": "text",
        "text": f"""Eres Exa, asistente contable de ExógenaDIAN ({BASE}). Experta en normativa tributaria y laboral colombiana. Tono profesional pero cercano.

HERRAMIENTAS:
Tributarias: Exógena DIAN→{BASE}/exogena (10 formatos F1001-F2276) | Renta F110→{BASE}/renta | IVA 300→{BASE}/iva | Retención 350→{BASE}/retencion
Financieras: Estados NIIF→{BASE}/estados (ver detalle abajo) | Dashboard→{BASE}/dashboard | Conciliación→{BASE}/conciliacion
Sanciones: Exógena→{BASE}/sanciones-exogena (Art.651) | DIAN→{BASE}/sanciones-dian (Arts.641,642,644) | Intereses mora→{BASE}/intereses (Art.635+Decreto 0240/2026)
Laboral: Ret. laboral→{BASE}/retencion-laboral | Liquidador→{BASE}/liquidador-laboral | Costo empleado→{BASE}/costo-empleado | NIT→{BASE}/consulta-nit | Vencimientos→{BASE}/vencimientos

VALORES: UVT 2025=$49.799 | UVT 2026=$52.374 | SMLMV 2026=$1.750.905 | Aux. transporte 2026=$249.095

PRO: $19.900/mes o $179.900/año. Gratis: Exógena, ESF+ERI básicos, Sanciones, Intereses, NIT, Vencimientos, Costo Empleado. PRO: Renta F110, IVA, Ret.350, Dashboard, Conciliación, Liquidador, Ret.Laboral, Estados con notas/revelaciones/comparativo. Compatible: Siigo, World Office, Helisa, Alegra, MidaSoft, ZEUS, GW.

DETALLE ESTADOS FINANCIEROS ({BASE}/estados):
- Gratis: Estado de Situación Financiera (ESF) + Estado de Resultados Integral (ERI)
- PRO: Notas a los EEFF, revelaciones, políticas contables, comparativo año vs año
- NO DISPONIBLE AÚN: Estado de Flujo de Efectivo y Estado de Cambios en el Patrimonio (están en desarrollo)
- IMPORTANTE: Si preguntan por flujo de efectivo o cambios en patrimonio, di que están en desarrollo y que próximamente estarán disponibles. NUNCA digas que ya existen.

WHATSAPP SOPORTE: {WHATSAPP_URL}

PRIVACIDAD Y SEGURIDAD DE DATOS (CONOCE ESTO A FONDO — los usuarios preguntan mucho):
- Todo el procesamiento de datos ocurre 100% en el navegador del usuario. Los archivos Excel NUNCA se suben a ningún servidor.
- ExógenaDIAN NO almacena, no lee, no transmite ni tiene acceso a los datos contables del usuario.
- El balance de prueba se procesa con JavaScript en el navegador y se descarga directamente al computador del usuario.
- No hay base de datos de clientes ni de información contable. No se guarda nada en la nube.
- La suscripción PRO solo valida una clave de activación — no almacena datos financieros.
- Es tan seguro como trabajar en Excel: los datos nunca salen del computador.
- Si el usuario expresa CUALQUIER duda sobre privacidad, seguridad, o si es seguro subir su balance, tranquilízalo con convicción y claridad. Esta es una preocupación legítima y debes responderla con total transparencia y seguridad.

REGLAS:
1. Español colombiano siempre.
2. Concisa: 1-3 párrafos, listas si es complejo.
3. Herramientas con link: **[Nombre]({BASE}/ruta)** — descripción.
4. Cálculos: paso a paso con fórmulas y resultado.
5. Si excede el chat → redirige a herramienta.
6. Solo temas contables/tributarios/laborales colombianos.
7. No inventar normas. Si no sabes, dilo.
8. Negrita en valores clave, artículos ET y herramientas.
9. Artículos con número: Art. 641 ET.
10. Máximo 1 emoji por mensaje.
11. WHATSAPP SOLO COMO ÚLTIMO RECURSO: NO ofrezcas WhatsApp de manera proactiva ni al principio de la conversación. Solo menciona WhatsApp cuando: (a) ya intentaste resolver la duda al menos 2 veces y no pudiste, (b) el tema claramente requiere revisión humana de documentos específicos del cliente, (c) es una cotización de servicio personalizado, o (d) hay un error técnico del portal que no puedes resolver. Cuando lo hagas, di algo como: "Para este caso específico te recomiendo que nos escribas por **[WhatsApp]({WHATSAPP_URL})** para que el equipo te ayude directamente."
12. Si el usuario se despide o dice gracias, responde brevemente y recuerda que puede volver cuando quiera.
13. PRIMERA RESPUESTA CORTA: cuando el historial tiene un solo mensaje del usuario, responde en máximo 2-3 líneas. No des contexto extra ni hagas preámbulos. Ve directo al grano.""",
        "cache_control": {"type": "ephemeral"},
    }
]

BUDGET_EXCEEDED_MSG = (
    "En este momento estoy en mantenimiento. Mientras tanto, puedes consultar "
    f"nuestras herramientas directamente en [{BASE}]({BASE}) o escribirnos por "
    f"**[WhatsApp]({WHATSAPP_URL})**."
)


# ═══════════════════════════════════════════════════════════════
#  COST TRACKER — acumula gasto mensual, alerta, bloquea
# ═══════════════════════════════════════════════════════════════

class CostTracker:
    def __init__(self):
        self.spend: float = 0.0
        self.month: str = self._current_month()
        self.alert_sent: bool = False
        self.message_count: int = 0

    @staticmethod
    def _current_month() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def _reset_if_new_month(self):
        current = self._current_month()
        if current != self.month:
            self.spend = 0.0
            self.month = current
            self.alert_sent = False
            self.message_count = 0

    def add(self, input_tokens: int, cached_tokens: int, output_tokens: int):
        """Sumar costo de una respuesta."""
        self._reset_if_new_month()
        # Tokens no cacheados = input_tokens - cached_tokens
        fresh_input = max(0, input_tokens - cached_tokens)
        cost = (
            (fresh_input / 1_000_000) * PRICE_INPUT
            + (cached_tokens / 1_000_000) * PRICE_CACHED_INPUT
            + (output_tokens / 1_000_000) * PRICE_OUTPUT
        )
        self.spend += cost
        self.message_count += 1
        logger.info(
            "Chat cost: $%.4f (total: $%.4f / $%.2f, msgs: %d)",
            cost, self.spend, CHAT_MONTHLY_BUDGET, self.message_count,
        )
        return cost

    def is_over_budget(self) -> bool:
        self._reset_if_new_month()
        return self.spend >= CHAT_MONTHLY_BUDGET

    def should_alert(self) -> bool:
        """True si estamos al 80%+ y no se ha enviado alerta este mes."""
        self._reset_if_new_month()
        if self.alert_sent:
            return False
        return self.spend >= CHAT_MONTHLY_BUDGET * 0.8

    def mark_alert_sent(self):
        self.alert_sent = True

    def stats(self) -> dict:
        self._reset_if_new_month()
        return {
            "month": self.month,
            "spend_usd": round(self.spend, 4),
            "budget_usd": CHAT_MONTHLY_BUDGET,
            "percent_used": round((self.spend / CHAT_MONTHLY_BUDGET) * 100, 1) if CHAT_MONTHLY_BUDGET > 0 else 0,
            "messages": self.message_count,
            "alert_sent": self.alert_sent,
        }


cost_tracker = CostTracker()


async def _send_budget_alert():
    """Enviar alerta de presupuesto via Google Apps Script webhook."""
    if not ALERT_WEBHOOK_URL:
        logger.warning("Budget alert triggered but no ALERT_WEBHOOK_URL configured")
        return
    stats = cost_tracker.stats()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.get(
                ALERT_WEBHOOK_URL,
                params={
                    "action": "sendAlert",
                    "email": ALERT_EMAIL,
                    "subject": f"⚠️ Exa: {stats['percent_used']}% del presupuesto usado",
                    "body": (
                        f"Hola,\n\n"
                        f"El chatbot Exa ha usado el {stats['percent_used']}% del presupuesto mensual.\n\n"
                        f"Gasto: ${stats['spend_usd']} USD de ${stats['budget_usd']} USD\n"
                        f"Mensajes este mes: {stats['messages']}\n"
                        f"Mes: {stats['month']}\n\n"
                        f"Recarga tu saldo en console.anthropic.com → Settings → Billing.\n\n"
                        f"---\nExógenaDIAN · exogenadian.com"
                    ),
                },
            )
        cost_tracker.mark_alert_sent()
        logger.info("Budget alert sent to %s", ALERT_EMAIL)
    except Exception as e:
        logger.error("Failed to send budget alert: %s", e)


# ─── Rate limiter (por IP, ventana deslizante 1h) ───

class ChatRateLimiter:
    def __init__(self):
        self.requests: dict[str, list[float]] = defaultdict(list)

    def check(self, ip: str) -> tuple[bool, int]:
        now = datetime.now(timezone.utc).timestamp()
        window = now - 3600
        reqs = self.requests[ip]
        self.requests[ip] = reqs = [t for t in reqs if t > window]
        remaining = CHAT_RATE_LIMIT - len(reqs)
        return remaining > 0, max(0, remaining)

    def consume(self, ip: str):
        self.requests[ip].append(datetime.now(timezone.utc).timestamp())


rate_limiter = ChatRateLimiter()


# ─── Request model ───

class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(max_length=20)


# ─── Helpers ───

def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ─── Streaming endpoint ───

@router.post("")
async def chat(body: ChatRequest, request: Request):
    if not ANTHROPIC_API_KEY:
        return {"error": "Chat no configurado. Falta ANTHROPIC_API_KEY."}

    # Budget check
    if cost_tracker.is_over_budget():
        return {"error": BUDGET_EXCEEDED_MSG}

    ip = _get_client_ip(request)
    allowed, remaining = rate_limiter.check(ip)

    if not allowed:
        return {
            "error": "Has alcanzado el límite de mensajes por hora. Intenta de nuevo en unos minutos.",
            "whatsapp": WHATSAPP_URL,
        }

    rate_limiter.consume(ip)

    messages = [{"role": m.role, "content": m.content} for m in body.messages[-10:]]

    # Track tokens across the stream
    usage_input = 0
    usage_cached = 0
    usage_output = 0

    async def event_stream():
        nonlocal usage_input, usage_cached, usage_output
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "anthropic-beta": "prompt-caching-2024-07-31",
                        "content-type": "application/json",
                    },
                    json={
                        "model": CHAT_MODEL,
                        "max_tokens": CHAT_MAX_TOKENS,
                        "system": SYSTEM_BLOCKS,
                        "messages": messages,
                        "stream": True,
                    },
                ) as resp:
                    if resp.status_code != 200:
                        error_body = await resp.aread()
                        logger.error("Anthropic API error %s: %s", resp.status_code, error_body[:500])
                        yield f"data: {json.dumps({'type': 'error', 'error': 'Error al procesar tu mensaje. Intenta de nuevo.'})}\n\n"
                        return

                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            event = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        etype = event.get("type", "")

                        # Capture usage from message_start
                        if etype == "message_start":
                            msg = event.get("message", {})
                            u = msg.get("usage", {})
                            usage_input = u.get("input_tokens", 0)
                            usage_cached = u.get("cache_read_input_tokens", 0)

                        elif etype == "content_block_delta":
                            delta = event.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text = delta.get("text", "")
                                if text:
                                    yield f"data: {json.dumps({'type': 'text', 'text': text})}\n\n"

                        # Capture output tokens from message_delta
                        elif etype == "message_delta":
                            u = event.get("usage", {})
                            usage_output = u.get("output_tokens", 0)

                        elif etype == "message_stop":
                            yield f"data: {json.dumps({'type': 'done'})}\n\n"

                        elif etype == "error":
                            yield f"data: {json.dumps({'type': 'error', 'error': 'Error interno.'})}\n\n"

        except httpx.TimeoutException:
            yield f"data: {json.dumps({'type': 'error', 'error': 'Tiempo de espera agotado.'})}\n\n"
        except Exception as e:
            logger.error("Chat stream error: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'error': 'Error inesperado.'})}\n\n"

    async def tracked_stream():
        """Wrapper que rastrea costos después del stream."""
        async for chunk in event_stream():
            yield chunk

        # Después de que el stream termine, registrar costo
        if usage_input > 0 or usage_output > 0:
            cost_tracker.add(usage_input, usage_cached, usage_output)

            # Enviar alerta si estamos al 80%+
            if cost_tracker.should_alert():
                await _send_budget_alert()

    return StreamingResponse(
        tracked_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Chat-Remaining": str(remaining - 1),
        },
    )


@router.get("/remaining")
async def chat_remaining(request: Request):
    ip = _get_client_ip(request)
    _, remaining = rate_limiter.check(ip)
    return {
        "remaining": remaining,
        "limit": CHAT_RATE_LIMIT,
        "budget": cost_tracker.stats(),
    }
