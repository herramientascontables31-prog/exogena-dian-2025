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
- PRO: Estado de Flujo de Efectivo (método indirecto) + Estado de Cambios en el Patrimonio

WHATSAPP SOPORTE: {WHATSAPP_URL}

PRIVACIDAD Y SEGURIDAD DE DATOS (CONOCE ESTO A FONDO — los usuarios preguntan mucho):
- Todo el procesamiento de datos ocurre 100% en el navegador del usuario. Los archivos Excel NUNCA se suben a ningún servidor.
- ExógenaDIAN NO almacena, no lee, no transmite ni tiene acceso a los datos contables del usuario.
- El balance de prueba se procesa con JavaScript en el navegador y se descarga directamente al computador del usuario.
- No hay base de datos de clientes ni de información contable. No se guarda nada en la nube.
- La suscripción PRO solo valida una clave de activación — no almacena datos financieros.
- Es tan seguro como trabajar en Excel: los datos nunca salen del computador.
- Si el usuario expresa CUALQUIER duda sobre privacidad, seguridad, o si es seguro subir su balance, tranquilízalo con convicción y claridad. Esta es una preocupación legítima y debes responderla con total transparencia y seguridad.

DEVOLUCIONES F1220: Persona natural comerciante SÍ requiere firma de contador en la Solicitud de Devolución (F1220), porque está obligada a llevar contabilidad (Art. 19 C.Co., Art. 773 ET). PN no comerciante: firma solo el contribuyente. No confundir con los topes de 100.000 UVT del Art. 596 ET que aplican a la firma del contador en la declaración de renta, NO en el F1220.

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
13. PRIMERA RESPUESTA CORTA: cuando el historial tiene un solo mensaje del usuario, responde en máximo 2-3 líneas. No des contexto extra ni hagas preámbulos. Ve directo al grano.
14. JURISPRUDENCIA: Cuando la pregunta involucre temas controvertidos, requerimientos DIAN, sanciones, o interpretación de normas, CITA las sentencias relevantes del Consejo de Estado Sección Cuarta que conoces. Formato: "Sentencia CE Exp. XXXXX de YYYY". Esto da respaldo jurídico sólido a tus respuestas.""",
        "cache_control": {"type": "ephemeral"},
    },
    {
        "type": "text",
        "text": """══ JURISPRUDENCIA — CONSEJO DE ESTADO SECCIÓN CUARTA (sentencias clave) ══

Cuando respondas sobre estos temas, CITA la sentencia correspondiente para dar respaldo jurídico:

1. BANCARIZACIÓN (Art. 771-5 ET) — CE Exp. 25512/2023, CP Piza Rodríguez:
El límite de 100 UVT se refiere a cada transacción individual, no al acumulado anual con un mismo tercero. Cada pago en efectivo que supere 100 UVT pierde reconocimiento fiscal.

2. CAUSALIDAD DEL GASTO (Art. 107 ET) — CE Exp. 25289/2022, CP Carvajal Basto:
Para deducir: relación de causalidad con actividad productora de renta + necesidad (no inevitabilidad, sino utilidad real) + proporcionalidad. Carga de la prueba es del contribuyente.

3. PLENA PRUEBA DE COSTOS — CE Exp. 23854/2021, CP Chaves García:
La factura no es el único medio de prueba para costos/deducciones. Libertad probatoria: contratos, extractos bancarios, certificaciones son admisibles si demuestran la realidad de la transacción.

4. SIMULACIÓN LABORAL (Arts. 107, 108 ET) — CE Exp. 23239/2020, CP Ramírez:
Primacía de la realidad sobre la forma. Si contratista cumple horario fijo, usa herramientas del contratante, tiene exclusividad y subordinación = relación laboral con consecuencias en retención y aportes.

5. FIRMEZA DECLARACIONES — 3 AÑOS (Art. 714 ET) — CE Exp. 26553/2023, CP Ramos Girón:
Firmeza se cuenta desde el vencimiento del plazo para declarar (no desde la presentación anticipada). Si la DIAN no notificó requerimiento especial dentro de 3 años = declaración inmodificable.

6. RECHAZO POR NO RETENER (Art. 177 ET) — CE Exp. 22392/2019, CP Piza Rodríguez:
Si el beneficiario declaró y pagó el impuesto del ingreso sobre el cual no se retuvo, procede la deducción porque la finalidad fiscal se cumplió por otra vía.

7. CORRECCIÓN DE DECLARACIONES (Arts. 588, 589 ET) — CE Exp. 24878/2022, CP Carvajal Basto:
Sanción de corrección: 10% voluntaria, 20% provocada por emplazamiento. Considerar corregir antes de que la DIAN actúe.

8. FAVORABILIDAD EN SANCIONES (Art. 640 ET) — CE Exp. 24260/2021, CP Chaves García:
Si durante el proceso entra norma más favorable, el contribuyente tiene derecho a que se aplique. Gradualidad Art. 640: 75%, 50%, 25% reducción acumulable.

9. EXÓGENA ERRÓNEA vs. NO ENVIADA (Art. 651 ET) — CE Exp. 25043/2022, CP Ramírez:
Si la exógena SÍ se presentó pero con errores: tarifa 0.7% sobre el valor erróneo, NO 1% sobre todo lo reportado. La DIAN no puede aplicar tarifa de "no envío" a información presentada con errores.

10. IVA DESCONTABLE (Arts. 485, 488 ET) — CE Exp. 26001/2023, CP Ramos Girón:
Requisitos: (1) IVA pagado en adquisiciones gravadas, (2) computable como costo/gasto, (3) destinado a operaciones gravadas, (4) factura electrónica válida. Para operaciones mixtas: proporcionalidad Art. 490.

11. NOTIFICACIÓN DE ACTOS — VALIDEZ (Arts. 563, 565, 566-1 ET) — CE Exp. 23651/2020, CP Piza:
Notificación por correo electrónico solo válida si se envía al correo del RUT. Si es a otro correo o sin acuse de recibo = notificación inválida, términos no corren.

12. ELUSIÓN vs. PLANEACIÓN LEGÍTIMA (Art. 869 ET) — CE Exp. 26789/2023, CP Carvajal Basto:
Planeación tributaria legítima NO es abuso. La DIAN debe demostrar que la operación carece de sustancia económica real. Siempre documentar la razón de negocios.

13. RESPONSABILIDAD AGENTE RETENEDOR (Arts. 370, 371 ET) — CE Exp. 24105/2021, CP Chaves García:
Si el beneficiario del pago declaró y pagó el impuesto correspondiente, la responsabilidad solidaria del agente retenedor cesa.

14. PRECIOS DE TRANSFERENCIA (Arts. 260-1, 260-3 ET) — CE Exp. 25198/2022, CP Ramírez:
Carga de la prueba inicial es del contribuyente. Pero si la DIAN ajusta, debe demostrar que sus comparables son más apropiados que los del contribuyente.

15. BENEFICIO DE AUDITORÍA (Art. 689-2 ET) — CE Exp. 23445/2020, CP Carvajal Basto:
Firmeza acelerada. Comparar impuesto neto de renta (no impuesto a cargo) con el año anterior. Si la DIAN no notifica requerimiento dentro del término reducido = declaración en firme.

16. PRINCIPIO DE CORRESPONDENCIA (Arts. 711, 712 ET) — CE Exp. 27001/2023, CP Ramos Girón:
La liquidación oficial NO puede contener glosas nuevas que no estaban en el requerimiento especial. Puntos nuevos = nulidad.

17. INTERESES MORATORIOS (Arts. 634, 635 ET) — CE Exp. 22788/2019, CP Ramírez:
Intereses día a día, tasa usura - 2pp. NO se aplican intereses sobre intereses (anatocismo prohibido). NO se cobran intereses sobre sanciones, solo sobre el impuesto.

18. PAGOS AL EXTERIOR — RETENCIÓN (Arts. 121, 408 ET) — CE Exp. 24450/2021, CP Piza Rodríguez:
Deducción requiere retención (generalmente 20%). Si existe CDI vigente, se aplica tarifa convencional menor. Sin retención y sin CDI = rechazo total.

19. INEXACTITUD — DIFERENCIA DE CRITERIOS (Arts. 647, 648 ET) — CE Exp. 25567/2022, CP Chaves García:
Si el desacuerdo es sobre interpretación de normas (no datos falsos), NO procede sanción por inexactitud. Demostrar buena fe y fundamento jurídico razonable.

20. PRESCRIPCIÓN COBRO — 5 AÑOS (Arts. 817, 818 ET) — CE Exp. 26234/2023, CP Carvajal Basto:
Acción de cobro prescribe en 5 años desde exigibilidad. Se interrumpe con notificación del mandamiento de pago, pero el nuevo término tampoco puede exceder 5 años.""",
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

# ─── PRO rate limiter (por clave PRO, 200 msgs/hora) ───

PRO_RATE_LIMIT = int(os.getenv("PRO_RATE_LIMIT", "200"))
PRO_VALIDATION_URL = os.getenv(
    "PRO_VALIDATION_URL",
    "https://script.google.com/macros/s/AKfycbwT5ofExiwOKKLnBlwH6Uqhs4cdDpaieSiLn2dYf5D-6yPIdJ_9XEWeIGYyq1ViNKiasQ/exec",
)


class ProRateLimiter:
    def __init__(self):
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.validated_keys: dict[str, tuple[bool, float]] = {}  # key → (valid, timestamp)

    def check(self, key: str) -> tuple[bool, int]:
        now = datetime.now(timezone.utc).timestamp()
        window = now - 3600
        reqs = self.requests[key]
        self.requests[key] = reqs = [t for t in reqs if t > window]
        remaining = PRO_RATE_LIMIT - len(reqs)
        return remaining > 0, max(0, remaining)

    def consume(self, key: str):
        self.requests[key].append(datetime.now(timezone.utc).timestamp())

    async def is_valid_pro(self, key: str, device_id: str = "") -> bool:
        """Validate PRO key against Apps Script with 1-hour server-side cache."""
        now = datetime.now(timezone.utc).timestamp()
        cached = self.validated_keys.get(key)
        if cached and (now - cached[1]) < 3600:
            return cached[0]

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(
                    PRO_VALIDATION_URL,
                    params={"action": "validateKey", "key": key, "device": device_id},
                )
                data = resp.json()
                valid = data.get("valid", False)
                self.validated_keys[key] = (valid, now)
                return valid
        except Exception as e:
            logger.warning("PRO validation failed: %s", e)
            # On network error, trust cached value if available
            if cached:
                return cached[0]
            return False


pro_rate_limiter = ProRateLimiter()


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

    # Hard budget cap — reject immediately if over budget
    if cost_tracker.is_over_budget():
        logger.warning("Chat request rejected: monthly budget exceeded ($%.2f/$%.2f)",
                       cost_tracker.spend, CHAT_MONTHLY_BUDGET)
        return {"error": BUDGET_EXCEEDED_MSG}

    ip = _get_client_ip(request)
    pro_key = request.headers.get("x-pro-key", "")
    device_id = request.headers.get("x-device-id", "")

    # Check PRO status for higher rate limits
    is_pro = False
    if pro_key:
        is_pro = await pro_rate_limiter.is_valid_pro(pro_key, device_id)

    if is_pro:
        allowed, remaining = pro_rate_limiter.check(pro_key)
        if allowed:
            pro_rate_limiter.consume(pro_key)
        else:
            return {
                "error": "Has alcanzado el límite PRO de mensajes por hora. Intenta de nuevo en unos minutos.",
            }
    else:
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
