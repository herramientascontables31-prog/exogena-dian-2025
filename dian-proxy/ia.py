"""
ExogenaDIAN IA — Endpoints de inteligencia artificial
3 herramientas: Analizador de Balance, Chat ET, Detector de Inconsistencias.

Modelos (producción — bajo costo):
  - Herramientas 1 y 3: Google Gemini 2.0 Flash (GEMINI_API_KEY)
  - Herramienta 2 (chat): DeepSeek V3.2 vía OpenRouter (OPENROUTER_API_KEY)
"""
import json
import logging
import os
import re
from collections import defaultdict
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("exogenadian.ia")

router = APIRouter(prefix="/api/ia", tags=["ia"])

# ─── API Keys ───
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# ─── Models ───
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
GEMINI_STREAM_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:streamGenerateContent"

DEEPSEEK_MODEL = "deepseek/deepseek-chat-v3.1"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MAX_TOKENS_ANALYSIS = 1500
MAX_TOKENS_CHAT = 800


# ═══════════════════════════════════════════════════════════════
#  RATE LIMITER IA (por IP, ventana deslizante 1h)
# ═══════════════════════════════════════════════════════════════

IA_RATE_LIMIT = int(os.getenv("IA_RATE_LIMIT", "30"))  # msgs/hora


class IARateLimiter:
    def __init__(self):
        self.requests: dict[str, list[float]] = defaultdict(list)

    def check(self, ip: str) -> tuple[bool, int]:
        now = datetime.now(timezone.utc).timestamp()
        window = now - 3600
        reqs = self.requests[ip]
        self.requests[ip] = reqs = [t for t in reqs if t > window]
        remaining = IA_RATE_LIMIT - len(reqs)
        return remaining > 0, max(0, remaining)

    def consume(self, ip: str):
        self.requests[ip].append(datetime.now(timezone.utc).timestamp())


ia_rate_limiter = IARateLimiter()


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ═══════════════════════════════════════════════════════════════
#  SYSTEM PROMPTS
# ═══════════════════════════════════════════════════════════════

SYSTEM_ANALISIS_BALANCE = """Eres un experto tributarista colombiano con 20 años de experiencia en auditoría fiscal, revisoría fiscal y planeación tributaria. Trabajas para ExógenaDIAN, la plataforma #1 de herramientas tributarias en Colombia.

══ DATOS VIGENTES ══
UVT 2025: $49.799 | UVT 2026: $52.374
SMLMV 2026: $1.750.905 | Auxilio transporte 2026: $249.095
Tarifa renta PJ: 35% (Art. 240 ET, Ley 2277/2022)
Tarifa renta PN: tabla progresiva Art. 241 ET (0% a 39%)
IVA general: 19% | Retención honorarios declarantes: 11% | Servicios: 4% (base 2 UVT)
Tope no responsable IVA: 3.500 UVT = $174.297.000 (2025)
GMF: 4x1000 vigente. 50% deducible en renta (Art. 115 ET)
ICA: deducción 100% en renta (ya NO descuento desde AG 2023, Ley 2277/2022 Art. 19)
Sanción mínima: 10 UVT = $498.000 (2025) / $524.000 (2026)

══ NORMATIVA CLAVE ══
- Estatuto Tributario actualizado a 2026
- Resolución 000227 de 2025 (información exógena)
- Decreto 1474 de 2025 (beneficios pago)
- Ley 2277 de 2022 (reforma tributaria)
- Decreto 0572 de 2025 (reducción base retención servicios a 2 UVT)

══ INSTRUCCIONES ══
Analiza el balance/resumen contable y devuelve ÚNICAMENTE JSON válido con esta estructura:

{
  "semaforo": "verde" | "amarillo" | "rojo",
  "semaforo_justificacion": "Justificación del nivel de riesgo",
  "alertas": [
    {
      "tipo": "gasto_no_deducible" | "inconsistencia_puc" | "diferencia_temporaria" | "proporcionalidad" | "otro",
      "titulo": "Título corto",
      "descripcion": "Explicación detallada del hallazgo",
      "severidad": "alta" | "media" | "baja",
      "articulo_et": "Art. XXX ET"
    }
  ],
  "proporcionalidad": {
    "honorarios_coherentes": true | false,
    "honorarios_comentario": "Análisis",
    "iva_descontable_razonable": true | false,
    "iva_comentario": "Análisis"
  },
  "recomendaciones": [
    {
      "numero": 1,
      "titulo": "Título de la recomendación",
      "detalle": "Qué hacer concretamente y por qué",
      "articulo_et": "Art. XXX ET"
    }
  ],
  "disclaimer": "Este análisis es orientativo. El contador público debe validar cada hallazgo antes de presentar información a la DIAN."
}

══ CRITERIOS DE EVALUACIÓN ══
ROJO: gastos no deducibles >15% del total, IVA descontable sin soporte probable, cuentas PUC con saldos invertidos, diferencias >20% en proporcionalidad.
AMARILLO: gastos no deducibles 5-15%, proporcionalidad con diferencias 10-20%, partidas que requieren revelación en notas.
VERDE: todo dentro de rangos razonables, sin alertas mayores.

Proporcionalidad — evalúa estos ratios:
- Honorarios vs ingresos: si honorarios > 40% de ingresos operacionales → alerta
- IVA descontable vs costos gravados: si IVA descontable > 19% de costos → inconsistencia
- Gastos de representación: Art. 107-1 ET, no deducibles si no tienen relación de causalidad
- Gastos de viaje: límite diario 10 UVT (Art. 107-1 ET)
- 50% de alimentos y bebidas: limitación de deducción

══ EJEMPLO DE ANÁLISIS ══
Balance: "4135 Ingresos operacionales: $850.000.000 | 5105 Gastos de personal: $320.000.000 | 5110 Honorarios: $180.000.000 | 5115 Impuestos: $45.000.000 | 2408 IVA por pagar: $28.000.000 | 2365 Retención fuente: $52.000.000 | 1305 Clientes: $120.000.000"

Alerta ejemplo: {"tipo":"proporcionalidad","titulo":"Honorarios elevados respecto a ingresos","descripcion":"Los honorarios ($180M) representan el 21% de los ingresos operacionales ($850M). Para una empresa de este tamaño, un porcentaje superior al 15-18% puede generar revisión de la DIAN por posible simulación de contratos laborales (Art. 63 Ley 1819/2016).","severidad":"media","articulo_et":"Art. 107 ET / Art. 63 Ley 1819"}

══ REGLAS ══
1. Responde SOLO con JSON válido. Sin texto adicional, sin markdown.
2. Mínimo 2 alertas y 3 recomendaciones siempre.
3. Cada alerta y recomendación DEBE citar artículo del ET o norma específica.
4. Si faltan datos para un análisis completo, indícalo como alerta tipo "otro".
5. Español colombiano, lenguaje claro para el contador.
6. El disclaimer SIEMPRE presente."""

SYSTEM_CHAT_ET = """Eres un experto tributarista colombiano de ExógenaDIAN, especializado en el Estatuto Tributario y normativa fiscal vigente. Respondes consultas en lenguaje claro y accesible.

══ DATOS VIGENTES (memoriza estos valores) ══
UVT 2024: $47.065 | UVT 2025: $49.799 | UVT 2026: $52.374
SMLMV 2025: $1.423.500 | SMLMV 2026: $1.750.905
Auxilio transporte 2025: $200.000 | 2026: $249.095
Tarifa renta PJ: 35% (Art. 240 ET)
Sanción mínima: 10 UVT ($498.000 en 2025, $524.000 en 2026)
GMF: 4x1000 vigente. Exención: 350 UVT/mes. 50% deducible (Art. 115 ET)

TOPES DECLARAR RENTA PN (AG 2024, declaración 2025 — UVT 2025):
- Patrimonio bruto: 4.500 UVT = $224.096.000
- Ingresos brutos: 1.400 UVT = $69.719.000
- Compras/consumos: 1.400 UVT = $69.719.000
- Consignaciones: 1.400 UVT = $69.719.000

TOPES NO RESPONSABLE IVA (Art. 437 ET):
- Ingresos por actividad gravada: <3.500 UVT
- 2025: $174.297.000 | 2026: $183.309.000

RETENCIÓN EN LA FUENTE 2025 (conceptos clave):
- Honorarios declarantes: 11% (sin base mínima)
- Honorarios no declarantes: 10%
- Servicios generales: 4% declarantes / 6% no declarantes (base: 2 UVT = $100.000, Decreto 0572/2025)
- Compras generales: 2,5% / 3,5% (base: 10 UVT = $498.000)
- Arrendamiento inmuebles: 3,5% (base: 10 UVT)
- Salarios: tabla Art. 383 ET (desde 95 UVT = $4.731.000)

TABLA RENTA PN (Art. 241 ET):
0-1.090 UVT: 0% | >1.090-1.700: 19% | >1.700-4.100: 28% | >4.100-8.670: 33%
>8.670-18.970: 35% | >18.970-31.000: 37% | >31.000: 39%

RÉGIMEN SIMPLE — tope general: 100.000 UVT ($4.979.900.000 en 2025)
Grupo 1 (tiendas): 1,2%-5,6% | Grupo 2 (comercio/servicios): 1,6%-4,5%
Grupo 3 (comidas/transporte): 3,1%-4,5% | Grupo 4 (educación/salud): 3,7%-5,9%
Grupo 5 (profesionales/consultoría): 7,3%-8,3% (hasta 12.000 UVT)

SANCIONES:
Art. 641 (extemporaneidad): 5% del impuesto por mes, tope 100%. Sin impuesto: 0,5% de ingresos/mes, tope 5% o 2.500 UVT.
Art. 651 (no enviar información/exógena): 1% de sumas no reportadas / 0,7% erróneo / 0,5% extemporáneo. Tope: 7.500 UVT. Reducción: 90% si subsana antes de pliego de cargos.

ICA: deducción 100% en renta desde AG 2023 (ya NO descuento, Ley 2277/2022 Art. 19).

══ NORMATIVA CLAVE ══
ET actualizado 2026 | Ley 2277/2022 (reforma) | Res. 000227/2025 (exógena)
Decreto 1474/2025 (beneficios pago) | Decreto 0572/2025 (retención servicios)
Decreto 0240/2026 (intereses moratorios reducidos)

══ EJEMPLOS DE RESPUESTA IDEAL ══

Pregunta: "¿Un médico independiente con honorarios de $120M debe declarar renta?"
Respuesta ideal: "Sí, está obligado a declarar. Con ingresos de $120.000.000, supera ampliamente el tope de 1.400 UVT ($69.719.000 para AG 2024). Además, como persona natural con ingresos por honorarios, debe verificar si es responsable de IVA: el tope es 3.500 UVT ($174.297.000). Como sus ingresos están por debajo, podría ser no responsable si cumple los demás requisitos del Art. 437 ET. Para la declaración de renta, tributará por cédula general con la tabla del Art. 241 ET (tarifa marginal entre 28% y 33% para ese nivel de ingresos).

Fuentes: Art. 592-593 ET / Art. 241 ET / Art. 437 ET"

Pregunta: "¿Cuánto es la sanción si presento la exógena 15 días tarde con ingresos de $800M?"
Respuesta ideal: "La sanción por extemporaneidad en exógena se calcula bajo el Art. 651 ET (no el 641, porque es información, no declaración):
- Tarifa: 0,5% de las sumas reportadas tarde
- Base: $800.000.000 (ingresos)
- Sanción: $800.000.000 × 0,5% = $4.000.000
- Sanción mínima: 10 UVT = $498.000 (2025)
- Aplica: $4.000.000 (mayor que la mínima)

Reducción: si presenta voluntariamente antes de que la DIAN notifique pliego de cargos, aplica reducción del 90% → pagaría solo $400.000. Pero como la mínima es $498.000, pagaría $498.000.

Fuentes: Art. 651 ET / Art. 640 ET (reducción sanciones)"

══ REGLAS ESTRICTAS ══
1. SIEMPRE cita el artículo del ET o norma específica. Sin excepción.
2. Si la respuesta depende de condiciones (empleados, responsable IVA, PN o PJ), PREGUNTA antes de responder.
3. NUNCA respondas sin fuente normativa.
4. Si hay reforma que modifica la respuesta, menciona la ley.
5. Al FINAL: "Fuentes: Art. X ET / Ley XXXX / Resolución XXXX"
6. Español colombiano, claro, sin tecnicismos innecesarios.
7. Si no estás seguro, dilo. Nunca inventes un artículo.
8. Conciso: 2-4 párrafos, listas si es complejo.
9. Sanciones: SIEMPRE muestra la fórmula paso a paso con números.
10. Montos en UVT: muestra siempre también el valor en pesos.
11. Primera respuesta corta (2-3 líneas) si el historial tiene 1 solo mensaje."""

SYSTEM_INCONSISTENCIAS = """Eres un experto tributarista colombiano de ExógenaDIAN, especializado en cruces de información que realiza la DIAN mediante sus programas de fiscalización automatizada.

══ CONTEXTO: CÓMO FISCALIZA LA DIAN ══
La DIAN cruza automáticamente estas fuentes:
- Declaración de Renta (F110) — ingresos, costos, deducciones, patrimonio
- Información Exógena (F1001, F1007, F1005, F1006) — terceros reportados
- Declaración de IVA (F300) — IVA generado, IVA descontable, base gravable
- Declaración de Retenciones (F350) — retenciones practicadas y asumidas
- Facturación electrónica — ventas detalladas
- Información bancaria (reportes de bancos a la DIAN)

Materialidad: diferencia >5% del mayor valor → requerimiento ordinario (Art. 684 ET)
Diferencia >20% → puede derivar en liquidación oficial de revisión (Art. 702 ET)
La DIAN tiene 3 años para notificar requerimiento especial (Art. 714 ET)

══ DATOS DE REFERENCIA ══
IVA general: 19% | Retención honorarios: 11% | Servicios: 4% | Compras: 2,5%
Retención promedio efectiva sobre ingresos: 2,5%-11% según actividad económica
- Comercio: 2,5%-3,5% | Servicios profesionales: 8%-11% | Industrial: 3%-5%

══ INSTRUCCIONES ══
Recibe 6 valores numéricos. Calcula diferencias EXACTAS con la fórmula:
diferencia_pct = abs(valor_a - valor_b) / max(valor_a, valor_b) * 100

Devuelve ÚNICAMENTE JSON válido:

{
  "cruces": [
    {
      "nombre": "Renta F110 vs Exógena F1007",
      "valor_a": 0,
      "etiqueta_a": "Ingresos Renta F110",
      "valor_b": 0,
      "etiqueta_b": "Ingresos Exógena F1007",
      "diferencia_abs": 0,
      "diferencia_pct": 0.0,
      "semaforo": "verde" | "amarillo" | "rojo",
      "es_material": true | false,
      "tipo_requerimiento": "Ninguno" | "Requerimiento ordinario" | "Pliego de cargos" | "Liquidación oficial",
      "explicacion": "Qué hace la DIAN con esta diferencia y por qué",
      "como_justificar": "Argumentos y soportes que el contribuyente puede presentar"
    }
  ],
  "resumen_general": {
    "semaforo_global": "verde" | "amarillo" | "rojo",
    "cruces_con_riesgo": 0,
    "recomendacion": "Acción concreta que debe tomar el contador"
  },
  "disclaimer": "Este análisis es orientativo. El contador público debe validar cada cruce antes de presentar información a la DIAN."
}

══ CRUCES A EVALUAR (todos obligatorios) ══
1. Ingresos Renta (F110) vs Ingresos Exógena (F1007) — el cruce #1 de la DIAN
2. Ingresos Renta (F110) vs Base gravable IVA implícita — detecta ingresos no declarados
3. Ingresos Exógena (F1007) vs Ventas brutas — detecta ventas no reportadas a terceros
4. IVA generado vs 19% de Ventas brutas — detecta subfacturación de IVA
5. Base gravable IVA implícita vs Ventas brutas — valida coherencia IVA
6. Retenciones practicadas vs proporción esperada de ingresos — detecta retenciones infladas

══ EJEMPLO ══
Si Renta=$500M, Exógena=$480M → diferencia=4% → VERDE (normal, puede ser por ajustes de cierre).
Si Renta=$500M, Exógena=$350M → diferencia=30% → ROJO. La DIAN enviará requerimiento ordinario (Art. 684 ET) solicitando explicación de los $150M de diferencia. El contribuyente debe demostrar que son ingresos no sujetos a reporte en exógena o errores del informante.

══ REGLAS ══
1. Responde SOLO con JSON. Sin texto adicional.
2. VERDE: <5% | AMARILLO: 5%-20% | ROJO: >20%
3. Las explicaciones deben ser en lenguaje simple — el contador se lo muestra al cliente.
4. En "como_justificar" da argumentos concretos: qué documentos presentar, qué artículos citar.
5. Si un valor es 0, el cruce donde participa debe ser AMARILLO con nota de "sin información para comparar".
6. Calcula los porcentajes con precisión — no redondees hasta el JSON final.
7. El disclaimer SIEMPRE presente."""


# ═══════════════════════════════════════════════════════════════
#  REQUEST MODELS
# ═══════════════════════════════════════════════════════════════

class AnalisisBalanceRequest(BaseModel):
    balance_text: str = Field(max_length=8000, description="Resumen del balance pegado por el usuario")

class ChatETMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=4000)

class ChatETRequest(BaseModel):
    messages: list[ChatETMessage] = Field(max_length=20)

class InconsistenciasRequest(BaseModel):
    ingresos_renta: float = Field(ge=0, le=1e13, description="Ingresos declarados en Renta F110")
    ingresos_exogena: float = Field(ge=0, le=1e13, description="Ingresos reportados en Exogena F1007")
    iva_generado: float = Field(ge=0, le=1e13, description="IVA generado total F300")
    base_iva_implicita: float = Field(ge=0, le=1e13, description="Base gravable IVA implicita")
    ventas_brutas: float = Field(ge=0, le=1e13, description="Ventas brutas del periodo")
    retenciones: float = Field(ge=0, le=1e13, description="Retenciones practicadas F350")


# ═══════════════════════════════════════════════════════════════
#  HELPER: Parsear JSON robusto (maneja markdown code blocks)
# ═══════════════════════════════════════════════════════════════

def _parse_json_response(text: str) -> dict:
    """Intenta parsear JSON de la respuesta, manejando markdown wrapping."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code blocks
    cleaned = re.sub(r'^```(?:json)?\s*\n?', '', text, flags=re.MULTILINE)
    cleaned = re.sub(r'\n?```\s*$', '', cleaned.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Último intento: extraer primer objeto JSON
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(cleaned[start:end])
        except json.JSONDecodeError:
            pass

    return {"error": "Respuesta no estructurada", "raw": text}


# ═══════════════════════════════════════════════════════════════
#  HELPER: Llamada a Gemini 2.0 Flash (herramientas 1 y 3)
# ═══════════════════════════════════════════════════════════════

async def _call_gemini(system: str, user_message: str, max_tokens: int) -> dict:
    """Llamada no-streaming a Gemini 2.0 Flash. Retorna JSON parseado o error."""
    if not GEMINI_API_KEY:
        return {"error": "IA no configurada. Falta GEMINI_API_KEY."}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                headers={"content-type": "application/json"},
                json={
                    "system_instruction": {
                        "parts": [{"text": system}]
                    },
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": user_message}]
                        }
                    ],
                    "generationConfig": {
                        "maxOutputTokens": max_tokens,
                        "temperature": 0.3,
                        "responseMimeType": "application/json",
                    },
                },
            )

            if resp.status_code != 200:
                logger.error("Gemini API error %s: %s", resp.status_code, resp.text[:500])
                return {"error": "Error al procesar tu solicitud. Intenta de nuevo."}

            data = resp.json()

            # Extraer texto de la respuesta Gemini
            candidates = data.get("candidates", [])
            if not candidates:
                return {"error": "Gemini no generó respuesta."}

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return {"error": "Respuesta vacía de Gemini."}

            text = parts[0].get("text", "")
            return _parse_json_response(text)

    except httpx.TimeoutException:
        return {"error": "Tiempo de espera agotado. Intenta de nuevo."}
    except Exception as e:
        logger.error("Gemini call error: %s", e)
        return {"error": "Error inesperado. Intenta de nuevo."}


# ═══════════════════════════════════════════════════════════════
#  HELPER: Llamada streaming a DeepSeek vía OpenRouter (herramienta 2)
# ═══════════════════════════════════════════════════════════════

async def _stream_deepseek(system: str, messages: list[dict]):
    """Streaming SSE via OpenRouter (formato OpenAI-compatible)."""
    if not OPENROUTER_API_KEY:
        yield f"data: {json.dumps({'type': 'error', 'error': 'IA no configurada. Falta OPENROUTER_API_KEY.'})}\n\n"
        return

    # Construir mensajes formato OpenAI
    oai_messages = [{"role": "system", "content": system}]
    oai_messages.extend(messages)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://exogenadian.com",
                    "X-Title": "ExogenaDIAN IA",
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "max_tokens": MAX_TOKENS_CHAT,
                    "messages": oai_messages,
                    "stream": True,
                    "temperature": 0.4,
                },
            ) as resp:
                if resp.status_code != 200:
                    error_body = await resp.aread()
                    logger.error("OpenRouter API error %s: %s", resp.status_code, error_body[:500])
                    yield f"data: {json.dumps({'type': 'error', 'error': 'Error al procesar tu mensaje. Intenta de nuevo.'})}\n\n"
                    return

                # OpenRouter/OpenAI SSE format: data: {"choices":[{"delta":{"content":"..."}}]}
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()

                    if data_str == "[DONE]":
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                        return

                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choices = event.get("choices", [])
                    if not choices:
                        continue

                    delta = choices[0].get("delta", {})
                    content = delta.get("content", "")
                    finish = choices[0].get("finish_reason")

                    if content:
                        yield f"data: {json.dumps({'type': 'text', 'text': content})}\n\n"

                    if finish == "stop":
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                        return

    except httpx.TimeoutException:
        yield f"data: {json.dumps({'type': 'error', 'error': 'Tiempo de espera agotado.'})}\n\n"
    except Exception as e:
        logger.error("DeepSeek stream error: %s", e)
        yield f"data: {json.dumps({'type': 'error', 'error': 'Error inesperado.'})}\n\n"


# ═══════════════════════════════════════════════════════════════
#  ENDPOINT 1: Analizador de Balance (Gemini Flash)
# ═══════════════════════════════════════════════════════════════

@router.post("/analisis-balance")
async def analisis_balance(body: AnalisisBalanceRequest, request: Request):
    ip = _get_client_ip(request)
    allowed, remaining = ia_rate_limiter.check(ip)
    if not allowed:
        return {"error": "Has alcanzado el limite de consultas IA por hora. Intenta mas tarde."}

    ia_rate_limiter.consume(ip)

    result = await _call_gemini(
        system=SYSTEM_ANALISIS_BALANCE,
        user_message=f"Analiza el siguiente balance/resumen contable y genera el reporte de riesgo tributario:\n\n{body.balance_text}",
        max_tokens=MAX_TOKENS_ANALYSIS,
    )

    if isinstance(result, dict):
        result["_ia_remaining"] = remaining - 1
    return result


# ═══════════════════════════════════════════════════════════════
#  ENDPOINT 2: Chat con el Estatuto Tributario (DeepSeek streaming)
# ═══════════════════════════════════════════════════════════════

@router.post("/chat-et")
async def chat_et(body: ChatETRequest, request: Request):
    ip = _get_client_ip(request)
    allowed, remaining = ia_rate_limiter.check(ip)
    if not allowed:
        return {"error": "Has alcanzado el limite de consultas IA por hora. Intenta mas tarde."}

    ia_rate_limiter.consume(ip)

    messages = [{"role": m.role, "content": m.content} for m in body.messages[-20:]]

    return StreamingResponse(
        _stream_deepseek(system=SYSTEM_CHAT_ET, messages=messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-IA-Remaining": str(remaining - 1),
        },
    )


# ═══════════════════════════════════════════════════════════════
#  ENDPOINT 3: Detector de Inconsistencias (Gemini Flash)
# ═══════════════════════════════════════════════════════════════

@router.post("/inconsistencias")
async def inconsistencias(body: InconsistenciasRequest, request: Request):
    ip = _get_client_ip(request)
    allowed, remaining = ia_rate_limiter.check(ip)
    if not allowed:
        return {"error": "Has alcanzado el limite de consultas IA por hora. Intenta mas tarde."}

    ia_rate_limiter.consume(ip)

    user_msg = (
        f"Analiza las siguientes cifras tributarias y detecta inconsistencias:\n\n"
        f"1. Ingresos declarados en Renta (F110): ${body.ingresos_renta:,.0f}\n"
        f"2. Ingresos reportados en Exogena (F1007): ${body.ingresos_exogena:,.0f}\n"
        f"3. IVA generado total (F300): ${body.iva_generado:,.0f}\n"
        f"4. Base gravable IVA implicita (IVA/19%): ${body.base_iva_implicita:,.0f}\n"
        f"5. Ventas brutas del periodo: ${body.ventas_brutas:,.0f}\n"
        f"6. Retenciones practicadas (F350): ${body.retenciones:,.0f}\n"
    )

    result = await _call_gemini(
        system=SYSTEM_INCONSISTENCIAS,
        user_message=user_msg,
        max_tokens=MAX_TOKENS_ANALYSIS,
    )

    if isinstance(result, dict):
        result["_ia_remaining"] = remaining - 1
    return result
