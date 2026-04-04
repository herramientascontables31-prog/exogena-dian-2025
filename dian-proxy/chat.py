"""
ExógenaDIAN — Chat endpoint: "Exa", asistente contable IA
Anthropic API con prompt caching + streaming SSE.
Rate limit: 20 mensajes/hora por IP.

Optimizaciones:
  - Prompt caching: el system prompt (~1200 tokens) se cachea por 5 min.
    Tokens cacheados cuestan 90% menos ($0.30/M vs $3/M input).
  - max_tokens reducido a 800 (respuestas concisas de Exa).
  - Historial recortado: solo últimos 10 mensajes para reducir input.
  - Mensajes de usuario limitados a 500 chars.
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

BASE = "https://exogenadian.com"

# System prompt con cache_control para Anthropic prompt caching.
# Se envía como array de bloques [{type, text, cache_control}].
SYSTEM_BLOCKS = [
    {
        "type": "text",
        "text": f"""Eres Exa, asistente contable de ExógenaDIAN ({BASE}). Experta en normativa tributaria y laboral colombiana. Tono profesional pero cercano.

HERRAMIENTAS:
Tributarias: Exógena DIAN→{BASE}/exogena (10 formatos F1001-F2276) | Renta F110→{BASE}/renta | IVA 300→{BASE}/iva | Retención 350→{BASE}/retencion
Financieras: Estados NIIF→{BASE}/estados | Dashboard→{BASE}/dashboard | Conciliación→{BASE}/conciliacion
Sanciones: Exógena→{BASE}/sanciones-exogena (Art.651) | DIAN→{BASE}/sanciones-dian (Arts.641,642,644) | Intereses mora→{BASE}/intereses (Art.635+Decreto 0240/2026)
Laboral: Ret. laboral→{BASE}/retencion-laboral | Liquidador→{BASE}/liquidador-laboral | Costo empleado→{BASE}/costo-empleado | NIT→{BASE}/consulta-nit | Vencimientos→{BASE}/vencimientos

VALORES: UVT 2025=$49.799 | UVT 2026=$52.374 | SMLMV 2026=$1.750.905 | Aux. transporte 2026=$249.095

PRO: $19.900/mes o $179.900/año. Gratis: Exógena, ESF+ERI básicos, Sanciones, Intereses, NIT, Vencimientos, Costo Empleado. PRO: Renta F110, IVA, Ret.350, Dashboard, Conciliación, Liquidador, Ret.Laboral, Estados con notas/comparativo/patrimonio/flujo. Compatible: Siigo, World Office, Helisa, Alegra, MidaSoft, ZEUS, GW.

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
    content: str = Field(max_length=4000)  # assistant responses can be long


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

    ip = _get_client_ip(request)
    allowed, remaining = rate_limiter.check(ip)

    if not allowed:
        return {
            "error": "Has alcanzado el límite de mensajes por hora. Intenta de nuevo en unos minutos.",
            "whatsapp": WHATSAPP_URL,
        }

    rate_limiter.consume(ip)

    # Últimos 10 mensajes para reducir tokens de input
    messages = [{"role": m.role, "content": m.content} for m in body.messages[-10:]]

    async def event_stream():
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

                        if etype == "content_block_delta":
                            delta = event.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text = delta.get("text", "")
                                if text:
                                    yield f"data: {json.dumps({'type': 'text', 'text': text})}\n\n"
                        elif etype == "message_stop":
                            yield f"data: {json.dumps({'type': 'done'})}\n\n"
                        elif etype == "error":
                            yield f"data: {json.dumps({'type': 'error', 'error': 'Error interno.'})}\n\n"

        except httpx.TimeoutException:
            yield f"data: {json.dumps({'type': 'error', 'error': 'Tiempo de espera agotado.'})}\n\n"
        except Exception as e:
            logger.error("Chat stream error: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'error': 'Error inesperado.'})}\n\n"

    return StreamingResponse(
        event_stream(),
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
    return {"remaining": remaining, "limit": CHAT_RATE_LIMIT}
