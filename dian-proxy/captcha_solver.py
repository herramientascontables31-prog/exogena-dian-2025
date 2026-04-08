"""
Resolver Cloudflare Turnstile usando CapSolver API.
Documentación: https://docs.capsolver.com/en/guide/antibots/cloudflare-turnstile/
"""
import asyncio
import os
import httpx

CAPSOLVER_API = "https://api.capsolver.com"


async def solve_turnstile(site_key: str, page_url: str, timeout: int = 30) -> str | None:
    """
    Enviar tarea a CapSolver para resolver Cloudflare Turnstile.
    Retorna el token resuelto o None si falla.
    """
    api_key = os.getenv("CAPSOLVER_API_KEY", "")
    if not api_key:
        raise ValueError("CAPSOLVER_API_KEY no configurada")

    async with httpx.AsyncClient(timeout=60) as client:
        # Crear tarea
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
                return token
            elif status == "failed":
                error_desc = result_data.get("errorDescription", "Task failed")
                raise RuntimeError(f"CapSolver task failed: {error_desc}")
            # status == "processing" → seguir esperando

    return None  # Timeout


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
