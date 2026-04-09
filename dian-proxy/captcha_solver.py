"""
Resolver Cloudflare Turnstile usando CapSolver API.
Documentación: https://docs.capsolver.com/en/guide/antibots/cloudflare-turnstile/
"""
import asyncio
import os
import httpx

CAPSOLVER_API = "https://api.capsolver.com"


async def solve_turnstile(site_key: str, page_url: str, timeout: int = 60, retries: int = 2) -> str | None:
    """
    Enviar tarea a CapSolver para resolver Cloudflare Turnstile.
    Retorna el token resuelto o None si falla.
    Reintenta hasta `retries` veces si hay timeout.
    """
    api_key = os.getenv("CAPSOLVER_API_KEY", "")
    if not api_key:
        raise ValueError("CAPSOLVER_API_KEY no configurada")

    import logging
    logger = logging.getLogger("exogenadian.captcha")

    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                # Crear tarea
                logger.info("[CAPTCHA] Intento %d/%d — sitekey=%s", attempt, retries, site_key[:20])
                create_resp = await client.post(f"{CAPSOLVER_API}/createTask", json={
                    "clientKey": api_key,
                    "task": {
                        "type": "AntiTurnstileTaskProxyLess",
                        "websiteURL": page_url,
                        "websiteKey": site_key,
                    }
                })
                create_data = create_resp.json()

                if create_data.get("errorId", 1) != 0:
                    error_desc = create_data.get("errorDescription", "Unknown error")
                    logger.warning("[CAPTCHA] createTask error: %s", error_desc)
                    if attempt < retries:
                        await asyncio.sleep(2)
                        continue
                    raise RuntimeError(f"CapSolver createTask error: {error_desc}")

                task_id = create_data["taskId"]

                # Polling hasta obtener resultado
                for _ in range(timeout):
                    await asyncio.sleep(1)
                    result_resp = await client.post(f"{CAPSOLVER_API}/getTaskResult", json={
                        "clientKey": api_key,
                        "taskId": task_id,
                    })
                    result_data = result_resp.json()

                    status = result_data.get("status", "")
                    if status == "ready":
                        token = result_data.get("solution", {}).get("token")
                        logger.info("[CAPTCHA] Resuelto en intento %d", attempt)
                        return token
                    elif status == "failed":
                        error_desc = result_data.get("errorDescription", "Task failed")
                        logger.warning("[CAPTCHA] Task failed: %s", error_desc)
                        break  # Sale del polling, reintenta
                    # status == "processing" → seguir esperando

                logger.warning("[CAPTCHA] Timeout en intento %d/%d", attempt, retries)
        except RuntimeError:
            raise
        except Exception as e:
            logger.error("[CAPTCHA] Error en intento %d: %s", attempt, str(e)[:100])
            if attempt >= retries:
                raise

    return None  # Todos los intentos fallaron


async def get_balance() -> float:
    """Consultar balance disponible en CapSolver."""
    api_key = os.getenv("CAPSOLVER_API_KEY", "")
    if not api_key:
        return 0.0

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{CAPSOLVER_API}/getBalance", json={
            "clientKey": api_key,
        })
        data = resp.json()
        return data.get("balance", 0.0)
