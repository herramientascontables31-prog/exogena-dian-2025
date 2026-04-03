"""
Fuentes de fallback para cuando DIAN MUISCA no responde.
Consulta en cascada: RUES → datos.gov.co (Pymes) → web search.
Adaptado de 1_Generar_Formatos.py:buscar_info_terceros()
"""
import logging
import re
import httpx

logger = logging.getLogger("exogenadian.fallback")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "es-CO,es;q=0.9",
}


def _calc_dv(nit: str) -> int:
    """Calcular dígito de verificación DIAN (módulo 11)."""
    s = str(nit).replace(".", "").replace("-", "").strip()
    pesos = [71, 67, 59, 53, 47, 43, 41, 37, 29, 23, 19, 17, 13, 7, 3]
    padded = s.zfill(15)
    total = sum(int(padded[i]) * pesos[i] for i in range(15))
    mod = total % 11
    return 11 - mod if mod >= 2 else mod


async def buscar_rues(nit: str) -> dict | None:
    """Consultar RUES (Registro Único Empresarial y Social)."""
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.get(
                "https://www.rues.org.co/RM/ConsultaNit_Api",
                params={"nit": str(nit), "tipo": "N"},
                headers={
                    **HEADERS,
                    "Referer": "https://www.rues.org.co/",
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json",
                },
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            registros = data if isinstance(data, list) else \
                data.get("registros", data.get("data", [])) if isinstance(data, dict) else []

            if not registros:
                return None

            reg = registros[0] if isinstance(registros, list) else registros
            return _extraer_info_dict(reg, "RUES")
    except Exception as e:
        logger.debug("RUES lookup failed for %s: %s", nit, e)
        return None


async def buscar_datos_gov(nit: str) -> dict | None:
    """Consultar datos.gov.co — dataset Pymes de Colombia."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Dataset Pymes
            resp = await client.get(
                "https://www.datos.gov.co/resource/gskn-y6cz.json",
                params={
                    "$where": f"nit='{re.sub(r'[^0-9]', '', nit)}' OR identificacion='{re.sub(r'[^0-9]', '', nit)}'",
                    "$limit": 5,
                },
                headers=HEADERS,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list) and len(data) > 0:
                    return _extraer_info_dict(data[0], "datos.gov.co")
    except Exception as e:
        logger.debug("datos.gov.co lookup failed for %s: %s", nit, e)
    return None


async def buscar_einforma(nit: str) -> dict | None:
    """Consultar Einforma.co para información de la empresa."""
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            resp = await client.get(
                f"https://www.einforma.co/servlet/app/portal/ENTP/prod/ETIQUETA_EMPRESA_498/nif/{nit}",
                headers=HEADERS,
            )
            if resp.status_code != 200:
                return None

            texto = resp.text
            info = {"nit": nit, "fuente": "Einforma"}

            # Razón social
            rs_match = re.findall(
                r'<h1[^>]*class="[^"]*nombre[^"]*"[^>]*>([^<]+)</h1>',
                texto, re.IGNORECASE,
            )
            if not rs_match:
                rs_match = re.findall(r"<title>([^<]+?)[\s\-|]", texto)
            # Filtrar falsos positivos (nombre del sitio, no de la empresa)
            FALSOS_POSITIVOS = {"einforma", "einforma colombia", "einforma.co", "empresas", "buscar empresa"}
            if rs_match:
                rs = rs_match[0].strip()
                if len(rs) > 3 and str(nit) not in rs.lower() and rs.strip().lower() not in FALSOS_POSITIVOS:
                    info["razon_social"] = rs.upper()

            # Dirección
            dir_match = re.findall(
                r'(?:Direcci[oó]n|Domicilio)[:\s]*</[^>]+>\s*<[^>]+>([^<]+)',
                texto, re.IGNORECASE,
            )
            if dir_match:
                info["direccion"] = dir_match[0].strip()

            if info.get("razon_social") or info.get("direccion"):
                info["dv"] = _calc_dv(nit)
                return info
    except Exception as e:
        logger.debug("Einforma lookup failed for %s: %s", nit, e)
    return None


async def buscar_web(nit: str) -> dict | None:
    """Búsqueda web como último recurso (DuckDuckGo)."""
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": f"NIT {nit} Colombia empresa"},
                headers=HEADERS,
            )
            if resp.status_code != 200:
                return None

            texto = re.sub(r"<[^>]+>", " ", resp.text)
            texto = re.sub(r"\s+", " ", texto)

            patrones = [
                r'(?:NIT|Nit|nit)[\s.:]*' + re.escape(str(nit)) + r'[\s\-–—:,.]+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s&.,]+)',
                r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s&.,]{5,50}?)[\s\-–—:,.]+(?:NIT|Nit|nit)[\s.:]*' + re.escape(str(nit)),
            ]
            # Palabras que indican basura en la razón social
            RUIDO = {
                "politica", "tratamiento", "datos", "personales", "privacidad",
                "terminos", "condiciones", "certificado", "existencia",
                "representacion", "legal", "camara", "comercio", "registro",
                "consulta", "resultado", "buscar", "busqueda", "colombia",
                "informacion", "empresa", "noticias", "documento", "pdf",
            }
            for patron in patrones:
                matches = re.findall(patron, texto)
                if matches:
                    rs = matches[0].strip().rstrip(".,;:-– ")
                    # Filtrar si tiene palabras de ruido (no es razón social real)
                    palabras = rs.lower().split()
                    ruido_count = sum(1 for p in palabras if p in RUIDO)
                    if 3 < len(rs) < 80 and ruido_count < 2 and len(palabras) <= 10:
                        return {
                            "nit": nit,
                            "razon_social": rs.upper(),
                            "dv": _calc_dv(nit),
                            "fuente": "Búsqueda web",
                        }
    except Exception as e:
        logger.debug("Web search failed for %s: %s", nit, e)
    return None


def _extraer_info_dict(emp: dict, fuente: str) -> dict | None:
    """Extraer información relevante de un dict de respuesta."""
    if not isinstance(emp, dict):
        return None

    info = {"fuente": fuente}

    # Razón social
    for campo in [
        "razon_social", "Razon_Social", "nombre", "Nombre", "razonSocial",
        "RazonSocial", "nombre_razon_social", "NombreEstablecimiento",
        "organizacion", "nombre_empresa", "empresa",
    ]:
        val = emp.get(campo, "")
        if val:
            info["razon_social"] = str(val).strip().upper()
            break

    # DV
    for campo in ["digito_verificacion", "Digito_Verificacion", "dv", "DV"]:
        val = emp.get(campo, "")
        if val is not None and str(val).strip():
            info["dv"] = str(val).strip()
            break

    # Dirección
    for campo in ["direccion", "Direccion", "direccion_comercial", "DireccionComercial"]:
        val = emp.get(campo, "")
        if val:
            info["direccion"] = str(val).strip()
            break

    # Departamento y municipio
    for campo in ["departamento", "codigo_departamento", "departamento_municipio_empresa"]:
        val = emp.get(campo, "")
        if val:
            info["departamento"] = str(val).strip()
            break

    for campo in ["municipio", "codigo_municipio", "ciudad"]:
        val = emp.get(campo, "")
        if val:
            info["municipio"] = str(val).strip()
            break

    if info.get("razon_social") or info.get("direccion"):
        return info
    return None


async def consultar_fallback(nit: str) -> dict:
    """
    Consultar todas las fuentes de fallback en cascada.
    Retorna el primer resultado exitoso.
    """
    nit = str(nit).strip()

    # 1. RUES
    result = await buscar_rues(nit)
    if result:
        result["nit"] = nit
        result.setdefault("dv", _calc_dv(nit))
        return result

    # 2. datos.gov.co
    result = await buscar_datos_gov(nit)
    if result:
        result["nit"] = nit
        result.setdefault("dv", _calc_dv(nit))
        return result

    # 3. Einforma
    result = await buscar_einforma(nit)
    if result:
        return result

    # 4. Búsqueda web
    result = await buscar_web(nit)
    if result:
        return result

    # Nada encontrado
    return {
        "nit": nit,
        "dv": _calc_dv(nit),
        "razon_social": "",
        "fuente": "No encontrado",
        "error": "NIT no encontrado en ninguna fuente",
    }
