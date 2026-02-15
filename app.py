import streamlit as st
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from collections import defaultdict
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="Exógena DIAN 2025", page_icon="📊", layout="wide")

# === PROTECCIÓN CON CONTRASEÑA ===
CLAVE_ACCESO = "ExoDIAN-2025-PRO"

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("""
    <div style="max-width: 450px; margin: 80px auto; text-align: center;">
        <h1 style="font-size: 2.5rem; margin-bottom: 0.2rem;">📊</h1>
        <h2 style="font-family: serif; font-size: 1.8rem; color: #0B1D3A; margin-bottom: 0.5rem;">Exógena DIAN 2025</h2>
        <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 2rem;">Ingresa tu contraseña de acceso para continuar</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        clave = st.text_input("Contraseña", type="password", placeholder="Ingresa tu contraseña aquí")
        if st.button("Ingresar", use_container_width=True, type="primary"):
            if clave == CLAVE_ACCESO:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta. Verifica tu compra en exogenadian.com")
        
        st.markdown("""
        <div style="text-align: center; margin-top: 2rem;">
            <p style="color: #94a3b8; font-size: 0.82rem;">
                ¿No tienes contraseña? <a href="https://exogenadian.com/#precios" target="_blank" style="color: #1F4E79;">Compra tu acceso aquí</a>
            </p>
        </div>
        """, unsafe_allow_html=True)
    st.stop()

# === ESTILOS ===
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1F4E79; margin-bottom: 0; }
    .sub-header { font-size: 1.1rem; color: #666; margin-top: 0; }
    .metric-card { background: #f8f9fa; border-radius: 10px; padding: 1rem; border-left: 4px solid #1F4E79; }
    .success-box { background: #d4edda; border-radius: 10px; padding: 1rem; border-left: 4px solid #28a745; }
    .stDownloadButton > button { background-color: #1F4E79 !important; color: white !important; font-size: 1.1rem !important; padding: 0.5rem 2rem !important; }
</style>
""", unsafe_allow_html=True)

# === CONSTANTES ===
UVT = 49799
C3UVT = 149397
C12UVT = 597588
NM = "222222222"
TDM = "43"

# === FUNCIONES CORE ===
def calc_dv(n):
    n = str(n).replace(".", "").replace("-", "").strip()
    if not n or not n.isdigit() or n == NM:
        return ""
    pesos = [71, 67, 59, 53, 47, 43, 41, 37, 29, 23, 19, 17, 13, 7, 3]
    np = n.zfill(15)
    s = sum(int(np[i]) * pesos[i] for i in range(15))
    r = s % 11
    return str(11 - r) if r >= 2 else str(r)

def detectar_tipo_doc(nit):
    """Detecta automáticamente el tipo de documento DIAN según el número de identificación.
    
    Tipos soportados:
    - 31: NIT (empresas colombianas, 9 dígitos que inician con 8 o 9)
    - 13: Cédula de ciudadanía (personas naturales colombianas)
    - 12: Tarjeta de identidad (menores de edad) — no distinguible por número
    - 22: Cédula de extranjería — no distinguible por número  
    - 41: Pasaporte (contiene letras)
    - 42: Documento de identificación extranjero (contiene letras)
    - 43: Cuantías menores / sin identificación
    
    Limitación: los tipos 12, 13 y 22 no se pueden distinguir solo por el número.
    Se asume 13 (CC) como default para personas. El contador debe ajustar manualmente
    los casos de TI (12) y CE (22) en el archivo de salida.
    """
    if not nit or nit == NM:
        return TDM  # "43" para cuantías menores
    
    nit = str(nit).strip()
    
    # Limpiar formato decimal (ej: "890904997.0" → "890904997")
    if '.' in nit:
        try:
            nit = str(int(float(nit)))
        except:
            pass
    
    # Si contiene letras → documento extranjero o pasaporte
    if not nit.isdigit():
        # Pasaportes suelen tener formato: 2 letras + números (ej: AB123456)
        # o patrones alfanuméricos cortos
        letras = sum(1 for c in nit if c.isalpha())
        if letras <= 3:
            return "41"  # Pasaporte (pocas letras + números)
        else:
            return "42"  # Documento de identificación extranjero
    
    # NIT de empresa: 9 dígitos, empieza con 8 o 9
    # Ej: 800123456, 890904997, 900555111
    if len(nit) == 9 and nit[0] in ('8', '9'):
        return "31"  # NIT
    
    # NIT de entidad pública o especial: 9+ dígitos con 8 o 9
    if len(nit) >= 9 and nit[0] in ('8', '9'):
        return "31"  # NIT
    
    # Todo lo demás se asume cédula de ciudadanía
    # Nota: TI (12) y CE (22) no se pueden distinguir automáticamente
    return "13"  # Cédula de ciudadanía

def safe_num(v):
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        import math
        if math.isnan(v):
            return 0.0
        return float(v)
    try:
        s = str(v).strip()
        if s.lower() == 'nan' or s == '':
            return 0.0
        return float(s.replace(",", "").replace("$", "").replace(" ", ""))
    except:
        return 0.0

def safe_str(v):
    if v is None:
        return ""
    s = str(v).strip()
    if s.lower() == 'nan':
        return ""
    return s

def en_rango(cta, d, h):
    n = len(d)
    return cta[:n] >= d and cta[:n] <= h

def pad_dpto(v):
    """Formatea código departamento DIAN: 2 dígitos con cero a la izquierda"""
    if not v:
        return ""
    v = str(v).strip()
    if '.' in v:
        try: v = str(int(float(v)))
        except: pass
    if v.lower() == 'nan': return ""
    return v.zfill(2) if v.isdigit() else v

def pad_mpio(v):
    """Formatea código municipio DIAN: 3 dígitos con ceros a la izquierda"""
    if not v:
        return ""
    v = str(v).strip()
    if '.' in v:
        try: v = str(int(float(v)))
        except: pass
    if v.lower() == 'nan': return ""
    return v.zfill(3) if v.isdigit() else v

def buscar_info_terceros(nits_list, progress_bar=None, log_fn=None):
    """Busca info de terceros usando múltiples fuentes de internet."""
    import requests
    from time import sleep
    import re

    def log(msg):
        if log_fn:
            log_fn(msg)

    encontrados = {}
    total = len(nits_list)
    errores_seguidos = 0

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'es-CO,es;q=0.9',
    }

    def buscar_rues(nit):
        try:
            resp = requests.get(
                'https://www.rues.org.co/RM/ConsultaNit_Api',
                params={'nit': str(nit), 'tipo': 'N'},
                headers={**HEADERS, 'Referer': 'https://www.rues.org.co/',
                         'X-Requested-With': 'XMLHttpRequest',
                         'Accept': 'application/json'},
                timeout=12
            )
            if resp.status_code == 200:
                data = resp.json()
                registros = data if isinstance(data, list) else \
                            data.get('registros', data.get('data', [])) if isinstance(data, dict) else []
                if registros and len(registros) > 0:
                    return extraer_info_dict(registros[0]), None
                return None, "Sin resultados"
            return None, f"HTTP {resp.status_code}"
        except Exception as e:
            return None, str(e)[:80]

    def buscar_datos_gov_lote(nits_batch):
        resultados = {}
        datasets = ["c82q-fe7j", "8yz5-t3jw"]
        for ds_id in datasets:
            try:
                nits_str = "','".join(str(n) for n in nits_batch)
                resp = requests.get(
                    f"https://www.datos.gov.co/resource/{ds_id}.json",
                    params={'$where': f"nit in ('{nits_str}')", '$limit': 5000},
                    headers=HEADERS, timeout=20
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data and isinstance(data, list):
                        for emp in data:
                            nit_val = str(emp.get('nit', emp.get('NIT', ''))).strip()
                            if nit_val:
                                info = extraer_info_dict(emp)
                                if info:
                                    resultados[nit_val] = info
                                    resultados[nit_val]['_fuente'] = 'Datos.gov.co'
                        if resultados:
                            return resultados, None
                    return {}, f"Dataset {ds_id}: sin datos"
                else:
                    continue
            except Exception as e:
                continue
        return {}, "Ningún dataset respondió"

    def buscar_einforma(nit):
        try:
            resp = requests.get(
                f'https://www.einforma.co/servlet/app/portal/ENTP/prod/ETIQUETA_EMPRESA_498/nif/{nit}',
                headers=HEADERS, timeout=12, allow_redirects=True
            )
            if resp.status_code == 200:
                info = {'razon_social': '', 'dv': '', 'dir': '', 'dp': '', 'mp': '', 'pais': '169'}
                texto = resp.text
                rs_match = re.findall(r'<h1[^>]*class="[^"]*nombre[^"]*"[^>]*>([^<]+)</h1>', texto, re.IGNORECASE)
                if not rs_match:
                    rs_match = re.findall(r'<title>([^<]+?)[\s\-|]', texto)
                if rs_match:
                    rs = rs_match[0].strip()
                    if len(rs) > 3 and str(nit) not in rs.lower():
                        info['razon_social'] = rs.upper()
                dir_match = re.findall(r'(?:Direcci[oó]n|Domicilio)[:\s]*</[^>]+>\s*<[^>]+>([^<]+)', texto, re.IGNORECASE)
                if dir_match:
                    info['dir'] = dir_match[0].strip()
                if info.get('razon_social') or info.get('dir'):
                    return info, None
            return None, f"HTTP {resp.status_code}"
        except Exception as e:
            return None, str(e)[:80]

    def buscar_web_ddg(nit):
        try:
            resp = requests.get('https://html.duckduckgo.com/html/',
                params={'q': f'NIT {nit} Colombia empresa direccion'}, headers=HEADERS, timeout=12)
            if resp.status_code == 200:
                return extraer_info_web(nit, resp.text), None
            return None, f"HTTP {resp.status_code}"
        except Exception as e:
            return None, str(e)[:80]

    def buscar_web_bing(nit):
        try:
            resp = requests.get(f'https://www.bing.com/search?q=NIT+{nit}+Colombia+empresa+direccion&setlang=es',
                headers=HEADERS, timeout=12)
            if resp.status_code == 200:
                return extraer_info_web(nit, resp.text), None
            return None, f"HTTP {resp.status_code}"
        except Exception as e:
            return None, str(e)[:80]

    def buscar_web_google(nit):
        try:
            query = f"NIT+{nit}+Colombia+empresa+direccion"
            resp = requests.get(f'https://www.google.com/search?q={query}&hl=es&gl=co',
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html', 'Accept-Language': 'es-CO,es;q=0.9'}, timeout=12)
            if resp.status_code == 200:
                return extraer_info_web(nit, resp.text), None
            return None, f"HTTP {resp.status_code}"
        except Exception as e:
            return None, str(e)[:80]

    def extraer_info_web(nit, html):
        info = {'razon_social': '', 'dv': '', 'dir': '', 'dp': '', 'mp': '', 'pais': '169'}
        nit_str = str(nit)
        texto = re.sub(r'<[^>]+>', ' ', html)
        texto = re.sub(r'\s+', ' ', texto)
        patrones_rs = [
            r'(?:NIT|Nit|nit)[\s.:]*' + re.escape(nit_str) + r'[\s\-–—:,.]+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s&.,]+)',
            r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s&.,]{5,50}?)[\s\-–—:,.]+(?:NIT|Nit|nit)[\s.:]*' + re.escape(nit_str),
            r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s&.,]{5,50}?)\s*[-–—]\s*NIT[\s.:]*' + re.escape(nit_str),
        ]
        for patron in patrones_rs:
            matches = re.findall(patron, texto)
            if matches:
                rs = matches[0].strip().rstrip('.,;:-– ')
                if 3 < len(rs) < 120:
                    info['razon_social'] = rs.upper()
                    break
        patrones_dir = [
            r'(?:Direcci[oó]n|Dir\.?|Ubicaci[oó]n)[:\s]+([A-Za-z]{2,3}[\s.]*(?:No\.?\s*)?\d+[\w\s#\-.,No°]+?\d)',
            r'((?:CL|CR|KR|TV|DG|CALLE|CARRERA|AV|AVENIDA|TRANSVERSAL|DIAGONAL)[\s.]*(?:No\.?\s*)?\d+[\w\s#\-.,No°]*\d)',
        ]
        for patron in patrones_dir:
            matches = re.findall(patron, texto, re.IGNORECASE)
            if matches:
                dir_candidata = matches[0].strip()[:100]
                if len(dir_candidata) > 5:
                    info['dir'] = dir_candidata
                    break
        if info.get('razon_social') or info.get('dir'):
            return info
        return None

    def extraer_info_dict(emp):
        if not isinstance(emp, dict):
            return None
        info = {'razon_social': '', 'dv': '', 'dir': '', 'dp': '', 'mp': '', 'pais': '169'}
        for campo in ['razon_social', 'Razon_Social', 'nombre', 'Nombre', 'razonSocial', 'RazonSocial',
                       'nombre_razon_social', 'NombreEstablecimiento', 'organizacion', 'nombre_empresa']:
            val = emp.get(campo, '')
            if val:
                info['razon_social'] = str(val).strip().upper()
                break
        for campo in ['digito_verificacion', 'Digito_Verificacion', 'dv', 'DV', 'digitoVerificacion']:
            val = emp.get(campo, '')
            if val is not None and str(val).strip():
                info['dv'] = str(val).strip()
                break
        for campo in ['direccion', 'Direccion', 'direccion_comercial', 'DireccionComercial', 'dir_comercial']:
            val = emp.get(campo, '')
            if val:
                info['dir'] = str(val).strip()
                break
        for campo in ['codigo_departamento', 'departamento', 'cod_departamento', 'CodigoDepartamento', 'dep_codigo', 'cod_depto']:
            val = emp.get(campo, '')
            if val:
                info['dp'] = pad_dpto(str(val).strip())
                break
        for campo in ['codigo_municipio', 'municipio', 'cod_municipio', 'CodigoMunicipio', 'mun_codigo', 'ciudad', 'cod_ciudad']:
            val = emp.get(campo, '')
            if val:
                info['mp'] = pad_mpio(str(val).strip())
                break
        return info if (info.get('razon_social') or info.get('dir')) else None

    # FLUJO PRINCIPAL
    log("📡 **Paso 1:** Consultando datos.gov.co (lote completo)...")
    try:
        lote_result, lote_error = buscar_datos_gov_lote(nits_list)
        if lote_result:
            encontrados.update(lote_result)
            log(f"  ✅ datos.gov.co: {len(lote_result)} terceros encontrados")
        else:
            log(f"  ❌ datos.gov.co: {lote_error}")
    except Exception as e:
        log(f"  ❌ datos.gov.co: Error — {str(e)[:80]}")

    nits_faltantes = [n for n in nits_list if n not in encontrados]
    rues_funciona = False
    if nits_faltantes:
        log(f"📡 **Paso 2:** Probando RUES ({len(nits_faltantes)} NITs pendientes)...")
        test_nit = nits_faltantes[0]
        try:
            resultado, error = buscar_rues(test_nit)
            if resultado:
                resultado['_fuente'] = 'RUES'
                encontrados[test_nit] = resultado
                rues_funciona = True
                log(f"  ✅ RUES funciona (NIT {test_nit} encontrado)")
            else:
                log(f"  ❌ RUES: {error}")
        except Exception as e:
            log(f"  ❌ RUES no disponible: {str(e)[:80]}")

    nits_faltantes = [n for n in nits_list if n not in encontrados]
    buscador_web = None
    buscadores = [('DuckDuckGo', buscar_web_ddg), ('Bing', buscar_web_bing), ('Google', buscar_web_google)]

    if nits_faltantes:
        log(f"📡 **Paso 3:** Probando buscadores web...")
        test_nit = nits_faltantes[0]
        for nombre_b, fn_b in buscadores:
            try:
                resultado, error = fn_b(test_nit)
                if resultado:
                    resultado['_fuente'] = nombre_b
                    encontrados[test_nit] = resultado
                    buscador_web = (nombre_b, fn_b)
                    log(f"  ✅ {nombre_b} funciona")
                    break
                else:
                    log(f"  ⚠️ {nombre_b}: {error}")
            except Exception as e:
                log(f"  ❌ {nombre_b}: {str(e)[:60]}")
        if not buscador_web:
            log("  ❌ Ningún buscador web funcionó")

    nits_faltantes = [n for n in nits_list if n not in encontrados]
    if nits_faltantes and (rues_funciona or buscador_web):
        fuentes_activas = []
        if rues_funciona: fuentes_activas.append(('RUES', buscar_rues))
        if buscador_web: fuentes_activas.append(buscador_web)
        nombres = " → ".join(f[0] for f in fuentes_activas)
        log(f"🔍 **Paso 4:** Buscando {len(nits_faltantes)} NITs restantes [{nombres}]...")

        for i, nit in enumerate(nits_faltantes):
            if progress_bar:
                progress_bar.progress((i + 1) / len(nits_faltantes),
                    text=f"🔍 {nit} ({i+1}/{len(nits_faltantes)}) — Encontrados: {len(encontrados)}")
            if errores_seguidos >= 15:
                log(f"  ⛔ Detenido tras {errores_seguidos} errores seguidos")
                break
            encontro = False
            for nombre_f, fn_f in fuentes_activas:
                try:
                    resultado, error = fn_f(nit)
                    if resultado:
                        resultado['_fuente'] = nombre_f
                        encontrados[nit] = resultado
                        encontro = True
                        errores_seguidos = 0
                        break
                except Exception:
                    continue
            if not encontro:
                errores_seguidos += 1
            sleep(0.8)

    nits_faltantes = [n for n in nits_list if n not in encontrados]
    if nits_faltantes and len(nits_faltantes) < 30:
        log(f"📡 **Paso 5:** Probando einforma.co ({len(nits_faltantes)} NITs pendientes)...")
        errores_ein = 0
        for nit in nits_faltantes:
            if errores_ein >= 5: break
            try:
                resultado, error = buscar_einforma(nit)
                if resultado:
                    resultado['_fuente'] = 'einforma.co'
                    encontrados[nit] = resultado
                    errores_ein = 0
                else:
                    errores_ein += 1
            except Exception:
                errores_ein += 1
            sleep(1.0)

    n_dir = sum(1 for d in encontrados.values() if d.get('dir'))
    n_rs = sum(1 for d in encontrados.values() if d.get('razon_social'))
    log(f"\n📊 **Resumen:** {len(encontrados)}/{total} terceros — {n_dir} con dirección, {n_rs} con razón social")
    return encontrados, len(encontrados) == 0 and total > 0


def normalizar_texto(t):
    import unicodedata
    if not t: return ""
    t = str(t).upper().strip()
    t = ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')
    for ch in '.,;:-_/\\()[]{}#"\'':
        t = t.replace(ch, ' ')
    t = ' '.join(t.split())
    reemplazos = [
        ('S A S', 'SAS'), ('S A  S', 'SAS'), ('S A', 'SA'), ('S  A', 'SA'),
        ('E S P', 'ESP'), ('E  S  P', 'ESP'), ('E U', 'EU'), ('E  U', 'EU'),
        ('C I', 'CI'), ('C  I', 'CI'), ('N I T', 'NIT'),
        ('SOCIEDAD ANONIMA', 'SA'), ('SOCIEDAD POR ACCIONES SIMPLIFICADA', 'SAS'),
        ('EMPRESA DE SERVICIOS PUBLICOS', 'ESP'), ('LIMITADA', 'LTDA'),
    ]
    for viejo, nuevo in reemplazos:
        t = t.replace(viejo, nuevo)
    return ' '.join(t.split())


def similitud_textos(a, b):
    a = normalizar_texto(a)
    b = normalizar_texto(b)
    if not a or not b: return 0.0
    if a == b: return 1.0
    pa = set(a.split())
    pb = set(b.split())
    if not pa or not pb: return 0.0
    comunes = pa & pb
    return len(comunes) / max(len(pa), len(pb))

# === PARAMETRIZACION ===
PARAM_1001_NOMINA_SUB = {
    "5001": ["06", "07", "08", "09", "10", "15", "27", "30", "33", "36", "39", "42", "45"],
    "5002": ["01", "03", "05"],
    "5024": ["02"],
    "5025": ["03"],
    "5027": ["04"],
    "5023": ["68", "72", "75"],
}

PARAM_1001_RANGOS = [
    ("5005", "5120", "5120", True), ("5005", "5220", "5220", True),
    ("5011", "5230", "5230", True), ("5011", "5130", "5130", True),
    ("5055", "5115", "5115", True), ("5004", "5110", "5110", True),
    ("5016", "5125", "5125", True), ("5016", "5135", "5139", True),
    ("5016", "5140", "5199", True), ("5016", "5210", "5219", True),
    ("5016", "5235", "5249", True), ("5016", "5295", "5299", True),
    ("5055", "5115", "5115", True), ("5006", "5305", "5305", True),
    ("5101", "530515", "530515", True), ("5007", "1435", "1499", True),
    ("5010", "1504", "1699", True), ("5010", "1520", "1540", True),
]

PARAM_1003 = [
    ("1301", "236505", "236509"), ("1302", "236510", "236514"),
    ("1303", "236515", "236519"), ("1304", "236520", "236524"),
    ("1305", "236525", "236529"), ("1306", "236530", "236539"),
    ("1307", "236540", "236549"), ("1308", "236595", "236599"),
    ("1311", "236575", "236579"),
]

PARAM_1007 = [
    ("4001", "4101", "4199"), ("4001", "4135", "4135"),
    ("4002", "4201", "4299"), ("4003", "4210", "4210"),
]

PARAM_1008 = [("1315", "1305", "1305"), ("1316", "1380", "1399"), ("1317", "1330", "1365")]
PARAM_1009 = [("2201", "2205", "2209"), ("2202", "2105", "2199"), ("2207", "2380", "2389"), ("2210", "2335", "2369")]

MAPEO_1012 = [
    ("8302", "1105", "1105"), ("8301", "1110", "1110"),
    ("8305", "1201", "1204"), ("8303", "1205", "1205"),
    ("8304", "1210", "1210"), ("8306", "1225", "1225"),
    ("8309", "1265", "1265"),
]

# === CLASIFICADOR INTELIGENTE POR NOMBRE DE CUENTA ===
KEYWORDS_1001 = [
    ("5001", True, ["sueldo", "salario", "basico", "jornal", "horas extra", "recargo",
                     "auxilio transporte", "auxilio de transporte", "rodamiento"]),
    ("5002", True, ["honorario", "honorarios"]),
    ("5002", True, ["comision", "comisiones"]),
    ("5024", True, ["aporte salud", "aporte eps", "aportes a eps", "aporte a eps",
                     "aporte a salud", "cotizacion salud", "aportes eps"]),
    ("5025", True, ["aporte pension", "aporte a pension", "aportes a pension",
                     "pension obligatoria", "cotizacion pension", "fondo pension", "aportes pension"]),
    ("5027", True, ["arl", "riesgo laboral", "riesgos laborales", "riesgos profesionales",
                     "aporte arl", "aporte riesgo", "aportes arl"]),
    ("5023", True, ["parafiscal", "parafiscales", "icbf", "sena", "caja de compensacion",
                     "compensacion familiar", "comfama", "compensar", "cafam", "colsubsidio", "comfenalco"]),
    ("5001", True, ["vacacion", "vacaciones"]),
    ("5001", True, ["cesantia", "cesantias", "interes sobre cesantia", "intereses cesantia",
                     "intereses sobre cesantias"]),
    ("5001", True, ["prima de servicio", "prima servicio", "prima legal"]),
    ("5001", True, ["dotacion", "suministro a trabajador"]),
    ("5001", True, ["incapacidad", "incapacidades"]),
    ("5001", True, ["bonificacion", "bonificaciones"]),
    ("5011", True, ["seguro", "poliza", "prima de seguro", "todo riesgo", "cumplimiento"]),
    ("5005", True, ["arriendo", "arrendamiento", "arrendamientos", "canon", "alquiler"]),
    ("5004", True, ["acueducto", "alcantarillado", "energia", "electrica", "telefono",
                     "telecomunicacion", "internet", "gas", "servicio publico", "servicios publicos",
                     "vigilancia", "correo", "portes"]),
    ("5004", True, ["transporte", "flete", "acarreo", "taxi", "taxis", "buses", "envio", "mensajeria"]),
    ("5055", True, ["impuesto", "ica", "industria y comercio", "predial", "vehiculo",
                     "timbre", "estampilla", "estampillas"]),
    ("5006", True, ["interes bancario", "intereses bancarios", "interes mora", "gmf", "4x1000", "4 x 1000",
                     "comision bancaria", "comisiones bancarias", "gasto financiero", "gastos financieros",
                     "diferencia en cambio", "gravamen", "rendimiento financiero"]),
    ("5010", True, ["gastos de personal", "personal admn", "bienestar", "medicina prepagada",
                     "auxilio funerario", "auxilio educativo", "capacitacion empleado"]),
    ("5016", True, ["viaje", "viatico", "pasaje", "tiquete", "hospedaje", "hotel"]),
    ("5016", True, ["mantenimiento", "reparacion", "adecuacion", "instalacion electrica"]),
    ("5016", True, ["legal", "notarial", "registro", "licencia"]),
    ("5016", True, ["depreciacion", "amortizacion", "agotamiento", "provision"]),
    ("5016", True, ["aseo y cafeteria", "cafeteria", "papeleria", "utiles", "fotocopia", "parqueadero",
                     "casino", "restaurante", "representacion", "suscripcion", "afiliacion",
                     "publicidad", "propaganda", "seminario", "elemento de aseo", "diversos"]),
    ("5007", True, ["inventario", "compra de", "mercancia", "materia prima", "material", "insumo", "repuesto"]),
]

KEYWORDS_1007 = [
    ("4001", ["ingreso operacional", "consultoria", "asesoria", "soporte tecnico",
              "capacitacion", "outsourcing", "desarrollo software", "servicio",
              "honorario recibido", "ingreso actividad"]),
    ("4001", ["venta", "comercio", "producto", "mercancia"]),
    ("4002", ["ingreso no operacional", "extraordinario", "recuperacion"]),
    ("4003", ["arrendamiento recibido", "arriendo recibido", "canon recibido"]),
]

KEYWORDS_1003 = [
    ("1301", ["retefuente honorario", "retfte honorario", "retencion honorario"]),
    ("1302", ["retefuente comision", "retfte comision", "retencion comision"]),
    ("1303", ["retefuente servicio", "retfte servicio", "retencion servicio"]),
    ("1304", ["retefuente arriendo", "retfte arriendo", "retencion arriendo"]),
    ("1305", ["retefuente rendimiento", "retfte rendimiento", "retencion rendimiento", "retencion financiero"]),
    ("1306", ["retefuente compra", "retfte compra", "retencion compra"]),
    ("1307", ["retencion ica", "rete ica", "reteica"]),
    ("1308", ["otras retencion", "otra retencion", "retencion otro"]),
    ("1311", ["autorretencion", "auto retencion", "autoretefte"]),
]

def normalizar_nombre(nom):
    import unicodedata
    if not nom: return ""
    nom = str(nom).lower().strip()
    nom = ''.join(c for c in unicodedata.normalize('NFD', nom) if unicodedata.category(c) != 'Mn')
    for ch in '.,;:-_/\\()[]{}#"\'&$%@!¿?':
        nom = nom.replace(ch, ' ')
    return ' '.join(nom.split())


def stem_es(palabra):
    if not palabra or len(palabra) < 4: return palabra
    if palabra.endswith('es') and len(palabra) > 5:
        base = palabra[:-2]
        if base.endswith('ion') or base.endswith('dad') or base.endswith('idad'):
            return base
        return base
    if palabra.endswith('s') and not palabra.endswith('ss'):
        return palabra[:-1]
    return palabra


def clasificar_por_nombre(nom, tabla_keywords):
    nom_n = normalizar_nombre(nom)
    if not nom_n: return None
    palabras_nom = set(nom_n.split())
    stems_nom = set(stem_es(p) for p in palabras_nom)
    nom_stemmed = ' '.join(stem_es(p) for p in nom_n.split())

    for item in tabla_keywords:
        if len(item) == 3:
            conc, ded, keywords = item
        else:
            conc, keywords = item
            ded = True
        for kw in keywords:
            if ' ' not in kw: continue
            kw_stemmed = ' '.join(stem_es(p) for p in kw.split())
            if kw_stemmed in nom_stemmed or kw in nom_n:
                return (conc, ded) if len(item) == 3 else conc

    for item in tabla_keywords:
        if len(item) == 3:
            conc, ded, keywords = item
        else:
            conc, keywords = item
            ded = True
        for kw in keywords:
            if ' ' in kw: continue
            kw_stem = stem_es(kw)
            if kw in palabras_nom or kw_stem in stems_nom:
                return (conc, ded) if len(item) == 3 else conc
    return None


def concepto_1001(cta, nom_cta=""):
    if en_rango(cta, "5105", "5105"):
        if nom_cta:
            resultado = clasificar_por_nombre(nom_cta, KEYWORDS_1001)
            if resultado: return resultado
        sc = cta[4:6] if len(cta) >= 6 else cta[4:] if len(cta) > 4 else ""
        for conc, subs in PARAM_1001_NOMINA_SUB.items():
            if sc in subs: return conc, True
        return "5001", True

    if cta[:2] in ("51", "52", "53"):
        if nom_cta:
            resultado = clasificar_por_nombre(nom_cta, KEYWORDS_1001)
            if resultado: return resultado
        for conc, d, h, ded in PARAM_1001_RANGOS:
            if en_rango(cta, d, h): return conc, ded
        return "5016", True

    if cta[:2] == "14":
        for conc, d, h, ded in PARAM_1001_RANGOS:
            if en_rango(cta, d, h): return conc, ded
        if nom_cta:
            resultado = clasificar_por_nombre(nom_cta, KEYWORDS_1001)
            if resultado: return resultado

    return None, True


def buscar_concepto(cta, params, nom_cta="", tabla_keywords=None):
    for c, d, h in params:
        if en_rango(cta, d, h): return c
    if tabla_keywords and nom_cta:
        resultado = clasificar_por_nombre(nom_cta, tabla_keywords)
        if resultado:
            return resultado if isinstance(resultado, str) else resultado[0]
    return ""

# === PROCESAMIENTO PRINCIPAL ===
def procesar_balance(df_balance, df_directorio=None, datos_rues=None):
    """Procesa el balance y retorna un workbook con todos los formatos.
    
    FORMATO DE ENTRADA SIMPLIFICADO (7 columnas):
    Col A: Cuenta | Col B: Nombre | Col C: NIT | Col D: Razón Social | Col E: Débito | Col F: Crédito | Col G: Saldo
    
    El tipo de documento se detecta automáticamente según el NIT.
    """

    # Cargar directorio externo de direcciones
    dir_externo = {}
    if df_directorio is not None:
        for _, row in df_directorio.iterrows():
            nit_d = safe_str(row.iloc[0])
            if not nit_d: continue
            if '.' in nit_d:
                try: nit_d = str(int(float(nit_d)))
                except: pass
            dir_externo[nit_d] = {
                'dir': safe_str(row.iloc[1]) if len(row) > 1 else "",
                'dp': pad_dpto(safe_str(row.iloc[2])) if len(row) > 2 else "",
                'mp': pad_mpio(safe_str(row.iloc[3])) if len(row) > 3 else "",
                'pais': safe_str(row.iloc[4]) if len(row) > 4 else "169",
            }

    if datos_rues:
        for nit_r, info_r in datos_rues.items():
            if nit_r not in dir_externo:
                dir_externo[nit_r] = {
                    'dir': info_r.get('dir', ''),
                    'dp': info_r.get('dp', ''),
                    'mp': info_r.get('mp', ''),
                    'pais': info_r.get('pais', '169'),
                }

    # === LEER BALANCE (formato simplificado de 7 columnas) ===
    bal = []
    for _, row in df_balance.iterrows():
        cta = safe_str(row.iloc[0])       # Col A: Cuenta
        nit = safe_str(row.iloc[2])       # Col C: NIT
        if not cta or not nit:
            continue
        # Limpiar NIT
        if '.' in nit:
            try: nit = str(int(float(nit)))
            except: pass
        bal.append({
            'cta': cta,
            'nom_cta': safe_str(row.iloc[1]),                          # Col B: Nombre cuenta
            'td': detectar_tipo_doc(nit),                              # Auto-detectado
            'nit': nit,
            'razon': safe_str(row.iloc[3]) if len(row) > 3 else "",   # Col D: Razón Social
            'deb': safe_num(row.iloc[4]) if len(row) > 4 else 0,      # Col E: Débito
            'cred': safe_num(row.iloc[5]) if len(row) > 5 else 0,     # Col F: Crédito
            'saldo': safe_num(row.iloc[6]) if len(row) > 6 else 0,    # Col G: Saldo
        })

    # Directorio
    direc = {}
    for f in bal:
        if f['nit'] not in direc:
            td = f['td']
            r = f['razon']
            d = {'td': td, 'dv': calc_dv(f['nit']),
                 'a1': '', 'a2': '', 'n1': '', 'n2': '',
                 'rs': '', 'dir': '', 'dp': '', 'mp': '', 'pais': '169'}
            if td == "13":
                p = r.split()
                if len(p) >= 1: d['a1'] = p[0]
                if len(p) >= 2: d['a2'] = p[1]
                if len(p) >= 3: d['n1'] = p[2]
                if len(p) >= 4: d['n2'] = ' '.join(p[3:])
            else:
                d['rs'] = r
            if f['nit'] in dir_externo:
                ext = dir_externo[f['nit']]
                if ext['dir']: d['dir'] = ext['dir']
                if ext['dp']: d['dp'] = pad_dpto(ext['dp'])
                if ext['mp']: d['mp'] = pad_mpio(ext['mp'])
                if ext.get('pais'): d['pais'] = ext['pais']
            direc[f['nit']] = d
    direc[NM] = {'td': TDM, 'dv': '', 'a1': '', 'a2': '', 'n1': '', 'n2': '',
                 'rs': 'CUANTIAS MENORES', 'dir': '', 'dp': '', 'mp': '', 'pais': '169'}

    def t(nit):
        return direc.get(nit, {'td': detectar_tipo_doc(nit), 'dv': calc_dv(nit),
                                'a1': '', 'a2': '', 'n1': '', 'n2': '',
                                'rs': nit, 'dir': '', 'dp': '', 'mp': '', 'pais': '169'})

    # === CREAR WORKBOOK ===
    wb = openpyxl.Workbook()
    hf = PatternFill('solid', fgColor='1F4E79')
    hfont = Font(bold=True, color='FFFFFF', size=10, name='Arial')
    thin = Side(style='thin', color='808080')

    def nueva_hoja(nombre, headers):
        ws = wb.create_sheet(nombre)
        for c, h in enumerate(headers, 1):
            cell = ws.cell(1, c, h)
            cell.font = hfont
            cell.fill = hf
            cell.alignment = Alignment(horizontal='center', wrap_text=True)
            cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
        return ws

    def escribir_tercero(ws, fila, col, nit, con_pais=False):
        d = t(nit)
        c = col
        valores = [d['td'], nit, d['dv'], d['a1'], d['a2'], d['n1'], d['n2'], d['rs'], d['dir'], d['dp'], d['mp']]
        for v in valores:
            cell = ws.cell(fila, c)
            cell.value = v
            cell.number_format = '@'
            c += 1
        if con_pais:
            cell = ws.cell(fila, c)
            cell.value = d.get('pais', '169') or "169"
            cell.number_format = '@'
            c += 1
        return c

    def fmt(ws, fila, cols):
        for c in cols:
            ws.cell(fila, c).number_format = '#,##0'

    def zebra(ws, fila):
        for c in range(1, ws.max_column + 1):
            ws.cell(fila, c).font = Font(size=10, name='Arial')
            ws.cell(fila, c).border = Border(top=thin, bottom=thin, left=thin, right=thin)
        if (fila - 2) % 2 == 0:
            for c in range(1, ws.max_column + 1):
                ws.cell(fila, c).fill = PatternFill('solid', fgColor='F2F7FB')

    resultados = {}

    # ========== PRE-CALCULAR RETENCIONES Y BASES POR NIT ==========
    ret_fte_por_nit = defaultdict(float)
    ret_iva_por_nit = defaultdict(float)
    gastos_por_nit = defaultdict(float)

    for f in bal:
        cta = f['cta']
        if en_rango(cta, "236505", "236530"):
            ret_fte_por_nit[f['nit']] += f['cred']
        elif en_rango(cta, "2367", "2367"):
            ret_iva_por_nit[f['nit']] += f['cred']
        if cta[:2] in ("51", "52", "53") and f['deb'] > 0:
            gastos_por_nit[f['nit']] += f['deb']

    # ========== F1001 ==========
    h = ["Concepto", "Tipo Doc", "No ID", "DV", "Apellido1", "Apellido2", "Nombre1", "Nombre2",
         "Razon Social", "Direccion", "Dpto", "Mpio", "Pais", "Pago Deducible", "Pago No Deducible",
         "IVA Ded", "IVA No Ded", "Ret Fte Renta", "Ret Fte Asumida", "Ret IVA R.Comun", "Ret IVA No Dom"]
    ws = nueva_hoja("F1001 Pagos", h)

    dic = defaultdict(lambda: [0.0] * 5)
    nits_en_1001 = set()
    for f in bal:
        conc, ded = concepto_1001(f['cta'], f.get('nom_cta', ''))
        if not conc or conc == "5001": continue
        k = (conc, f['nit'])
        if ded: dic[k][0] += f['deb']
        else: dic[k][1] += f['deb']
        nits_en_1001.add(f['nit'])

    nit_conceptos = defaultdict(list)
    for (conc, nit), v in dic.items():
        nit_conceptos[nit].append((conc, v[0] + v[1]))

    for nit in nit_conceptos:
        ret_total = ret_fte_por_nit.get(nit, 0)
        ret_iva = ret_iva_por_nit.get(nit, 0)
        if ret_total == 0 and ret_iva == 0: continue
        total_pagado = sum(v for _, v in nit_conceptos[nit])
        if total_pagado == 0: continue
        for conc, pago in nit_conceptos[nit]:
            proporcion = pago / total_pagado if total_pagado > 0 else 0
            dic[(conc, nit)][2] += ret_total * proporcion
            dic[(conc, nit)][4] += ret_iva * proporcion

    final = {}
    menores = defaultdict(lambda: [0.0] * 5)
    for (c, n), v in dic.items():
        tiene_retencion = v[2] > 0 or v[4] > 0
        if v[0] + v[1] < C3UVT and not tiene_retencion:
            for i in range(5): menores[(c, NM)][i] += v[i]
        else:
            final[(c, n)] = v
    for k, v in menores.items():
        if k not in final: final[k] = v

    fila = 2
    for (conc, nit), v in sorted(final.items()):
        ws.cell(fila, 1).value = conc
        escribir_tercero(ws, fila, 2, nit, True)
        ws.cell(fila, 14).value = int(v[0])
        ws.cell(fila, 15).value = int(v[1])
        ws.cell(fila, 16).value = 0
        ws.cell(fila, 17).value = 0
        ws.cell(fila, 18).value = int(v[2])
        ws.cell(fila, 19).value = 0
        ws.cell(fila, 20).value = int(v[4])
        ws.cell(fila, 21).value = 0
        fmt(ws, fila, range(14, 22))
        zebra(ws, fila)
        fila += 1
    resultados['F1001 Pagos'] = len(final)

    # ========== F1003 ==========
    h = ["Concepto", "Tipo Doc", "No ID", "DV", "Apellido1", "Apellido2", "Nombre1", "Nombre2",
         "Razon Social", "Direccion", "Dpto", "Mpio", "Base Retencion", "Retencion Acumulada"]
    ws = nueva_hoja("F1003 Retenciones", h)

    dic3 = defaultdict(lambda: [0.0, 0.0])
    for f in bal:
        conc = buscar_concepto(f['cta'], PARAM_1003, f.get('nom_cta', ''), KEYWORDS_1003)
        if not conc: continue
        dic3[(conc, f['nit'])][1] += f['cred']

    # Usar gastos del NIT como base gravable
    for (conc, nit), v in dic3.items():
        if v[0] == 0 and v[1] > 0:
            v[0] = gastos_por_nit.get(nit, 0)

    fila = 2
    for (conc, nit), v in sorted(dic3.items()):
        ws.cell(fila, 1).value = conc
        escribir_tercero(ws, fila, 2, nit)
        ws.cell(fila, 13).value = int(v[0])
        ws.cell(fila, 14).value = int(v[1])
        fmt(ws, fila, [13, 14])
        zebra(ws, fila)
        fila += 1
    resultados['F1003 Retenciones'] = len(dic3)

    # ========== F1005 ==========
    h = ["Tipo Doc", "No ID", "DV", "Apellido1", "Apellido2", "Nombre1", "Nombre2",
         "Razon Social", "Direccion", "Dpto", "Mpio", "IVA Descontable", "IVA Devol Ventas"]
    ws = nueva_hoja("F1005 IVA Descontable", h)

    dic5 = defaultdict(float)
    for f in bal:
        if en_rango(f['cta'], "2408", "2408") and f['deb'] > 0:
            dic5[f['nit']] += f['deb']

    fila = 2
    for nit, val in sorted(dic5.items()):
        escribir_tercero(ws, fila, 1, nit)
        ws.cell(fila, 12).value = int(val)
        ws.cell(fila, 13).value = 0
        fmt(ws, fila, [12, 13])
        zebra(ws, fila)
        fila += 1
    resultados['F1005 IVA Descontable'] = len(dic5)

    # ========== F1006 ==========
    h = ["Tipo Doc", "No ID", "DV", "Apellido1", "Apellido2", "Nombre1", "Nombre2",
         "Razon Social", "Direccion", "Dpto", "Mpio", "IVA Generado", "IVA Devol Compras", "Imp Consumo"]
    ws = nueva_hoja("F1006 IVA Generado", h)

    dic6 = defaultdict(float)
    for f in bal:
        if en_rango(f['cta'], "2408", "2408") and f['cred'] > 0:
            dic6[f['nit']] += f['cred']

    fila = 2
    for nit, val in sorted(dic6.items()):
        escribir_tercero(ws, fila, 1, nit)
        ws.cell(fila, 12).value = int(val)
        ws.cell(fila, 13).value = 0
        ws.cell(fila, 14).value = 0
        fmt(ws, fila, [12, 13, 14])
        zebra(ws, fila)
        fila += 1
    resultados['F1006 IVA Generado'] = len(dic6)

    # ========== F1007 ==========
    h = ["Concepto", "Tipo Doc", "No ID", "DV", "Apellido1", "Apellido2", "Nombre1", "Nombre2",
         "Razon Social", "Direccion", "Dpto", "Mpio", "Pais", "Ingresos Brutos", "Devoluciones"]
    ws = nueva_hoja("F1007 Ingresos", h)

    dic7 = defaultdict(float)
    for f in bal:
        conc = buscar_concepto(f['cta'], PARAM_1007, f.get('nom_cta', ''), KEYWORDS_1007)
        if not conc: continue
        dic7[(conc, f['nit'])] += f['cred']

    final7 = {}
    men7 = defaultdict(float)
    for (c, n), v in dic7.items():
        if v < C3UVT: men7[(c, NM)] += v
        else: final7[(c, n)] = v
    for k, v in men7.items():
        if k not in final7: final7[k] = v

    fila = 2
    for (conc, nit), val in sorted(final7.items()):
        ws.cell(fila, 1).value = conc
        escribir_tercero(ws, fila, 2, nit, True)
        ws.cell(fila, 14).value = int(val)
        ws.cell(fila, 15).value = 0
        fmt(ws, fila, [14, 15])
        zebra(ws, fila)
        fila += 1
    resultados['F1007 Ingresos'] = len(final7)

    # ========== F1008 ==========
    h = ["Concepto", "Tipo Doc", "No ID", "DV", "Apellido1", "Apellido2", "Nombre1", "Nombre2",
         "Razon Social", "Direccion", "Dpto", "Mpio", "Saldo CxC Dic31"]
    ws = nueva_hoja("F1008 CxC", h)

    dic8 = defaultdict(float)
    for f in bal:
        conc = buscar_concepto(f['cta'], PARAM_1008, f.get('nom_cta', ''))
        if not conc: continue
        s = abs(f['saldo'])
        if s == 0: continue
        dic8[(conc, f['nit'])] += s

    final8 = {}
    men8 = defaultdict(float)
    for (c, n), v in dic8.items():
        if v < C12UVT: men8[(c, NM)] += v
        else: final8[(c, n)] = v
    for k, v in men8.items():
        if k not in final8: final8[k] = v

    fila = 2
    for (conc, nit), val in sorted(final8.items()):
        ws.cell(fila, 1).value = conc
        escribir_tercero(ws, fila, 2, nit)
        ws.cell(fila, 13).value = int(val)
        fmt(ws, fila, [13])
        zebra(ws, fila)
        fila += 1
    resultados['F1008 CxC'] = len(final8)

    # ========== F1009 ==========
    h = ["Concepto", "Tipo Doc", "No ID", "DV", "Apellido1", "Apellido2", "Nombre1", "Nombre2",
         "Razon Social", "Direccion", "Dpto", "Mpio", "Saldo CxP Dic31"]
    ws = nueva_hoja("F1009 CxP", h)

    dic9 = defaultdict(float)
    for f in bal:
        conc = buscar_concepto(f['cta'], PARAM_1009, f.get('nom_cta', ''))
        if not conc: continue
        s = abs(f['saldo'])
        if s == 0: continue
        dic9[(conc, f['nit'])] += s

    final9 = {}
    men9 = defaultdict(float)
    for (c, n), v in dic9.items():
        if v < C12UVT: men9[(c, NM)] += v
        else: final9[(c, n)] = v
    for k, v in men9.items():
        if k not in final9: final9[k] = v

    fila = 2
    for (conc, nit), val in sorted(final9.items()):
        ws.cell(fila, 1).value = conc
        escribir_tercero(ws, fila, 2, nit)
        ws.cell(fila, 13).value = int(val)
        fmt(ws, fila, [13])
        zebra(ws, fila)
        fila += 1
    resultados['F1009 CxP'] = len(final9)

    # ========== F1010 ==========
    h = ["Tipo Doc", "No ID", "DV", "Apellido1", "Apellido2", "Nombre1", "Nombre2",
         "Razon Social", "Direccion", "Dpto", "Mpio", "Pais", "Valor Patrimonial", "% Participacion", "Valor Porcentual"]
    ws = nueva_hoja("F1010 Socios", h)

    dic10 = defaultdict(float)
    for f in bal:
        if en_rango(f['cta'], "3105", "3115") or en_rango(f['cta'], "3110", "3110"):
            dic10[f['nit']] += abs(f['saldo'])

    capital_total = sum(dic10.values())
    fila = 2
    for nit, val in sorted(dic10.items()):
        escribir_tercero(ws, fila, 1, nit, True)
        ws.cell(fila, 13).value = int(val)
        pct = round(val / capital_total * 100, 2) if capital_total > 0 else 0
        ws.cell(fila, 14).value = pct / 100
        ws.cell(fila, 14).number_format = '0.00%'
        ws.cell(fila, 15).value = int(val)
        fmt(ws, fila, [13, 15])
        zebra(ws, fila)
        fila += 1
    resultados['F1010 Socios'] = len(dic10)

    # ========== F1012 ==========
    h = ["Concepto", "Tipo Doc", "No ID", "DV", "Apellido1", "Apellido2", "Nombre1", "Nombre2",
         "Razon Social", "Saldo Dic31", "Valor Patrimonial"]
    ws = nueva_hoja("F1012 Inversiones", h)

    dic12 = defaultdict(float)
    for f in bal:
        for conc, d, h2 in MAPEO_1012:
            if en_rango(f['cta'], d, h2):
                dic12[(conc, f['nit'])] += abs(f['saldo'])
                break

    fila = 2
    for (conc, nit), val in sorted(dic12.items()):
        ws.cell(fila, 1).value = conc
        escribir_tercero(ws, fila, 2, nit)
        ws.cell(fila, 10).value = int(val)
        ws.cell(fila, 11).value = int(val)
        fmt(ws, fila, [10, 11])
        zebra(ws, fila)
        fila += 1
    resultados['F1012 Inversiones'] = len(dic12)

    # ========== F2276 ==========
    h = ["Tipo Doc", "No ID", "DV", "Apellido1", "Apellido2", "Nombre1", "Nombre2",
         "Direccion", "Dpto", "Mpio", "Pais", "Salarios", "Emol Ecles", "Honor 383",
         "Serv 383", "Comis 383", "Pensiones", "Vacaciones", "Cesantias e Int",
         "Incapacidades", "Otros Pag Lab", "Total Bruto", "Aporte Salud", "Aporte Pension",
         "Sol Pensional", "Vol Empleador", "Vol Trabajador", "AFC", "Ret Fte", "Total Pagos"]
    ws = nueva_hoja("F2276 Rentas Trabajo", h)

    dic26 = defaultdict(lambda: [0.0] * 19)
    for f in bal:
        if not en_rango(f['cta'], "5105", "5105") or f['deb'] == 0: continue
        nit = f['nit']
        nom = normalizar_nombre(f.get('nom_cta', ''))
        sc = f['cta'][4:6] if len(f['cta']) >= 6 else ""
        clasificado = False

        if sc in ("06", "07", "08", "09", "10", "15"):
            dic26[nit][0] += f['deb']; clasificado = True
        elif sc in ("27",):
            dic26[nit][10] += f['deb']; clasificado = True
        elif sc in ("30", "33"):
            dic26[nit][8] += f['deb']; clasificado = True
        elif sc in ("36",):
            dic26[nit][10] += f['deb']; clasificado = True
        elif sc in ("39",):
            dic26[nit][7] += f['deb']; clasificado = True
        elif sc in ("42", "45"):
            dic26[nit][10] += f['deb']; clasificado = True
        elif sc in ("01", "03", "05"):
            d2 = t(nit)
            if d2['td'] == "13":
                dic26[nit][3] += f['deb']; clasificado = True
        elif sc in ("02",):
            dic26[nit][12] += f['deb']; clasificado = True
        elif sc in ("04",):
            dic26[nit][13] += f['deb']; clasificado = True
        elif sc in ("68", "72", "75"):
            clasificado = True

        if not clasificado and nom:
            palabras = set(nom.split())
            if any(kw in palabras for kw in ["sueldo", "salario", "basico", "jornal"]) or \
               any(kw in nom for kw in ["hora extra", "horas extra", "recargo"]):
                dic26[nit][0] += f['deb']
            elif any(kw in nom for kw in ["cesantia", "interes sobre cesantia", "intereses cesantia"]):
                dic26[nit][8] += f['deb']
            elif any(kw in palabras for kw in ["vacacion", "vacaciones"]):
                dic26[nit][7] += f['deb']
            elif any(kw in nom for kw in ["prima de servicio", "prima servicio"]):
                dic26[nit][10] += f['deb']
            elif any(kw in palabras for kw in ["incapacidad", "incapacidades"]):
                dic26[nit][9] += f['deb']
            elif any(kw in nom for kw in ["aporte salud", "aporte eps", "aportes eps", "aportes a eps"]):
                dic26[nit][12] += f['deb']
            elif any(kw in nom for kw in ["aporte pension", "aportes pension", "aportes a pension"]):
                dic26[nit][13] += f['deb']
            elif any(kw in palabras for kw in ["dotacion", "bonificacion", "auxilio"]):
                dic26[nit][10] += f['deb']
            elif any(kw in palabras for kw in ["honorario", "honorarios"]):
                d2 = t(nit)
                if d2['td'] == "13": dic26[nit][3] += f['deb']
                else: dic26[nit][10] += f['deb']
            elif any(kw in palabras for kw in ["parafiscal", "parafiscales", "icbf", "sena",
                                                "compensar", "comfama", "cafam"]):
                pass
            else:
                dic26[nit][10] += f['deb']

    for f in bal:
        if en_rango(f['cta'], "2365", "2365") and f['nit'] in dic26:
            dic26[f['nit']][17] += f['cred']

    for nit in dic26:
        dic26[nit][11] = sum(dic26[nit][:11])
        dic26[nit][18] = dic26[nit][11]

    fila = 2
    for nit, v in sorted(dic26.items()):
        d = t(nit)
        for ci, val in [(1, d['td']), (2, nit), (3, d['dv']),
                        (4, d['a1']), (5, d['a2']), (6, d['n1']), (7, d['n2']),
                        (8, d['dir']), (9, d['dp']), (10, d['mp']),
                        (11, d.get('pais', '169') or '169')]:
            cell = ws.cell(fila, ci)
            cell.value = val
            cell.number_format = '@'
        for i in range(19):
            ws.cell(fila, 12 + i).value = int(v[i])
            ws.cell(fila, 12 + i).number_format = '#,##0'
        zebra(ws, fila)
        fila += 1
    resultados['F2276 Rentas Trabajo'] = len(dic26)

    # ========== VALIDACION TERCEROS (vs INTERNET) ==========
    validaciones = []
    if datos_rues:
        warn_fill = PatternFill('solid', fgColor='FFF3CD')
        err_fill = PatternFill('solid', fgColor='F8D7DA')
        ok_fill = PatternFill('solid', fgColor='D4EDDA')

        h_val = ["NIT", "Campo", "Valor en Balance", "Valor en Internet", "Estado", "Observación"]
        ws_val = nueva_hoja("Validacion Terceros", h_val)

        fila_val = 2
        for nit_v, info_rues in sorted(datos_rues.items()):
            if nit_v not in direc or nit_v == NM: continue
            d_bal = direc[nit_v]

            dv_calculado = calc_dv(nit_v)
            dv_rues = str(info_rues.get('dv', '')).strip()
            if dv_rues and dv_calculado:
                if dv_calculado == dv_rues:
                    estado_dv = "✅ OK"; fill_dv = ok_fill
                    obs_dv = "DV coincide con internet y cálculo"
                else:
                    estado_dv = "❌ ERROR"; fill_dv = err_fill
                    obs_dv = f"DV calculado={dv_calculado}, Internet={dv_rues}. REVISAR"
                    validaciones.append(('dv_error', nit_v))

                ws_val.cell(fila_val, 1).value = nit_v
                ws_val.cell(fila_val, 1).number_format = '@'
                ws_val.cell(fila_val, 2).value = "Dígito Verificación"
                ws_val.cell(fila_val, 3).value = dv_calculado
                ws_val.cell(fila_val, 4).value = dv_rues
                ws_val.cell(fila_val, 5).value = estado_dv
                ws_val.cell(fila_val, 6).value = obs_dv
                for c in range(1, 7):
                    ws_val.cell(fila_val, c).fill = fill_dv
                    ws_val.cell(fila_val, c).font = Font(size=10, name='Arial')
                    ws_val.cell(fila_val, c).border = Border(top=thin, bottom=thin, left=thin, right=thin)
                fila_val += 1

            rs_balance = d_bal.get('rs', '').strip()
            if d_bal.get('td') == '13':
                partes = [d_bal.get('a1',''), d_bal.get('a2',''), d_bal.get('n1',''), d_bal.get('n2','')]
                rs_balance = ' '.join(p for p in partes if p).strip()
            rs_rues = info_rues.get('razon_social', '').strip()

            if rs_rues and rs_balance:
                sim = similitud_textos(rs_balance, rs_rues)
                rs_norm_bal = normalizar_texto(rs_balance)
                rs_norm_rues = normalizar_texto(rs_rues)

                if rs_norm_bal == rs_norm_rues:
                    estado_rs = "✅ OK"; fill_rs = ok_fill
                    obs_rs = "Razón social coincide exactamente"
                elif sim >= 0.7:
                    estado_rs = "⚠️ SIMILAR"; fill_rs = warn_fill
                    obs_rs = f"Similitud {sim:.0%}. Verificar ortografía"
                    validaciones.append(('rs_warn', nit_v))
                else:
                    estado_rs = "❌ DIFERENTE"; fill_rs = err_fill
                    obs_rs = f"Similitud {sim:.0%}. Razón social NO coincide con fuente pública"
                    validaciones.append(('rs_error', nit_v))

                ws_val.cell(fila_val, 1).value = nit_v
                ws_val.cell(fila_val, 1).number_format = '@'
                ws_val.cell(fila_val, 2).value = "Razón Social"
                ws_val.cell(fila_val, 3).value = rs_balance
                ws_val.cell(fila_val, 4).value = rs_rues
                ws_val.cell(fila_val, 5).value = estado_rs
                ws_val.cell(fila_val, 6).value = obs_rs
                for c in range(1, 7):
                    ws_val.cell(fila_val, c).fill = fill_rs
                    ws_val.cell(fila_val, c).font = Font(size=10, name='Arial')
                    ws_val.cell(fila_val, c).border = Border(top=thin, bottom=thin, left=thin, right=thin)
                fila_val += 1

        anchos_val = [18, 22, 40, 40, 16, 50]
        for i, ancho in enumerate(anchos_val, 1):
            ws_val.column_dimensions[openpyxl.utils.get_column_letter(i)].width = ancho
        ws_val.freeze_panes = 'A2'

    # ========== RESUMEN ==========
    n_con_dir = sum(1 for d in direc.values() if d.get('dir', ''))

    wsr = wb.active
    wsr.title = "Resumen"
    wsr['A1'] = "RESUMEN PROCESAMIENTO EXOGENA AG 2025"
    wsr['A1'].font = Font(bold=True, size=14, name='Arial', color='1F4E79')
    wsr['A3'] = "Fecha:"
    wsr['B3'] = datetime.now().strftime("%d/%m/%Y %H:%M")
    wsr['A4'] = "Filas del balance:"
    wsr['B4'] = len(bal)
    wsr['A5'] = "Terceros:"
    wsr['B5'] = len(direc)
    wsr['A6'] = "Con dirección:"
    wsr['B6'] = n_con_dir

    if datos_rues:
        n_dv_err = sum(1 for tipo, _ in validaciones if tipo == 'dv_error')
        n_rs_err = sum(1 for tipo, _ in validaciones if tipo == 'rs_error')
        n_rs_warn = sum(1 for tipo, _ in validaciones if tipo == 'rs_warn')
        wsr['A7'] = "Validados vs Internet:"
        wsr['B7'] = len(datos_rues)
        wsr['A8'] = "  ❌ DV con error:"
        wsr['B8'] = n_dv_err
        if n_dv_err > 0: wsr['B8'].font = Font(bold=True, color='CC0000')
        wsr['A9'] = "  ❌ Razón social diferente:"
        wsr['B9'] = n_rs_err
        if n_rs_err > 0: wsr['B9'].font = Font(bold=True, color='CC0000')
        wsr['A10'] = "  ⚠️ Razón social similar:"
        wsr['B10'] = n_rs_warn
        fila_inicio_formatos = 12
    else:
        fila_inicio_formatos = 8

    wsr.cell(fila_inicio_formatos, 1).value = "Formato"
    wsr.cell(fila_inicio_formatos, 2).value = "Registros"
    wsr.cell(fila_inicio_formatos, 1).font = Font(bold=True)
    wsr.cell(fila_inicio_formatos, 2).font = Font(bold=True)
    row = fila_inicio_formatos + 1
    for nombre, n in resultados.items():
        wsr.cell(row, 1).value = nombre
        wsr.cell(row, 2).value = n
        row += 1
    wsr.cell(row + 1, 1).value = "TOTAL"
    wsr.cell(row + 1, 1).font = Font(bold=True)
    wsr.cell(row + 1, 2).value = sum(resultados.values())
    wsr.cell(row + 1, 2).font = Font(bold=True)
    wsr.cell(row + 3, 1).value = "F1004, F1011, F1647: requieren datos manuales"
    wsr.column_dimensions['A'].width = 30
    wsr.column_dimensions['B'].width = 15

    for ws_name in wb.sheetnames:
        ws2 = wb[ws_name]
        if ws_name.startswith("F"):
            for col in range(1, ws2.max_column + 1):
                ws2.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 16
            ws2.freeze_panes = 'A2'

    return wb, resultados, len(bal), len(direc), n_con_dir, validaciones


# === INTERFAZ ===
st.markdown('<p class="main-header">📊 Exógena DIAN — AG 2025</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Genera automáticamente los formatos de información exógena a partir del balance de prueba por tercero</p>', unsafe_allow_html=True)

st.divider()

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 📁 Sube el Balance de Prueba por Tercero")
    st.markdown("""
    El archivo Excel debe tener esta estructura desde la **fila de datos** (puede tener encabezados arriba):

    | Col A | Col B | Col C | Col D | Col E | Col F | Col G |
    |-------|-------|-------|-------|-------|-------|-------|
    | Cuenta | Nombre Cuenta | NIT | Razón Social | Débito | Crédito | Saldo |

    💡 *El tipo de documento (NIT/Cédula) se detecta automáticamente según el número de identificación.*
    """)

    uploaded_file = st.file_uploader("Selecciona el archivo Excel", type=['xlsx', 'xls', 'csv'])

with col2:
    st.markdown("### ⚙️ Configuración")
    fila_encabezado = st.number_input("Fila del encabezado", min_value=1, max_value=20, value=3,
                                       help="Fila donde están los títulos de columna (ej: 1, 3)")
    nombre_hoja = st.text_input("Nombre de la hoja (dejar vacío = primera hoja)", value="",
                                 help="Si tu archivo tiene varias hojas, escribe el nombre de la del balance")

st.divider()

# === DIRECTORIO DE TERCEROS (DIRECCIONES) ===
st.markdown("### 📋 Directorio de Terceros (opcional)")
st.markdown("""
Sube un archivo con las **direcciones** de tus terceros para que aparezcan en los formatos.
Si no lo subes, el programa puede **buscar las direcciones automáticamente** en internet.
""")

col_dir1, col_dir2 = st.columns([2, 1])

with col_dir1:
    st.markdown("""
    | Col A | Col B | Col C | Col D | Col E |
    |-------|-------|-------|-------|-------|
    | NIT | Dirección | Cod Depto | Cod Municipio | Cod País |

    Ejemplo: `890904997 | CL 30 65-15 | 05 | 001 | 169`

    *Los códigos deben ser formato DIAN (ej: Antioquia = 05, Medellín = 001, Colombia = 169)*
    """)
    uploaded_dir = st.file_uploader("Selecciona el archivo de directorio", type=['xlsx', 'xls', 'csv'],
                                     key="directorio")

with col_dir2:
    st.markdown("#### 📥 Plantilla")
    st.markdown("Descarga la plantilla y llénala con los datos de tus terceros:")

    from io import BytesIO as _BytesIO
    wb_plantilla = openpyxl.Workbook()
    ws_p = wb_plantilla.active
    ws_p.title = "Directorio"
    headers_p = ["NIT", "Direccion", "Cod Departamento", "Cod Municipio", "Cod Pais"]
    hf_p = PatternFill('solid', fgColor='1F4E79')
    hfont_p = Font(bold=True, color='FFFFFF', size=10, name='Arial')
    for c, h in enumerate(headers_p, 1):
        cell = ws_p.cell(1, c, h)
        cell.font = hfont_p
        cell.fill = hf_p
        cell.alignment = Alignment(horizontal='center')
    ejemplos = [
        ("890904997", "CL 30 65-15", "05", "001", "169"),
        ("800123456", "KR 7 32-16 OF 801", "11", "001", "169"),
        ("900555111", "AV 6 NORTE 23-45", "76", "001", "169"),
    ]
    for r, ej in enumerate(ejemplos, 2):
        for c, v in enumerate(ej, 1):
            cell = ws_p.cell(r, c)
            cell.value = v
            cell.number_format = '@'

    ws_cod = wb_plantilla.create_sheet("Codigos DIAN")
    ws_cod['A1'] = "DEPARTAMENTOS DIAN"
    ws_cod['A1'].font = Font(bold=True, size=11)
    ws_cod['D1'] = "PAISES"
    ws_cod['D1'].font = Font(bold=True, size=11)
    dptos = [
        ("05","Antioquia"),("08","Atlántico"),("11","Bogotá DC"),("13","Bolívar"),
        ("15","Boyacá"),("17","Caldas"),("18","Caquetá"),("19","Cauca"),("20","Cesar"),
        ("23","Córdoba"),("25","Cundinamarca"),("27","Chocó"),("41","Huila"),
        ("44","La Guajira"),("47","Magdalena"),("50","Meta"),("52","Nariño"),
        ("54","Norte Santander"),("63","Quindío"),("66","Risaralda"),("68","Santander"),
        ("70","Sucre"),("73","Tolima"),("76","Valle del Cauca"),("81","Arauca"),
        ("85","Casanare"),("86","Putumayo"),("88","San Andrés"),("91","Amazonas"),
        ("94","Guainía"),("95","Guaviare"),("97","Vaupés"),("99","Vichada"),
    ]
    ws_cod['A2'] = "Código"; ws_cod['B2'] = "Departamento"
    ws_cod['A2'].font = Font(bold=True); ws_cod['B2'].font = Font(bold=True)
    for i, (cod, nom) in enumerate(dptos, 3):
        ws_cod.cell(i, 1).value = cod
        ws_cod.cell(i, 1).number_format = '@'
        ws_cod.cell(i, 2).value = nom
    ws_cod['D2'] = "Código"; ws_cod['E2'] = "País"
    ws_cod['D2'].font = Font(bold=True); ws_cod['E2'].font = Font(bold=True)
    paises_ej = [("169","Colombia"),("249","Estados Unidos"),("200","México"),
                 ("210","Panamá"),("234","España"),("240","Venezuela")]
    for i, (cod, nom) in enumerate(paises_ej, 3):
        ws_cod.cell(i, 4).value = cod
        ws_cod.cell(i, 5).value = nom

    for col in range(1, 6):
        ws_p.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 22
        ws_cod.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 20

    buf_p = _BytesIO()
    wb_plantilla.save(buf_p)
    buf_p.seek(0)
    st.download_button("📥 Descargar plantilla directorio",
                       data=buf_p.getvalue(),
                       file_name="plantilla_directorio_terceros.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.divider()

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, header=fila_encabezado - 1)
        else:
            sheet = nombre_hoja if nombre_hoja.strip() else 0
            df = pd.read_excel(uploaded_file, header=fila_encabezado - 1, sheet_name=sheet)

        st.success(f"✅ Archivo cargado: **{len(df)} filas** x {len(df.columns)} columnas")

        with st.expander("👁 Vista previa del balance", expanded=False):
            st.dataframe(df.head(20), use_container_width=True)

        df_dir = None
        if uploaded_dir:
            try:
                if uploaded_dir.name.endswith('.csv'):
                    df_dir = pd.read_csv(uploaded_dir, dtype=str)
                else:
                    df_dir = pd.read_excel(uploaded_dir, dtype=str)
                st.success(f"✅ Directorio cargado: **{len(df_dir)} terceros** con direcciones")
            except Exception as e:
                st.warning(f"⚠️ No se pudo leer el directorio: {str(e)}. Se procesará sin direcciones.")

        st.divider()

        col_btn1, col_btn2 = st.columns(2)
        btn_normal = col_btn1.button("🚀 PROCESAR EXÓGENA", type="primary", use_container_width=True)
        btn_internet = col_btn2.button("🌐 PROCESAR + BUSCAR INTERNET", use_container_width=True,
                                        help="Busca direcciones y razón social en RUES, Datos Abiertos y web")

        if btn_normal or btn_internet:
            datos_rues = None
            df_dir_auto = None
            if btn_internet:
                import requests as _req

                st.markdown("---")
                st.markdown("### 🌐 Búsqueda de terceros en internet")

                st.write("**Probando conexión a internet...**")
                _test_urls = [
                    ("Google", "https://www.google.com", 5),
                    ("datos.gov.co", "https://www.datos.gov.co", 5),
                    ("RUES", "https://www.rues.org.co", 5),
                    ("DuckDuckGo", "https://html.duckduckgo.com", 5),
                    ("Bing", "https://www.bing.com", 5),
                ]
                _test_results = []
                for nombre, url, timeout in _test_urls:
                    try:
                        r = _req.get(url, timeout=timeout, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
                        _test_results.append(f"✅ {nombre}: HTTP {r.status_code}")
                    except _req.exceptions.Timeout:
                        _test_results.append(f"⏱️ {nombre}: Timeout ({timeout}s)")
                    except _req.exceptions.ConnectionError as e:
                        _test_results.append(f"❌ {nombre}: Conexión fallida — {str(e)[:60]}")
                    except Exception as e:
                        _test_results.append(f"❌ {nombre}: {type(e).__name__}: {str(e)[:60]}")

                for tr in _test_results:
                    st.write(tr)

                hay_internet = any("✅" in tr for tr in _test_results)

                if not hay_internet:
                    st.error("⛔ **No hay acceso a internet desde esta aplicación.** "
                             "Streamlit Cloud puede estar bloqueando las conexiones salientes. "
                             "Usa la plantilla de directorio para agregar direcciones manualmente.")
                else:
                    st.write("---")
                    nits_unicos = set()
                    for _, row in df.iterrows():
                        nit_val = safe_str(row.iloc[2])  # Col C: NIT (nuevo índice)
                        if nit_val and nit_val != NM:
                            if '.' in nit_val:
                                try: nit_val = str(int(float(nit_val)))
                                except: pass
                            nits_unicos.add(nit_val)

                    nits_list = sorted(list(nits_unicos))
                    st.write(f"**{len(nits_list)}** NITs únicos para consultar")

                    progress_bar = st.progress(0, text="🔍 Buscando...")
                    _log_msgs = []
                    def _log_fn(msg): _log_msgs.append(msg)

                    try:
                        datos_rues, api_fallida = buscar_info_terceros(nits_list, progress_bar, log_fn=_log_fn)
                    except Exception as e:
                        _log_msgs.append(f"💥 **ERROR INESPERADO:** {type(e).__name__}: {str(e)}")
                        datos_rues = {}
                        api_fallida = True

                    progress_bar.empty()
                    st.write("**📋 Log de búsqueda:**")
                    for msg in _log_msgs:
                        st.markdown(msg)

                    if datos_rues:
                        n_con_dir_rues = sum(1 for d in datos_rues.values() if d.get('dir'))
                        n_con_rs = sum(1 for d in datos_rues.values() if d.get('razon_social'))
                        st.success(f"✅ **{len(datos_rues)}** terceros encontrados — "
                                   f"{n_con_dir_rues} con dirección, {n_con_rs} con razón social")

                        fuentes_usadas = {}
                        for d in datos_rues.values():
                            f_nombre = d.get('_fuente', 'Desconocida')
                            fuentes_usadas[f_nombre] = fuentes_usadas.get(f_nombre, 0) + 1
                        if fuentes_usadas:
                            desglose = " | ".join(f"{f}: {n}" for f, n in fuentes_usadas.items())
                            st.info(f"🔗 Fuentes: {desglose}")

                        if not uploaded_dir:
                            rows_auto = []
                            for nit_e, datos_e in datos_rues.items():
                                if datos_e.get('dir'):
                                    rows_auto.append({
                                        'NIT': nit_e, 'Direccion': datos_e['dir'],
                                        'Cod_Depto': datos_e['dp'], 'Cod_Mpio': datos_e['mp'],
                                        'Cod_Pais': datos_e.get('pais', '169'),
                                    })
                            if rows_auto:
                                df_dir_auto = pd.DataFrame(rows_auto)
                    elif api_fallida:
                        st.error("❌ No se encontraron datos. Revisa el log arriba.")
                    else:
                        st.warning("⚠️ Las fuentes respondieron pero sin datos para estos NITs.")

                st.markdown("---")

            dir_final = df_dir if df_dir is not None else df_dir_auto

            with st.spinner("Procesando formatos..."):
                wb, resultados, n_filas, n_terceros, n_con_dir, validaciones = procesar_balance(df, dir_final, datos_rues)

            st.markdown('<div class="success-box">', unsafe_allow_html=True)
            st.markdown("### ✅ Procesamiento completado")
            st.markdown('</div>', unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Filas procesadas", f"{n_filas:,}")
            c2.metric("Terceros identificados", f"{n_terceros:,}")
            c3.metric("Con dirección", f"{n_con_dir:,}")
            c4.metric("Registros generados", f"{sum(resultados.values()):,}")

            if validaciones:
                n_dv_err = sum(1 for tipo, _ in validaciones if tipo == 'dv_error')
                n_rs_err = sum(1 for tipo, _ in validaciones if tipo == 'rs_error')
                n_rs_warn = sum(1 for tipo, _ in validaciones if tipo == 'rs_warn')

                st.markdown("### 🔍 Validación vs Internet")
                cv1, cv2, cv3 = st.columns(3)
                if n_dv_err > 0: cv1.error(f"❌ **{n_dv_err}** DV con error")
                else: cv1.success("✅ Todos los DV correctos")
                if n_rs_err > 0: cv2.error(f"❌ **{n_rs_err}** razones sociales diferentes")
                else: cv2.success("✅ Razones sociales correctas")
                if n_rs_warn > 0: cv3.warning(f"⚠️ **{n_rs_warn}** razones sociales similares (verificar)")
                else: cv3.success("✅ Sin advertencias")
                st.info("📋 Revisa la hoja **'Validacion Terceros'** en el archivo descargado para ver el detalle completo.")
            elif btn_internet and datos_rues:
                st.success("✅ Validación completada: no se encontraron diferencias.")

            st.markdown("### 📋 Resultados por formato")
            cols = st.columns(5)
            for i, (nombre, n) in enumerate(resultados.items()):
                with cols[i % 5]:
                    st.metric(nombre.split(" ", 1)[0], f"{n} reg")

            output = BytesIO()
            wb.save(output)
            output.seek(0)

            st.divider()
            st.download_button(
                label="📥 DESCARGAR ARCHIVO PROCESADO",
                data=output.getvalue(),
                file_name=f"exogena_AG2025_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            st.info("💡 **Formatos manuales:** F1004 (Descuentos), F1011 (Declaraciones) y F1647 (Ingresos para terceros) requieren datos que no están en el balance.")

    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {str(e)}")
        st.info("Verifica que la fila del encabezado sea correcta y que el archivo tenga la estructura esperada.")

st.divider()
st.markdown("""
<div style="text-align: center; color: #999; font-size: 0.85rem;">
    Exógena DIAN AG 2025 | Resolución 000227/2025 | UVT $49.799<br>
    ⚠️ Esta herramienta es un asistente. El contador debe validar los resultados antes de presentar a la DIAN.
</div>
""", unsafe_allow_html=True)

