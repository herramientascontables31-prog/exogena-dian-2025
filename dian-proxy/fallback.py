"""
Fuentes de fallback para cuando DIAN MUISCA no responde.
Consulta en cascada: RegistroNIT → datos.gov.co → Einforma → DuckDuckGo.
"""
import asyncio
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


async def buscar_registronit(nit: str) -> dict | None:
    """Consultar registronit.com — directorio público de NITs colombianos."""
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            resp = await client.get(
                f"https://www.registronit.com/{nit}",
                headers=HEADERS,
            )
            if resp.status_code != 200:
                return None

            texto = resp.text
            info = {"nit": nit, "fuente": "RegistroNIT"}

            # Razón social desde <h1>
            h1 = re.findall(r'<h1[^>]*>([^<]+)</h1>', texto, re.IGNORECASE)
            if h1:
                rs = h1[0].strip()
                if len(rs) > 3 and "no encontrado" not in rs.lower():
                    info["razon_social"] = rs.upper()

            # Dirección comercial
            dir_match = re.search(
                r'[Dd]irecci[oó]n\s+comercial\s+es\s+([^.]{5,100})',
                texto,
            )
            if dir_match:
                info["direccion"] = dir_match.group(1).strip().rstrip(".")

            # Estado — NO confiable desde fuentes externas, solo informativo
            # Solo DIAN MUISCA es fuente oficial del estado del RUT
            estado_match = re.search(r'en\s+estado\s+(ACTIVA|CANCELADA|INACTIVA)', texto, re.IGNORECASE)
            if estado_match:
                raw_estado = estado_match.group(1).upper()
                # Normalizar terminación femenina → masculina (DIAN usa masculino)
                estado_map = {"ACTIVA": "ACTIVO", "CANCELADA": "CANCELADO", "INACTIVA": "INACTIVO"}
                info["estado_rut"] = estado_map.get(raw_estado, raw_estado)
                info["_estado_no_oficial"] = True  # Marcar como no verificado en DIAN

            if info.get("razon_social"):
                info["dv"] = _calc_dv(nit)
                return info
    except Exception as e:
        logger.debug("registronit.com lookup failed for %s: %s", nit, e)
    return None


async def buscar_datos_gov(nit: str) -> dict | None:
    """Consultar datos.gov.co — múltiples datasets de empresas colombianas."""
    clean_nit = re.sub(r'[^0-9]', '', nit)
    datasets = [
        # Base de datos de NITs empresas con actividad comercial (Confecámaras)
        ("rtt5-cgkk", f"nit='{clean_nit}'"),
        # Base de datos NIT y Actividad Económica
        ("cas9-r54x", f"nit='{clean_nit}'"),
        # Dataset Pymes (original)
        ("gskn-y6cz", f"nit='{clean_nit}' OR identificacion='{clean_nit}'"),
    ]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            for dataset_id, where_clause in datasets:
                try:
                    resp = await client.get(
                        f"https://www.datos.gov.co/resource/{dataset_id}.json",
                        params={"$where": where_clause, "$limit": 5},
                        headers=HEADERS,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data and isinstance(data, list) and len(data) > 0:
                            return _extraer_info_dict(data[0], "datos.gov.co")
                except Exception:
                    continue
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
                r'(?:NIT|Nit|nit)[\s.:]*' + re.escape(str(nit)) + r'[\s\-–—:,.]+([A-Za-záéíóúñÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ\s&.,]+)',
                r'([A-Za-záéíóúñÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ\s&.,]{5,50}?)[\s\-–—:,.]+(?:NIT|Nit|nit)[\s.:]*' + re.escape(str(nit)),
                r'([A-Za-záéíóúñÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ\s&.,]{3,60}?)\s*-\s*' + re.escape(str(nit)),
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
                        # Limpiar sufijos de sitios web
                        rs = re.sub(r'\s*[-–]\s*(edirectorio|registronit|einforma|empresite).*$', '', rs, flags=re.IGNORECASE)
                        if len(rs.strip()) > 3:
                            return {
                                "nit": nit,
                                "razon_social": rs.strip().upper(),
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

    # NIT
    for campo in ["nit", "Nit", "NIT", "numero_identificacion", "NumeroIdentificacion"]:
        val = emp.get(campo, "")
        if val:
            info["nit"] = str(val).strip()
            break

    # Razón social
    for campo in [
        "razon_social", "Razon_Social", "RazonSocial", "razonSocial",
        "nombre", "Nombre", "nombre_razon_social", "NombreEstablecimiento",
        "organizacion", "nombre_empresa", "empresa", "nombre_propio",
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

    for campo in ["municipio", "codigo_municipio", "ciudad", "mun_comercial", "MunicipioComercial"]:
        val = emp.get(campo, "")
        if val:
            info["municipio"] = str(val).strip()
            break

    if info.get("razon_social") or info.get("direccion"):
        return info
    return None


async def consultar_fallback(nit: str) -> dict:
    """
    Consultar todas las fuentes de fallback en PARALELO.
    Retorna el mejor resultado (prioridad: RegistroNIT > datos.gov > Einforma > web).
    """
    nit = str(nit).strip()

    # Lanzar todas las fuentes en paralelo
    results = await asyncio.gather(
        buscar_registronit(nit),
        buscar_datos_gov(nit),
        buscar_einforma(nit),
        buscar_web(nit),
        return_exceptions=True,
    )

    # Retornar el primer resultado exitoso por orden de prioridad
    for result in results:
        if isinstance(result, Exception) or result is None:
            continue
        if result.get("razon_social"):
            result["nit"] = nit
            result.setdefault("dv", _calc_dv(nit))
            return result

    # Nada encontrado
    return {
        "nit": nit,
        "dv": _calc_dv(nit),
        "razon_social": "",
        "fuente": "No encontrado",
        "error": "NIT no encontrado en ninguna fuente",
    }
