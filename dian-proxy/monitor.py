"""
Monitor de salud del servicio de consulta NIT.
Diseñado para ejecutarse 3x/día via Cloud Scheduler o cron local.

Verifica:
1. Que el backend API responde
2. Que la consulta a DIAN MUISCA funciona
3. Balance de CapSolver

Cron recomendado: 0 8,13,18 * * * (8am, 1pm, 6pm hora Colombia)
"""
import asyncio
import os
import sys
from datetime import datetime

import httpx

# URL del backend desplegado
API_URL = os.getenv("API_URL", "https://dian-proxy-337146111457.southamerica-east1.run.app")
# NIT de prueba: DIAN misma
TEST_NIT = "800197268"
# Email para alertas (futuro: integrar SendGrid o similar)
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "soporte@exogenadian.com")


async def check_health() -> tuple[bool, str]:
    """Verificar que el endpoint /api/health responde."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{API_URL}/api/health")
            if resp.status_code == 200:
                data = resp.json()
                return True, f"OK — Cache: {data.get('cache', {})}"
            return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, f"Error: {str(e)[:100]}"


async def check_nit_query() -> tuple[bool, str]:
    """Verificar que una consulta de NIT funciona end-to-end."""
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.get(f"{API_URL}/api/nit/{TEST_NIT}")
            if resp.status_code == 200:
                data = resp.json()
                rs = data.get("razon_social", "")
                fuente = data.get("fuente", "")
                error = data.get("error", "")
                if error:
                    return False, f"NIT query error: {error}"
                if rs:
                    return True, f"OK — {rs} (fuente: {fuente})"
                return False, "NIT query: sin razón social"
            return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, f"Error: {str(e)[:100]}"


async def check_capsolver_balance() -> tuple[bool, str]:
    """Verificar balance de CapSolver."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{API_URL}/api/stats")
            if resp.status_code == 200:
                data = resp.json()
                balance = data.get("capsolver_balance", 0)
                if balance < 0:
                    return False, "No se pudo consultar balance"
                if balance < 1.0:
                    return False, f"Balance bajo: ${balance:.2f}"
                return True, f"OK — Balance: ${balance:.2f}"
            return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, f"Error: {str(e)[:100]}"


def send_alert(subject: str, body: str):
    """Enviar alerta (placeholder — integrar con SendGrid, Twilio, o email SMTP)."""
    # TODO: Integrar con servicio de email real
    print(f"\n{'='*60}")
    print(f"ALERTA: {subject}")
    print(f"{'='*60}")
    print(body)
    print(f"Enviar a: {ALERT_EMAIL}")
    print(f"{'='*60}\n")


async def run_monitor():
    """Ejecutar todas las verificaciones."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[Monitor ExógenaDIAN] {now}")
    print(f"API URL: {API_URL}")
    print("-" * 40)

    all_ok = True
    report = []

    # 1. Health check
    ok, msg = await check_health()
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] Health check: {msg}")
    report.append(f"Health: {status} — {msg}")
    if not ok:
        all_ok = False

    # 2. NIT query
    ok, msg = await check_nit_query()
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] NIT query: {msg}")
    report.append(f"NIT query: {status} — {msg}")
    if not ok:
        all_ok = False

    # 3. CapSolver balance
    ok, msg = await check_capsolver_balance()
    status = "PASS" if ok else "WARN"
    print(f"  [{status}] CapSolver: {msg}")
    report.append(f"CapSolver: {status} — {msg}")

    print("-" * 40)

    if all_ok:
        print("  RESULTADO: Todo OK")
    else:
        print("  RESULTADO: HAY FALLOS — enviando alerta")
        send_alert(
            f"ExógenaDIAN Monitor — FALLO {now}",
            "\n".join(report),
        )

    return all_ok


if __name__ == "__main__":
    success = asyncio.run(run_monitor())
    sys.exit(0 if success else 1)
