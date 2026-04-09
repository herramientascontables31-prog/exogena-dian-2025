"""
Scraper del portal MUISCA de la DIAN para consulta de estado RUT.
Usa Playwright (headless Chromium) + CapSolver para Cloudflare Turnstile.
Incluye Circuit Breaker para detectar bloqueos y autocorregir.
Browser Pool para reusar instancias de Chromium y soportar miles de usuarios.
"""
import asyncio
import logging
import re
import time
from dataclasses import dataclass, field

from playwright.async_api import async_playwright, Page, Browser, Playwright

from captcha_solver import solve_turnstile

logger = logging.getLogger("dian_scraper")

DIAN_URL = "https://muisca.dian.gov.co/WebRutMuisca/DefConsultaEstadoRUT.faces"

# Selectores JSF del formulario DIAN
SEL_NIT_INPUT = 'input[name="vistaConsultaEstadoRUT:formConsultaEstadoRUT:numNit"]'
SEL_ESTADO = '#vistaConsultaEstadoRUT\\:formConsultaEstadoRUT\\:estado'
SEL_NOMBRE = '#vistaConsultaEstadoRUT\\:formConsultaEstadoRUT\\:nombre'
SEL_TURNSTILE = 'iframe[src*="challenges.cloudflare.com"]'
SEL_TURNSTILE_INPUT = 'input[name="cf-turnstile-response"]'

# Señales de bloqueo Cloudflare
CLOUDFLARE_SIGNALS = [
    "just a moment", "checking your browser", "ray id",
    "cloudflare", "access denied", "error 1015",
    "error 403", "you have been blocked",
]


# ═══════════════════════════════════════════════════════════════
#  BROWSER POOL — reusar instancias de Chromium
# ═══════════════════════════════════════════════════════════════

class BrowserPool:
    """
    Pool de browsers Chromium para evitar crear/destruir por cada request.
    Cada consulta DIAN usa un context nuevo (aislado) sobre un browser compartido.
    Semáforo limita consultas DIAN concurrentes por worker (Chromium es pesado).
    """
    def __init__(self, max_concurrent: int = 5):
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._request_count = 0
        self._max_requests_before_restart = 200

    async def _start_playwright(self):
        """Iniciar o reiniciar Playwright completamente."""
        # Cerrar todo lo anterior
        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        self._browser = None
        self._playwright = None

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--single-process",
                "--disable-extensions",
            ],
        )
        self._request_count = 0
        logger.info("[BrowserPool] Browser Chromium iniciado")

    async def _ensure_browser(self):
        if self._browser:
            try:
                if self._browser.is_connected():
                    return
            except Exception:
                pass
            # Browser muerto — reiniciar todo
            logger.warning("[BrowserPool] Browser desconectado, reiniciando...")
        await self._start_playwright()

    async def get_context(self):
        """Obtener un context aislado. Usar con 'async with pool.acquire():'."""
        async with self._lock:
            await self._ensure_browser()
            self._request_count += 1
            if self._request_count > self._max_requests_before_restart:
                logger.info("[BrowserPool] Reiniciando browser (límite de requests)")
                await self._start_playwright()
        try:
            context = await self._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="es-CO",
            )
            return context
        except Exception as e:
            logger.error("[BrowserPool] Error creando context: %s — reiniciando", str(e)[:100])
            async with self._lock:
                await self._start_playwright()
            context = await self._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="es-CO",
            )
            return context

    async def _restart_browser(self):
        await self._start_playwright()

    async def shutdown(self):
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass

    @property
    def semaphore(self):
        return self._semaphore


# Pool global — un browser compartido por worker, máx 5 consultas DIAN simultáneas
browser_pool = BrowserPool(max_concurrent=5)


# ═══════════════════════════════════════════════════════════════
#  CIRCUIT BREAKER
# ═══════════════════════════════════════════════════════════════

@dataclass
class CircuitBreaker:
    """
    Patrón Circuit Breaker para manejar bloqueos de la DIAN.

    Estados:
      CLOSED  → Todo normal, se permiten consultas
      OPEN    → Bloqueado, NO se permiten consultas (esperar cooldown)
      HALF    → Probando con 1 consulta para ver si se recuperó
    """
    state: str = "CLOSED"           # CLOSED | OPEN | HALF_OPEN
    failures: int = 0               # Fallos consecutivos
    failure_threshold: int = 3      # Fallos antes de abrir circuito
    success_threshold: int = 2      # Éxitos en HALF_OPEN para cerrar
    half_open_successes: int = 0
    opened_at: float = 0            # Timestamp cuando se abrió
    cooldown_seconds: float = 900   # 15 minutos inicial
    max_cooldown: float = 7200      # 2 horas máximo
    last_error: str = ""
    total_blocks: int = 0           # Total de veces bloqueado
    _alert_callback: object = None

    def set_alert_callback(self, fn):
        self._alert_callback = fn

    def _alert(self, message: str):
        logger.warning(f"[CircuitBreaker] {message}")
        if self._alert_callback:
            try:
                self._alert_callback(message)
            except Exception:
                pass

    def can_request(self) -> bool:
        """¿Se puede hacer una consulta ahora?"""
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            elapsed = time.time() - self.opened_at
            if elapsed >= self.cooldown_seconds:
                self.state = "HALF_OPEN"
                self.half_open_successes = 0
                logger.info(f"[CircuitBreaker] HALF_OPEN — probando recuperación")
                return True
            return False
        # HALF_OPEN: permitir consultas de prueba
        return True

    def record_success(self):
        """Registrar consulta exitosa."""
        if self.state == "HALF_OPEN":
            self.half_open_successes += 1
            if self.half_open_successes >= self.success_threshold:
                self.state = "CLOSED"
                self.failures = 0
                self.cooldown_seconds = 900  # Reset cooldown
                self._alert("RECUPERADO — Circuito cerrado, DIAN respondiendo normalmente")
                logger.info("[CircuitBreaker] CLOSED — recuperado")
        elif self.state == "CLOSED":
            self.failures = 0  # Reset contador de fallos

    def record_failure(self, error: str = ""):
        """Registrar fallo (bloqueo, timeout, error)."""
        self.last_error = error
        self.failures += 1

        if self.state == "HALF_OPEN":
            # Fallo durante prueba → volver a OPEN con cooldown mayor
            self.state = "OPEN"
            self.opened_at = time.time()
            self.cooldown_seconds = min(self.cooldown_seconds * 2, self.max_cooldown)
            self.total_blocks += 1
            self._alert(
                f"BLOQUEADO DE NUEVO — Cooldown extendido a {self.cooldown_seconds // 60:.0f} min. "
                f"Error: {error[:100]}"
            )
        elif self.failures >= self.failure_threshold:
            self.state = "OPEN"
            self.opened_at = time.time()
            self.total_blocks += 1
            self._alert(
                f"CIRCUITO ABIERTO — DIAN bloqueada. Pausa de {self.cooldown_seconds // 60:.0f} min. "
                f"Error: {error[:100]}. Bloqueos totales: {self.total_blocks}"
            )

    def get_status(self) -> dict:
        """Estado actual para el endpoint /api/health."""
        info = {
            "state": self.state,
            "failures": self.failures,
            "total_blocks": self.total_blocks,
            "last_error": self.last_error,
        }
        if self.state == "OPEN":
            remaining = self.cooldown_seconds - (time.time() - self.opened_at)
            info["retry_in_seconds"] = max(0, int(remaining))
            info["cooldown_minutes"] = self.cooldown_seconds / 60
        return info


# Singleton del circuit breaker
circuit_breaker = CircuitBreaker()


# ═══════════════════════════════════════════════════════════════
#  DETECCIÓN DE BLOQUEO
# ═══════════════════════════════════════════════════════════════

def _is_cloudflare_block(html: str) -> bool:
    """Detectar si la respuesta es una página de bloqueo de Cloudflare."""
    html_lower = html.lower()
    matches = sum(1 for signal in CLOUDFLARE_SIGNALS if signal in html_lower)
    return matches >= 2  # Al menos 2 señales para confirmar


async def _check_page_blocked(page: Page) -> str | None:
    """Verificar si la página actual es un bloqueo. Retorna motivo o None."""
    try:
        html = await page.content()
        if _is_cloudflare_block(html):
            return "Cloudflare block detectado"

        # Verificar HTTP status via response
        title = await page.title()
        if "403" in title or "access denied" in title.lower():
            return f"HTTP 403 — {title}"
        if "error" in title.lower() and "dian" not in title.lower():
            return f"Página de error — {title}"

    except Exception as e:
        return f"Error verificando página: {str(e)[:80]}"
    return None


# ═══════════════════════════════════════════════════════════════
#  SCRAPER PRINCIPAL
# ═══════════════════════════════════════════════════════════════

async def _extract_turnstile_sitekey(page: Page) -> str | None:
    """Extraer el sitekey de Cloudflare Turnstile de la página."""
    sitekey = await page.evaluate("""
        () => {
            const widget = document.querySelector('[data-sitekey]');
            if (widget) return widget.getAttribute('data-sitekey');
            const scripts = document.querySelectorAll('script');
            for (const s of scripts) {
                const match = s.textContent.match(/sitekey['":\\s]+['"]([\\w-]+)['"]/);
                if (match) return match[1];
            }
            const iframe = document.querySelector('iframe[src*="challenges.cloudflare.com"]');
            if (iframe) {
                const m = iframe.src.match(/[?&]k=([\\w-]+)/);
                if (m) return m[1];
            }
            return null;
        }
    """)
    return sitekey


async def _inject_turnstile_token(page: Page, token: str):
    """Inyectar el token de Turnstile resuelto en el formulario."""
    await page.evaluate("""
        (token) => {
            const input = document.querySelector('input[name="cf-turnstile-response"]');
            if (input) {
                input.value = token;
                input.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }
    """, token)


async def _parse_resultado(page: Page) -> dict:
    """Parsear la página de resultado después del submit."""
    result = {
        "razon_social": "",
        "estado_rut": "",
        "tipo_persona": "",
        "responsabilidades": [],
    }

    try:
        await page.wait_for_selector(
            f"{SEL_ESTADO}, div.elDivScroll, .ui-messages-error",
            timeout=15000,
        )
    except Exception:
        # Verificar si es bloqueo
        block = await _check_page_blocked(page)
        if block:
            result["_blocked"] = True
            result["error"] = f"Bloqueado: {block}"
        else:
            result["error"] = "Timeout esperando respuesta de la DIAN"
        return result

    # Verificar error modal
    error_modal = await page.query_selector("div.elDivScroll")
    if error_modal:
        error_text = await error_modal.inner_text()
        result["error"] = error_text.strip()[:200]
        return result

    # Extraer estado del RUT
    estado_el = await page.query_selector(SEL_ESTADO)
    if estado_el:
        estado_text = (await estado_el.inner_text()).strip()
        match = re.search(r'(ACTIVO|CANCELADO|SUSPENDIDO|NO REGISTRADO)', estado_text, re.IGNORECASE)
        result["estado_rut"] = match.group(1).upper() if match else estado_text

    # Extraer información usando selectores JSF específicos y texto de página
    page_text = await page.inner_text("body")

    # Intentar extraer por selectores JSF directos
    try:
        nombre_el = await page.query_selector(SEL_NOMBRE)
        if nombre_el:
            nombre = (await nombre_el.inner_text()).strip()
            if nombre and len(nombre) > 2:
                result["razon_social"] = nombre.upper()
    except Exception:
        pass

    # Si no se encontró por selector, buscar en texto de página
    if not result["razon_social"]:
        # Para persona jurídica: Razón Social
        m = re.search(r'Raz[oó]n\s+Social[:\s]+([^\n\r]{3,80})', page_text, re.IGNORECASE)
        if m:
            rs = re.sub(r'[\t]+', ' ', m.group(1)).strip()
            rs = re.sub(r'\s{2,}', ' ', rs)
            if len(rs) > 2:
                result["razon_social"] = rs.upper()

    # Para persona natural: extraer campos individuales por selectores JSF
    if not result["razon_social"]:
        nombres = {}
        selectors = {
            "p_apellido": 'span[id*="primerApellido"], td:has(> label:text-is("Primer Apellido")) + td',
            "s_apellido": 'span[id*="segundoApellido"], td:has(> label:text-is("Segundo Apellido")) + td',
            "p_nombre": 'span[id*="primerNombre"], td:has(> label:text-is("Primer Nombre")) + td',
            "o_nombres": 'span[id*="otrosNombres"], td:has(> label:text-is("Otros Nombres")) + td',
        }
        for campo, sel in selectors.items():
            try:
                el = await page.query_selector(sel)
                if el:
                    val = (await el.inner_text()).strip()
                    # Filtrar: no debe contener etiquetas como "Segundo Apellido"
                    if val and len(val) > 1 and not re.match(r'(?:Primer|Segundo|Otros)\s', val, re.IGNORECASE):
                        nombres[campo] = val
            except Exception:
                pass

        # Fallback: regex en texto (más cuidadoso con etiquetas)
        if not nombres:
            # Buscar líneas que tengan el patrón: "Etiqueta\tValor" o "Etiqueta: Valor"
            for campo, pattern in [
                ("p_apellido", r'Primer\s+Apellido[\s:\t]+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{1,25})'),
                ("s_apellido", r'Segundo\s+Apellido[\s:\t]+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{1,25})'),
                ("p_nombre", r'Primer\s+Nombre[\s:\t]+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{1,25})'),
                ("o_nombres", r'Otros\s+Nombres[\s:\t]+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{1,25})'),
            ]:
                m = re.search(pattern, page_text)
                if m:
                    val = m.group(1).strip()
                    # Asegurarse que el valor no sea otra etiqueta
                    if val and val.upper() not in ('SEGUNDO', 'PRIMER', 'OTROS', 'APELLIDO', 'NOMBRE', 'N/A'):
                        nombres[campo] = val

        if nombres:
            parts = [
                nombres.get("p_nombre", ""),
                nombres.get("o_nombres", ""),
                nombres.get("p_apellido", ""),
                nombres.get("s_apellido", ""),
            ]
            full_name = " ".join(p.strip() for p in parts if p.strip())
            if full_name:
                result["razon_social"] = full_name.upper()

    # Tipo de persona
    if re.search(r'Persona\s+Jur[ií]dica', page_text, re.IGNORECASE):
        result["tipo_persona"] = "JURÍDICA"
    elif re.search(r'Persona\s+Natural', page_text, re.IGNORECASE):
        result["tipo_persona"] = "NATURAL"

    # Responsabilidades fiscales
    for name, pattern in [
        ("Gran Contribuyente", r'[Gg]ran\s+[Cc]ontribuyente'),
        ("Autorretenedor", r'[Aa]uto[r]?retenedor'),
        ("Agente de Retención IVA", r'[Aa]gente\s+de\s+[Rr]etenci[oó]n.*IVA'),
        ("Responsable de IVA", r'[Rr]esponsable\s+de\s+IVA'),
        ("No Responsable de IVA", r'[Nn]o\s+[Rr]esponsable\s+de\s+IVA'),
        ("Régimen Simple", r'[Rr][eé]gimen\s+[Ss]imple'),
    ]:
        if re.search(pattern, page_text):
            result["responsabilidades"].append(name)

    return result


async def consultar_dian(nit: str) -> dict:
    """
    Consultar estado RUT de un NIT en el portal MUISCA de la DIAN.
    Respeta el circuit breaker — si está abierto, retorna error inmediato.
    Usa browser pool para reusar Chromium y soportar alta concurrencia.
    """
    nit = str(nit).strip().replace(".", "").replace("-", "").split("-")[0]

    # Circuit breaker check
    if not circuit_breaker.can_request():
        status = circuit_breaker.get_status()
        retry_in = status.get("retry_in_seconds", 0)
        return {
            "nit": nit,
            "error": f"DIAN temporalmente no disponible. Reintentando en {retry_in // 60} min.",
            "fuente": "DIAN MUISCA (pausado)",
            "_circuit_open": True,
        }

    # Semáforo: limita consultas DIAN concurrentes (Chromium es pesado)
    async with browser_pool.semaphore:
        context = await browser_pool.get_context()
        page = await context.new_page()

        try:
            # 1. Navegar al portal
            logger.info("[DIAN %s] Navegando a %s", nit, DIAN_URL)
            response = await page.goto(DIAN_URL, wait_until="domcontentloaded", timeout=45000)
            logger.info("[DIAN %s] Respuesta HTTP %s", nit, response.status if response else "None")

            # 2. Verificar bloqueo inmediato
            if response and response.status in (403, 503, 429):
                circuit_breaker.record_failure(f"HTTP {response.status}")
                return {"nit": nit, "error": f"DIAN respondió HTTP {response.status}", "fuente": "DIAN MUISCA"}

            block = await _check_page_blocked(page)
            if block:
                logger.warning("[DIAN %s] Bloqueado: %s", nit, block)
                circuit_breaker.record_failure(block)
                return {"nit": nit, "error": block, "fuente": "DIAN MUISCA"}

            # 3. Buscar y resolver Turnstile
            sitekey = await _extract_turnstile_sitekey(page)
            logger.info("[DIAN %s] Turnstile sitekey: %s", nit, sitekey[:20] if sitekey else "None")
            if sitekey:
                token = await solve_turnstile(sitekey, DIAN_URL)
                logger.info("[DIAN %s] CAPTCHA resuelto: %s", nit, "OK" if token else "FAIL")
                if token:
                    await _inject_turnstile_token(page, token)
                    await asyncio.sleep(2)
                else:
                    circuit_breaker.record_failure("CAPTCHA no resuelto")
                    return {"nit": nit, "error": "No se pudo resolver el CAPTCHA", "fuente": "DIAN MUISCA"}

            # 4. Esperar a que el campo NIT esté visible y llenar
            logger.info("[DIAN %s] Buscando campo NIT...", nit)
            try:
                await page.wait_for_selector(SEL_NIT_INPUT, state="visible", timeout=15000)
                logger.info("[DIAN %s] Campo NIT encontrado", nit)
            except Exception as wait_err:
                logger.warning("[DIAN %s] Campo NIT no encontrado con selector principal: %s", nit, str(wait_err)[:100])
                alt_selectors = [
                    'input[id*="numNit"]',
                    'input[type="text"][maxlength]',
                    'input[name*="nit" i]',
                ]
                found = False
                for sel in alt_selectors:
                    el = await page.query_selector(sel)
                    if el:
                        await el.fill(nit)
                        await page.keyboard.press("Enter")
                        found = True
                        break
                if not found:
                    return {"nit": nit, "error": "No se encontró el campo de NIT en la DIAN", "fuente": "DIAN MUISCA"}
                result = await _parse_resultado(page)
                result["nit"] = nit
                result["fuente"] = "DIAN MUISCA"
                if not result.get("error"):
                    circuit_breaker.record_success()
                return result

            await page.fill(SEL_NIT_INPUT, nit)
            await page.keyboard.press("Enter")
            logger.info("[DIAN %s] NIT enviado, esperando resultado...", nit)

            # 5. Parsear resultado
            result = await _parse_resultado(page)
            result["nit"] = nit
            result["fuente"] = "DIAN MUISCA"
            logger.info("[DIAN %s] Resultado: estado=%s, nombre=%s, error=%s",
                        nit, result.get("estado_rut", ""), result.get("razon_social", "")[:50], result.get("error", ""))

            # 6. Circuit breaker: registrar éxito o fallo
            if result.get("_blocked"):
                circuit_breaker.record_failure(result.get("error", "Blocked"))
                del result["_blocked"]
            elif result.get("error") and "timeout" in result["error"].lower():
                circuit_breaker.record_failure(result["error"])
            else:
                circuit_breaker.record_success()

            return result

        except Exception as e:
            error_msg = str(e)[:200]
            logger.error("[DIAN %s] EXCEPCIÓN: %s", nit, error_msg)
            circuit_breaker.record_failure(error_msg)
            return {
                "nit": nit,
                "error": f"Error al consultar DIAN: {error_msg}",
                "fuente": "DIAN MUISCA",
            }
        finally:
            await context.close()


async def consultar_dian_batch(nits: list[str], max_concurrent: int = 3) -> list[dict]:
    """Consultar múltiples NITs con límite de concurrencia y respeto al circuit breaker."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _limited(nit):
        async with semaphore:
            # Si el circuito se abrió durante el batch, no seguir golpeando
            if not circuit_breaker.can_request():
                return {
                    "nit": nit,
                    "error": "DIAN pausada durante consulta masiva",
                    "fuente": "DIAN MUISCA (pausado)",
                }
            return await consultar_dian(nit)

    tasks = [_limited(nit) for nit in nits]
    return await asyncio.gather(*tasks)
