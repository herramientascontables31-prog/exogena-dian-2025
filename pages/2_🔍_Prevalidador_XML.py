"""
PREVALIDADOR Y GENERADOR XML — EXÓGENA DIAN AG 2025
====================================================
Lee el Excel generado por la App de Exógena, valida todos los campos
requeridos por la DIAN, muestra errores, permite correcciones inline
y genera los XML listos para cargar al portal MUISCA.

Autor: Generado con IA
Versión: 1.0
"""
import streamlit as st
import pandas as pd
import numpy as np
import io, os, re, zipfile
from datetime import datetime
from collections import defaultdict
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

# ======================================================================
# CONSTANTES
# ======================================================================
NM = "222222222"
TDM = "43"
ANO_GRAVABLE = "2025"

# Tipos de documento válidos DIAN
TIPOS_DOC_VALIDOS = {
    "11": "Registro civil",
    "12": "Tarjeta de identidad",
    "13": "Cédula de ciudadanía",
    "21": "Tarjeta de extranjería",
    "22": "Cédula de extranjería",
    "31": "NIT",
    "41": "Pasaporte",
    "42": "Documento de identificación extranjero",
    "43": "Sin identificación del exterior",
    "44": "Documento de identificación extranjero persona jurídica",
    "46": "Carné diplomático",
    "47": "PEP",
    "48": "PPT",
    "50": "NIT de otro país",
}

# Departamentos válidos DIAN
DPTOS_VALIDOS = {
    "05": "Antioquia", "08": "Atlántico", "11": "Bogotá DC",
    "13": "Bolívar", "15": "Boyacá", "17": "Caldas",
    "18": "Caquetá", "19": "Cauca", "20": "Cesar",
    "23": "Córdoba", "25": "Cundinamarca", "27": "Chocó",
    "41": "Huila", "44": "La Guajira", "47": "Magdalena",
    "50": "Meta", "52": "Nariño", "54": "Norte de Santander",
    "63": "Quindío", "66": "Risaralda", "68": "Santander",
    "70": "Sucre", "73": "Tolima", "76": "Valle del Cauca",
    "81": "Arauca", "85": "Casanare", "86": "Putumayo",
    "88": "San Andrés", "91": "Amazonas", "94": "Guainía",
    "95": "Guaviare", "97": "Vaupés", "99": "Vichada",
}

# Conceptos válidos por formato
CONCEPTOS_VALIDOS = {
    "F1001": ["5001","5002","5003","5004","5005","5006","5007","5008","5009","5010",
              "5011","5012","5013","5014","5015","5016","5023","5024","5025","5027",
              "5028","5029","5030","5055","5056","5058","5059","5060","5061","5069",
              "5070","5071","5072","5073","5074","5075","5076","5077","5078","5079",
              "5101","5102","5103","5104","5105"],
    "F1003": ["1301","1302","1303","1304","1305","1306","1307","1308","1309","1310","1311"],
    "F1005": [],  # No usa concepto, son campos directos
    "F1006": [],
    "F1007": ["4001","4002","4003","4004","4005","4006","4007","4008","4009","4010",
              "4015","4016","4017","4018","4019","4020"],
    "F1008": ["1315","1316","1317","1325","1330","1345"],
    "F1009": ["2201","2202","2203","2204","2205","2206","2207","2208","2209","2210"],
    "F1010": [],
    "F1012": ["8301","8302","8303","8304","8305","8306","8307","8308","8309","8310"],
    "F2276": [],
}

# ======================================================================
# UTILIDADES
# ======================================================================
def calc_dv(n):
    n = str(n).replace(".", "").replace("-", "").strip()
    if not n or not n.isdigit() or n == NM:
        return ""
    pesos = [71, 67, 59, 53, 47, 43, 41, 37, 29, 23, 19, 17, 13, 7, 3]
    np_ = n.zfill(15)
    s = sum(int(np_[i]) * pesos[i] for i in range(15))
    r = s % 11
    return str(11 - r) if r >= 2 else str(r)

def safe_str(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    return str(v).strip()

def safe_int(v):
    try:
        return int(float(v))
    except:
        return 0

def detectar_tipo_doc(nit):
    if not nit or nit == NM:
        return TDM
    nit = str(nit).strip()
    if not nit.isdigit():
        return "42"
    if len(nit) >= 9 and nit[0] in ('8', '9'):
        return "31"
    return "13"

def es_persona_natural(td):
    return td in ("13", "12", "11", "21", "22", "41", "46", "47", "48")

def es_persona_juridica(td):
    return td in ("31", "44", "50")

# ======================================================================
# DEFINICIONES DE FORMATOS — Columnas de cada hoja Excel
# ======================================================================
FORMATO_DEFS = {
    "F1001 Pagos": {
        "formato": "1001", "version": "10", "concepto_global": "1",
        "cols": {
            "concepto": 0, "td": 1, "nid": 2, "dv": 3,
            "a1": 4, "a2": 5, "n1": 6, "n2": 7, "rs": 8,
            "dir": 9, "dp": 10, "mp": 11, "pais": 12,
            # Valores
            "pago_deducible": 13, "pago_no_deducible": 14,
            "iva_mayor_valor": 15, "retfte_practicada": 16,
            "iva_mayor_valor_nd": 17, "retica": 18,
            "retiva_practicada": 19, "retiva_asumida": 20,
        },
        "campos_valor": ["pago_deducible", "pago_no_deducible", "iva_mayor_valor",
                         "retfte_practicada", "iva_mayor_valor_nd", "retica",
                         "retiva_practicada", "retiva_asumida"],
        "xml_tag": "pagos", "xml_row": "pag",
    },
    "F1003 Retenciones": {
        "formato": "1003", "version": "7", "concepto_global": "1",
        "cols": {
            "concepto": 0, "td": 1, "nid": 2, "dv": 3,
            "a1": 4, "a2": 5, "n1": 6, "n2": 7, "rs": 8,
            "dir": 9, "dp": 10, "mp": 11,
            "base_retencion": 12, "retencion": 13,
        },
        "campos_valor": ["base_retencion", "retencion"],
        "xml_tag": "retenciones", "xml_row": "ret",
    },
    "F1005 IVA Descontable": {
        "formato": "1005", "version": "8", "concepto_global": "1",
        "cols": {
            "td": 0, "nid": 1, "dv": 2,
            "a1": 3, "a2": 4, "n1": 5, "n2": 6, "rs": 7,
            "dir": 8, "dp": 9, "mp": 10,
            "iva_descontable": 11,
        },
        "campos_valor": ["iva_descontable"],
        "xml_tag": "ivadescontable", "xml_row": "ivd",
    },
    "F1006 IVA Generado": {
        "formato": "1006", "version": "8", "concepto_global": "1",
        "cols": {
            "td": 0, "nid": 1, "dv": 2,
            "a1": 3, "a2": 4, "n1": 5, "n2": 6, "rs": 7,
            "dir": 8, "dp": 9, "mp": 10,
            "iva_generado": 11,
        },
        "campos_valor": ["iva_generado"],
        "xml_tag": "ivagenerado", "xml_row": "ivg",
    },
    "F1007 Ingresos": {
        "formato": "1007", "version": "9", "concepto_global": "1",
        "cols": {
            "concepto": 0, "td": 1, "nid": 2, "dv": 3,
            "a1": 4, "a2": 5, "n1": 6, "n2": 7, "rs": 8,
            "dir": 9, "dp": 10, "mp": 11, "pais": 12,
            "ingreso_recibido": 13, "devol_rebaja_desc": 14,
        },
        "campos_valor": ["ingreso_recibido", "devol_rebaja_desc"],
        "xml_tag": "ingresos", "xml_row": "ing",
    },
    "F1008 CxC": {
        "formato": "1008", "version": "7", "concepto_global": "1",
        "cols": {
            "concepto": 0, "td": 1, "nid": 2, "dv": 3,
            "a1": 4, "a2": 5, "n1": 6, "n2": 7, "rs": 8,
            "dir": 9, "dp": 10, "mp": 11,
            "saldo_cxc": 12,
        },
        "campos_valor": ["saldo_cxc"],
        "xml_tag": "cxcobrar", "xml_row": "cxc",
    },
    "F1009 CxP": {
        "formato": "1009", "version": "7", "concepto_global": "1",
        "cols": {
            "concepto": 0, "td": 1, "nid": 2, "dv": 3,
            "a1": 4, "a2": 5, "n1": 6, "n2": 7, "rs": 8,
            "dir": 9, "dp": 10, "mp": 11,
            "saldo_cxp": 12,
        },
        "campos_valor": ["saldo_cxp"],
        "xml_tag": "cxpagar", "xml_row": "cxp",
    },
    "F1010 Socios": {
        "formato": "1010", "version": "8", "concepto_global": "1",
        "cols": {
            "td": 0, "nid": 1, "dv": 2,
            "a1": 3, "a2": 4, "n1": 5, "n2": 6, "rs": 7,
            "dir": 8, "dp": 9, "mp": 10, "pais": 11,
            "valor_patrimonial": 12, "pct_participacion": 13,
            "acciones": 14,
        },
        "campos_valor": ["valor_patrimonial", "pct_participacion", "acciones"],
        "xml_tag": "socios", "xml_row": "soc",
    },
    "F1012 Inversiones": {
        "formato": "1012", "version": "8", "concepto_global": "1",
        "cols": {
            "concepto": 0, "td": 1, "nid": 2, "dv": 3,
            "a1": 4, "a2": 5, "n1": 6, "n2": 7, "rs": 8,
            "saldo_dic31": 9, "valor_patrimonial": 10,
        },
        "campos_valor": ["saldo_dic31", "valor_patrimonial"],
        "xml_tag": "inversiones", "xml_row": "inv",
    },
    "F2276 Rentas Trabajo": {
        "formato": "2276", "version": "3", "concepto_global": "1",
        "cols": {
            "td": 0, "nid": 1, "dv": 2,
            "a1": 3, "a2": 4, "n1": 5, "n2": 6,
            "dir": 7, "dp": 8, "mp": 9, "pais": 10,
            "salarios": 11, "emol_ecles": 12, "honor_383": 13,
            "serv_383": 14, "comis_383": 15, "pensiones": 16,
            "vacaciones": 17, "cesantias_int": 18,
            "incapacidades": 19, "otros_pag_lab": 20,
            "total_bruto": 21, "aporte_salud": 22, "aporte_pension": 23,
            "sol_pensional": 24, "vol_empleador": 25,
            "vol_trabajador": 26, "afc": 27,
            "retfte": 28, "total_pagos": 29,
        },
        "campos_valor": ["salarios", "emol_ecles", "honor_383", "serv_383",
                         "comis_383", "pensiones", "vacaciones", "cesantias_int",
                         "incapacidades", "otros_pag_lab", "total_bruto",
                         "aporte_salud", "aporte_pension", "sol_pensional",
                         "vol_empleador", "vol_trabajador", "afc",
                         "retfte", "total_pagos"],
        "xml_tag": "rentas", "xml_row": "ren",
    },
}

# ======================================================================
# LECTURA DEL EXCEL
# ======================================================================
@st.cache_data
def leer_excel(uploaded_file):
    """Lee todas las hojas del Excel y retorna datos estructurados por formato."""
    xls = pd.ExcelFile(uploaded_file)
    hojas = xls.sheet_names
    formatos = {}

    for nombre_hoja in hojas:
        if nombre_hoja not in FORMATO_DEFS:
            continue

        fdef = FORMATO_DEFS[nombre_hoja]
        df = pd.read_excel(uploaded_file, sheet_name=nombre_hoja, header=None, skiprows=1)
        if df.empty:
            continue

        registros = []
        for idx, row in df.iterrows():
            reg = {}
            for campo, col_idx in fdef["cols"].items():
                if col_idx < len(row):
                    val = safe_str(row.iloc[col_idx])
                    # Limpiar float artefacts de pandas
                    if val.endswith('.0') and campo not in fdef.get("campos_valor", []):
                        val = val[:-2]
                    # Limpiar "nan"
                    if val.lower() == 'nan':
                        val = ""
                    # Padding especial
                    if campo == "dp" and val:
                        val = val.zfill(2) if val.isdigit() else val
                    elif campo == "mp" and val:
                        val = val.zfill(3) if val.isdigit() else val
                    elif campo == "dv" and val:
                        val = val.split('.')[0] if '.' in val else val
                    reg[campo] = val
                else:
                    reg[campo] = ""
            reg["_fila"] = idx + 2
            registros.append(reg)

        formatos[nombre_hoja] = {
            "def": fdef,
            "registros": registros,
            "hoja": nombre_hoja,
        }

    return formatos


# ======================================================================
# MOTOR DE VALIDACIÓN
# ======================================================================
def validar_formato(nombre, datos):
    """Valida todos los registros de un formato. Retorna lista de errores/warnings."""
    fdef = datos["def"]
    registros = datos["registros"]
    errores = []  # (fila, campo, tipo, mensaje)

    fmt_code = fdef["formato"]
    conceptos_validos = CONCEPTOS_VALIDOS.get(f"F{fmt_code}", [])

    for reg in registros:
        fila = reg["_fila"]
        nid = reg.get("nid", "")
        td = reg.get("td", "")
        dv = reg.get("dv", "")

        # --- NIT ---
        if not nid:
            errores.append((fila, "nid", "❌", "NIT vacío"))
            continue

        # --- Tipo documento ---
        if not td:
            errores.append((fila, "td", "❌", f"Tipo documento vacío para NIT {nid}"))
        elif td not in TIPOS_DOC_VALIDOS:
            errores.append((fila, "td", "❌", f"Tipo doc '{td}' inválido para NIT {nid}"))

        # --- Dígito de verificación ---
        if td == "31":
            dv_calc = calc_dv(nid)
            if dv and dv_calc and dv != dv_calc:
                errores.append((fila, "dv", "❌", f"DV incorrecto NIT {nid}: tiene '{dv}', debe ser '{dv_calc}'"))
            elif not dv:
                errores.append((fila, "dv", "⚠️", f"DV vacío para NIT {nid}"))

        # --- Nombres ---
        if nid != NM:
            if es_persona_natural(td):
                a1 = reg.get("a1", "")
                n1 = reg.get("n1", "")
                if not a1:
                    errores.append((fila, "a1", "❌", f"Primer apellido vacío — NIT {nid} (persona natural)"))
                if not n1:
                    errores.append((fila, "n1", "❌", f"Primer nombre vacío — NIT {nid} (persona natural)"))
            elif es_persona_juridica(td):
                rs = reg.get("rs", "")
                if not rs:
                    errores.append((fila, "rs", "❌", f"Razón social vacía — NIT {nid} (persona jurídica)"))

        # --- Dirección ---
        if "dir" in reg and not reg["dir"] and nid != NM:
            errores.append((fila, "dir", "⚠️", f"Dirección vacía — NIT {nid}"))

        # --- Departamento ---
        dp = reg.get("dp", "")
        if "dp" in fdef["cols"]:
            if dp and dp not in DPTOS_VALIDOS and nid != NM:
                errores.append((fila, "dp", "⚠️", f"Dpto '{dp}' no reconocido — NIT {nid}"))
            elif not dp and nid != NM:
                errores.append((fila, "dp", "⚠️", f"Departamento vacío — NIT {nid}"))

        # --- Municipio ---
        mp = reg.get("mp", "")
        if "mp" in fdef["cols"]:
            if not mp and nid != NM:
                errores.append((fila, "mp", "⚠️", f"Municipio vacío — NIT {nid}"))

        # --- Concepto ---
        if "concepto" in reg and conceptos_validos:
            conc = reg.get("concepto", "")
            if conc and conc not in conceptos_validos:
                errores.append((fila, "concepto", "⚠️",
                    f"Concepto '{conc}' no está en la lista estándar del F{fmt_code}"))

        # --- Valores ---
        for campo_v in fdef["campos_valor"]:
            val = reg.get(campo_v, "")
            if val:
                try:
                    v = float(val)
                    if v < 0:
                        errores.append((fila, campo_v, "⚠️",
                            f"Valor negativo en {campo_v}: {v} — NIT {nid}"))
                except:
                    errores.append((fila, campo_v, "❌",
                        f"Valor no numérico en {campo_v}: '{val}' — NIT {nid}"))

    return errores


def resumen_validacion(formatos):
    """Ejecuta validación de todos los formatos y genera resumen."""
    resultados = {}
    for nombre, datos in formatos.items():
        errores = validar_formato(nombre, datos)
        criticos = sum(1 for e in errores if e[2] == "❌")
        warnings = sum(1 for e in errores if e[2] == "⚠️")
        resultados[nombre] = {
            "registros": len(datos["registros"]),
            "errores": errores,
            "criticos": criticos,
            "warnings": warnings,
            "listo": criticos == 0,
        }
    return resultados


# ======================================================================
# GENERADOR XML — Estructura DIAN
# ======================================================================
def generar_xml_formato(nombre_hoja, datos, info_declarante, num_envio):
    """Genera el XML DIAN para un formato específico."""
    fdef = datos["def"]
    registros = datos["registros"]

    if not registros:
        return None

    root = Element("mas")
    root.set("xmlns", "http://www.dian.gov.co/muisca/mas")

    # === CABECERA ===
    cab = SubElement(root, "Cab")
    campos_cab = [
        ("CodCpt", fdef["concepto_global"]),
        ("Formato", fdef["formato"]),
        ("Version", fdef["version"]),
        ("AnoGrav", ANO_GRAVABLE),
        ("NumEnvio", str(num_envio).zfill(5)),
        ("FecEnvio", datetime.now().strftime("%Y-%m-%d")),
        ("FecIni", f"{ANO_GRAVABLE}-01-01"),
        ("FecFin", f"{ANO_GRAVABLE}-12-31"),
        ("NumReg", str(len(registros))),
        ("TipoDoc", info_declarante.get("td", "31")),
        ("NumNit", info_declarante.get("nit", "")),
        ("DV", info_declarante.get("dv", "")),
        ("Ape1", info_declarante.get("a1", "")),
        ("Ape2", info_declarante.get("a2", "")),
        ("Nom1", info_declarante.get("n1", "")),
        ("Nom2", info_declarante.get("n2", "")),
        ("RazonSocial", info_declarante.get("rs", "")),
        ("Direccion", info_declarante.get("dir", "")),
        ("CodDpto", info_declarante.get("dp", "")),
        ("CodMpio", info_declarante.get("mp", "")),
    ]
    for tag, val in campos_cab:
        el = SubElement(cab, tag)
        el.text = str(val) if val else ""

    # === DETALLE ===
    sec = SubElement(root, fdef["xml_tag"])
    cols = fdef["cols"]
    campos_valor = fdef["campos_valor"]

    # Mapeo de campos internos a tags XML
    TAG_MAP = {
        "concepto": "co", "td": "tdoc", "nid": "nid", "dv": "dv",
        "a1": "ape1", "a2": "ape2", "n1": "nom1", "n2": "nom2",
        "rs": "raz", "dir": "dir", "dp": "dpto", "mp": "mpio",
        "pais": "pais",
    }

    for reg in registros:
        row_el = SubElement(sec, fdef["xml_row"])

        # Campos de identificación
        for campo in cols:
            if campo.startswith("_"):
                continue
            tag = TAG_MAP.get(campo, campo)
            val = reg.get(campo, "")

            # Valores numéricos → enteros
            if campo in campos_valor:
                try:
                    val = str(int(float(val))) if val else "0"
                except:
                    val = "0"

            el = SubElement(row_el, tag)
            el.text = str(val) if val else ""

    # Formatear XML con indentación
    xml_str = tostring(root, encoding="unicode")
    try:
        dom = parseString(xml_str)
        xml_pretty = dom.toprettyxml(indent="  ", encoding="ISO-8859-1")
        # Reemplazar la declaración XML generada por minidom
        lines = xml_pretty.decode("ISO-8859-1").split("\n")
        lines[0] = '<?xml version="1.0" encoding="ISO-8859-1"?>'
        return "\n".join(lines)
    except:
        return f'<?xml version="1.0" encoding="ISO-8859-1"?>\n{xml_str}'


# ======================================================================
# INTERFAZ STREAMLIT
# ======================================================================
def main():
    st.set_page_config(
        page_title="Prevalidador XML — Exógena DIAN",
        page_icon="🔍",
        layout="wide"
    )

    st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    h1 { color: #1a5276; }
    .stat-box {
        background: white; border-radius: 8px; padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        text-align: center; margin: 4px;
    }
    .stat-num { font-size: 28px; font-weight: bold; }
    .stat-label { font-size: 12px; color: #666; margin-top: 4px; }
    .ok { color: #27ae60; }
    .warn { color: #f39c12; }
    .err { color: #e74c3c; }
    </style>
    """, unsafe_allow_html=True)

    st.title("🔍 Prevalidador y Generador XML — Exógena DIAN")
    st.caption("Cargue el Excel generado por la App de Exógena, valide los datos y genere los XML para el MUISCA")

    # =================================================================
    # SIDEBAR — Datos del declarante
    # =================================================================
    with st.sidebar:
        st.header("📋 Datos del Declarante")
        st.caption("Requeridos para generar los XML")

        decl_nit = st.text_input("NIT del declarante", placeholder="900123456")
        decl_dv = ""
        if decl_nit:
            decl_dv = calc_dv(decl_nit)
            st.text(f"DV: {decl_dv}")

        decl_td = st.selectbox("Tipo de declarante",
                               ["31 - NIT (Persona Jurídica)", "13 - CC (Persona Natural)"],
                               index=0)
        decl_td_code = decl_td[:2]

        if decl_td_code == "31":
            decl_rs = st.text_input("Razón Social", placeholder="MI EMPRESA S.A.S")
            decl_a1 = decl_a2 = decl_n1 = decl_n2 = ""
        else:
            decl_a1 = st.text_input("Primer Apellido")
            decl_a2 = st.text_input("Segundo Apellido")
            decl_n1 = st.text_input("Primer Nombre")
            decl_n2 = st.text_input("Segundo Nombre")
            decl_rs = ""

        decl_dir = st.text_input("Dirección", placeholder="CRA 10 # 20-30")
        decl_dp = st.text_input("Cod. Departamento", placeholder="05", max_chars=2)
        decl_mp = st.text_input("Cod. Municipio", placeholder="05001", max_chars=5)

        st.divider()
        st.subheader("📨 Consecutivos XML")
        st.caption("Número de envío inicial. Cada formato se numera consecutivamente.")
        num_envio_inicio = st.number_input("Envío inicial", min_value=1, value=1, step=1)

        st.divider()
        rep_legal_td = st.text_input("Tipo Doc Rep. Legal", value="13", max_chars=2)
        rep_legal_nit = st.text_input("CC Rep. Legal", placeholder="1234567890")
        rep_legal_dv = calc_dv(rep_legal_nit) if rep_legal_nit else ""
        rep_legal_a1 = st.text_input("Apellido1 Rep. Legal")
        rep_legal_n1 = st.text_input("Nombre1 Rep. Legal")

    info_declarante = {
        "td": decl_td_code, "nit": decl_nit, "dv": decl_dv,
        "a1": decl_a1 if decl_td_code != "31" else "",
        "a2": decl_a2 if decl_td_code != "31" else "",
        "n1": decl_n1 if decl_td_code != "31" else "",
        "n2": decl_n2 if decl_td_code != "31" else "",
        "rs": decl_rs, "dir": decl_dir, "dp": decl_dp, "mp": decl_mp,
    }

    # =================================================================
    # ÁREA PRINCIPAL — Carga de archivo
    # =================================================================
    uploaded = st.file_uploader("📁 Suba el Excel de Exógena", type=["xlsx"])

    if not uploaded:
        st.info("👆 Suba el archivo Excel generado por la App de Exógena para comenzar la validación.")

        with st.expander("ℹ️ ¿Cómo funciona?"):
            st.markdown("""
            **Paso 1:** Genere el Excel con la App de Exógena (App 1)

            **Paso 2:** Súbalo aquí. El prevalidador revisa:
            - ✅ NIT y DV correctos
            - ✅ Nombres completos (apellidos para CC, razón social para NIT)
            - ✅ Dirección, departamento y municipio
            - ✅ Conceptos válidos por formato
            - ✅ Valores numéricos positivos

            **Paso 3:** Corrija los errores en el Excel o aquí mismo

            **Paso 4:** Complete los datos del declarante en la barra lateral

            **Paso 5:** Genere los XML y cárguelos al MUISCA
            """)
        return

    # =================================================================
    # PROCESAR ARCHIVO
    # =================================================================
    formatos = leer_excel(uploaded)

    if not formatos:
        st.error("No se encontraron hojas con formatos válidos en el archivo.")
        return

    # Ejecutar validación
    resultados = resumen_validacion(formatos)

    # =================================================================
    # DASHBOARD DE VALIDACIÓN
    # =================================================================
    total_regs = sum(r["registros"] for r in resultados.values())
    total_criticos = sum(r["criticos"] for r in resultados.values())
    total_warnings = sum(r["warnings"] for r in resultados.values())
    formatos_listos = sum(1 for r in resultados.values() if r["listo"])
    total_formatos = len(resultados)

    # Indicadores principales
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="stat-box">
            <div class="stat-num">{total_formatos}</div>
            <div class="stat-label">Formatos cargados</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="stat-box">
            <div class="stat-num">{total_regs:,}</div>
            <div class="stat-label">Registros totales</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        color = "ok" if total_criticos == 0 else "err"
        st.markdown(f"""<div class="stat-box">
            <div class="stat-num {color}">{total_criticos}</div>
            <div class="stat-label">Errores críticos</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="stat-box">
            <div class="stat-num ok">{formatos_listos} / {total_formatos}</div>
            <div class="stat-label">Listos para XML</div>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # =================================================================
    # TABLA RESUMEN POR FORMATO
    # =================================================================
    st.subheader("📊 Estado por formato")

    tabla_data = []
    for nombre, res in resultados.items():
        estado = "✅ Listo" if res["listo"] else f"❌ {res['criticos']} errores"
        tabla_data.append({
            "Formato": nombre,
            "Registros": res["registros"],
            "Errores": res["criticos"],
            "Advertencias": res["warnings"],
            "Estado": estado,
        })

    df_tabla = pd.DataFrame(tabla_data)
    st.dataframe(df_tabla, use_container_width=True, hide_index=True)

    # =================================================================
    # DETALLE DE ERRORES POR FORMATO
    # =================================================================
    st.subheader("🔎 Detalle de errores")

    formatos_con_errores = {k: v for k, v in resultados.items() if v["errores"]}

    if not formatos_con_errores:
        st.success("🎉 ¡Todos los formatos pasaron la validación sin errores críticos!")
    else:
        for nombre, res in formatos_con_errores.items():
            with st.expander(
                f"{'❌' if res['criticos'] > 0 else '⚠️'} {nombre} — "
                f"{res['criticos']} errores, {res['warnings']} advertencias",
                expanded=(res['criticos'] > 0)
            ):
                # Agrupar errores por tipo
                errores_por_campo = defaultdict(list)
                for fila, campo, tipo, msg in res["errores"]:
                    errores_por_campo[campo].append((fila, tipo, msg))

                for campo, errs in errores_por_campo.items():
                    st.markdown(f"**Campo: `{campo}`** ({len(errs)} problemas)")
                    # Mostrar solo los primeros 10
                    for fila, tipo, msg in errs[:10]:
                        st.markdown(f"  {tipo} Fila {fila}: {msg}")
                    if len(errs) > 10:
                        st.caption(f"  ... y {len(errs) - 10} más")

                # Análisis rápido de NIT sin dirección
                nits_sin_dir = set()
                for fila, campo, tipo, msg in res["errores"]:
                    if campo == "dir":
                        nit_match = re.search(r'NIT (\d+)', msg)
                        if nit_match:
                            nits_sin_dir.add(nit_match.group(1))

                if nits_sin_dir:
                    st.info(f"💡 {len(nits_sin_dir)} terceros sin dirección. "
                            "Puede completarlas en el directorio del Excel o en la App 1 "
                            "con un archivo de directorio externo.")

    # =================================================================
    # VALIDACIÓN DEL DECLARANTE
    # =================================================================
    st.divider()
    st.subheader("📋 Validación datos del declarante")

    errores_decl = []
    if not decl_nit:
        errores_decl.append("❌ NIT del declarante vacío")
    elif not decl_nit.isdigit():
        errores_decl.append("❌ NIT del declarante debe ser numérico")
    if decl_td_code == "31" and not decl_rs:
        errores_decl.append("❌ Razón social vacía (requerida para NIT)")
    if decl_td_code == "13" and not decl_a1:
        errores_decl.append("❌ Primer apellido vacío (requerido para CC)")
    if not decl_dir:
        errores_decl.append("❌ Dirección del declarante vacía")
    if not decl_dp:
        errores_decl.append("❌ Departamento del declarante vacío")
    if not decl_mp:
        errores_decl.append("❌ Municipio del declarante vacío")

    if errores_decl:
        for e in errores_decl:
            st.error(e)
        st.warning("⚠️ Complete los datos del declarante en la **barra lateral izquierda** antes de generar XML.")
    else:
        st.success("✅ Datos del declarante completos")

    # =================================================================
    # GENERACIÓN DE XML
    # =================================================================
    st.divider()
    st.subheader("📤 Generar XML para DIAN")

    # Verificar si se puede generar
    puede_generar = (total_criticos == 0 and len(errores_decl) == 0)
    puede_forzar = (len(errores_decl) == 0 and total_criticos > 0)

    if puede_generar:
        st.success("✅ Todo listo para generar los XML")
    elif puede_forzar:
        st.warning(f"⚠️ Hay {total_criticos} errores críticos. Puede generar de todas formas "
                   "pero los XML podrían ser rechazados por la DIAN.")
    else:
        st.error("❌ Complete los datos del declarante y corrija los errores críticos antes de generar.")

    # Selección de formatos a generar
    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        formatos_disponibles = list(formatos.keys())
        formatos_seleccionados = st.multiselect(
            "Formatos a generar",
            formatos_disponibles,
            default=formatos_disponibles,
        )

    generar = False
    with col_btn:
        st.write("")  # Spacer
        if puede_generar:
            generar = st.button("🚀 Generar XML", type="primary", use_container_width=True)
        elif puede_forzar:
            generar = st.button("⚠️ Generar con errores", type="secondary", use_container_width=True)

    if generar and formatos_seleccionados:
        xmls_generados = {}
        num_envio = num_envio_inicio

        progress = st.progress(0, text="Generando XML...")
        for i, nombre_hoja in enumerate(formatos_seleccionados):
            datos = formatos[nombre_hoja]
            fdef = datos["def"]
            fmt_num = fdef["formato"]

            xml_content = generar_xml_formato(nombre_hoja, datos, info_declarante, num_envio)
            if xml_content:
                filename = f"{fmt_num}_{ANO_GRAVABLE}_{str(num_envio).zfill(5)}.xml"
                xmls_generados[filename] = xml_content
                num_envio += 1

            progress.progress((i + 1) / len(formatos_seleccionados),
                            text=f"Generando {nombre_hoja}...")

        progress.empty()

        if xmls_generados:
            st.success(f"✅ {len(xmls_generados)} archivos XML generados")

            # Tabla de archivos generados
            st.markdown("**Archivos generados:**")
            tabla_xml = []
            for fn, content in xmls_generados.items():
                n_lines = content.count("<" + list(FORMATO_DEFS.values())[0]["xml_row"])
                tabla_xml.append({
                    "Archivo": fn,
                    "Tamaño": f"{len(content):,} bytes",
                    "Envío #": fn.split("_")[-1].replace(".xml", ""),
                })
            st.dataframe(pd.DataFrame(tabla_xml), use_container_width=True, hide_index=True)

            # Descargas individuales
            st.markdown("**Descargar:**")
            cols_dl = st.columns(min(len(xmls_generados), 4))
            for i, (fn, content) in enumerate(xmls_generados.items()):
                with cols_dl[i % len(cols_dl)]:
                    st.download_button(
                        f"📥 {fn}",
                        data=content.encode("ISO-8859-1"),
                        file_name=fn,
                        mime="application/xml",
                        use_container_width=True,
                    )

            # ZIP con todos
            st.divider()
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for fn, content in xmls_generados.items():
                    zf.writestr(fn, content.encode("ISO-8859-1"))
            zip_buffer.seek(0)

            st.download_button(
                "📦 Descargar TODOS los XML (ZIP)",
                data=zip_buffer,
                file_name=f"Exogena_XML_{ANO_GRAVABLE}.zip",
                mime="application/zip",
                type="primary",
                use_container_width=True,
            )

            # Previsualización
            with st.expander("👁️ Previsualizar XML"):
                xml_preview = st.selectbox("Seleccionar archivo", list(xmls_generados.keys()))
                if xml_preview:
                    st.code(xmls_generados[xml_preview][:3000], language="xml")
                    if len(xmls_generados[xml_preview]) > 3000:
                        st.caption(f"... mostrando primeros 3,000 de {len(xmls_generados[xml_preview]):,} caracteres")

    # =================================================================
    # ESTADÍSTICAS ADICIONALES
    # =================================================================
    st.divider()
    with st.expander("📈 Análisis de calidad de datos"):
        # NIT más problemáticos
        todos_errores = []
        for nombre, res in resultados.items():
            for e in res["errores"]:
                todos_errores.append((nombre, *e))

        if todos_errores:
            # Por tipo de error
            tipos_error = defaultdict(int)
            for _, _, campo, tipo, msg in todos_errores:
                tipos_error[campo] += 1

            st.markdown("**Errores por campo:**")
            df_campos = pd.DataFrame([
                {"Campo": k, "Errores": v}
                for k, v in sorted(tipos_error.items(), key=lambda x: -x[1])
            ])
            st.dataframe(df_campos, use_container_width=True, hide_index=True)

            # NITs con más errores
            nits_errores = defaultdict(int)
            for _, _, campo, tipo, msg in todos_errores:
                nit_match = re.search(r'NIT (\d+)', msg)
                if nit_match:
                    nits_errores[nit_match.group(1)] += 1

            if nits_errores:
                st.markdown("**Terceros con más problemas (Top 10):**")
                top_nits = sorted(nits_errores.items(), key=lambda x: -x[1])[:10]
                df_nits = pd.DataFrame([{"NIT": k, "Errores": v} for k, v in top_nits])
                st.dataframe(df_nits, use_container_width=True, hide_index=True)
        else:
            st.info("No hay errores que analizar. ¡Los datos están limpios!")


if __name__ == "__main__":
    main()
