"""
PREVALIDADOR Y GENERADOR XML — EXOGENA DIAN AG 2025
====================================================
Lee el Excel generado por la App de Exogena, valida todos los campos
requeridos por la DIAN, muestra errores, permite correcciones inline,
rellena direcciones faltantes y genera los XML listos para el MUISCA.

Version: 2.0
"""
import streamlit as st
import pandas as pd
import numpy as np
import io, os, re, zipfile, copy
from datetime import datetime
from collections import defaultdict
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

NM = "222222222"
TDM = "43"
ANO_GRAVABLE = "2025"

TIPOS_DOC_VALIDOS = {
    "11": "Registro civil", "12": "Tarjeta de identidad",
    "13": "Cedula de ciudadania", "21": "Tarjeta de extranjeria",
    "22": "Cedula de extranjeria", "31": "NIT",
    "41": "Pasaporte", "42": "Doc. identificacion extranjero",
    "43": "Sin identificacion del exterior",
    "44": "Doc. ID extranjero persona juridica",
    "46": "Carne diplomatico", "47": "PEP", "48": "PPT",
    "50": "NIT de otro pais",
}

DPTOS_VALIDOS = {
    "05": "Antioquia", "08": "Atlantico", "11": "Bogota DC",
    "13": "Bolivar", "15": "Boyaca", "17": "Caldas",
    "18": "Caqueta", "19": "Cauca", "20": "Cesar",
    "23": "Cordoba", "25": "Cundinamarca", "27": "Choco",
    "41": "Huila", "44": "La Guajira", "47": "Magdalena",
    "50": "Meta", "52": "Narino", "54": "Norte de Santander",
    "63": "Quindio", "66": "Risaralda", "68": "Santander",
    "70": "Sucre", "73": "Tolima", "76": "Valle del Cauca",
    "81": "Arauca", "85": "Casanare", "86": "Putumayo",
    "88": "San Andres", "91": "Amazonas", "94": "Guainia",
    "95": "Guaviare", "97": "Vaupes", "99": "Vichada",
}

CONCEPTOS_VALIDOS = {
    "F1001": ["5001","5002","5003","5004","5005","5006","5007","5008","5009","5010",
              "5011","5012","5013","5014","5015","5016","5023","5024","5025","5027",
              "5028","5029","5030","5055","5056","5058","5059","5060","5061","5069",
              "5070","5071","5072","5073","5074","5075","5076","5077","5078","5079",
              "5101","5102","5103","5104","5105"],
    "F1003": ["1301","1302","1303","1304","1305","1306","1307","1308","1309","1310","1311"],
    "F1005": [], "F1006": [],
    "F1007": ["4001","4002","4003","4004","4005","4006","4007","4008","4009","4010",
              "4015","4016","4017","4018","4019","4020"],
    "F1008": ["1315","1316","1317","1325","1330","1345"],
    "F1009": ["2201","2202","2203","2204","2205","2206","2207","2208","2209","2210"],
    "F1010": [],
    "F1012": ["8301","8302","8303","8304","8305","8306","8307","8308","8309","8310"],
    "F2276": [],
}

ORDEN_FORMATOS = [
    "F1001 Pagos", "F1003 Retenciones", "F1005 IVA Descontable",
    "F1006 IVA Generado", "F1007 Ingresos", "F1008 CxC",
    "F1009 CxP", "F1010 Socios", "F1012 Inversiones",
    "F2276 Rentas Trabajo",
]

def calc_dv(n):
    n = str(n).replace(".", "").replace("-", "").strip()
    if not n or not n.isdigit() or n == NM: return ""
    pesos = [71, 67, 59, 53, 47, 43, 41, 37, 29, 23, 19, 17, 13, 7, 3]
    np_ = n.zfill(15)
    s = sum(int(np_[i]) * pesos[i] for i in range(15))
    r = s % 11
    return str(11 - r) if r >= 2 else str(r)

def safe_str(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return ""
    return str(v).strip()

def safe_int(v):
    try: return int(float(v))
    except: return 0

def detectar_tipo_doc(nit):
    if not nit or nit == NM: return TDM
    nit = str(nit).strip()
    if not nit.isdigit(): return "42"
    if len(nit) >= 9 and nit[0] in ('8', '9'): return "31"
    return "13"

def es_persona_natural(td):
    return td in ("13", "12", "11", "21", "22", "41", "46", "47", "48")

def es_persona_juridica(td):
    return td in ("31", "44", "50")

def es_tipo_doc_extranjero(td):
    """Tipos de documento que indican tercero del exterior."""
    return td in ("42", "43", "44", "50", "41")

def es_nacional(td):
    """Tipos de documento nacionales colombianos."""
    return td in ("11", "12", "13", "21", "22", "31", "46", "47", "48")

def sanitizar_registro(reg, fdef, info_declarante):
    """Sanitiza un registro para que el XML no tenga campos vacíos que la DIAN rechace.
    Reglas:
    - td: OBLIGATORIO. Si vacío, auto-detectar del NIT.
    - nid: OBLIGATORIO. Si vacío, el registro no debería existir.
    - dv: Obligatorio para td=31. Auto-calcular si falta.
    - Persona natural (td 13,12,11,etc): a1 y n1 obligatorios, rs vacía.
    - Persona jurídica (td 31,44,50): rs obligatoria, a1/a2/n1/n2 vacíos.
    - Exterior (td 42,43): rs obligatoria, a1/a2/n1/n2 vacíos, dir/dp/mp vacíos, pais NO Colombia.
    - NM (222222222): td=43, rs=CUANTIAS MENORES, sin dir/dp/mp.
    - Nacional: dir, dp, mp obligatorios. Si faltan, usar datos de empresa.
    - Campos numéricos: "0" en vez de vacío.
    """
    r = dict(reg)  # Copia
    nid = r.get("nid", "")
    if not nid:
        return r  # Sin NIT no hay nada que hacer

    # --- Tipo documento ---
    td = r.get("td", "")
    if not td:
        td = detectar_tipo_doc(nid)
        r["td"] = td

    # --- DV ---
    if "dv" in fdef["cols"]:
        if td == "31" and not r.get("dv", ""):
            r["dv"] = calc_dv(nid)
        elif td != "31":
            # Para no-NIT, DV puede ir vacío pero DIAN a veces lo pide
            if not r.get("dv", ""):
                r["dv"] = ""

    # --- Cuantías menores (222222222) ---
    if nid == NM:
        r["td"] = "43"
        r["dv"] = ""
        for campo in ("a1", "a2", "n1", "n2"):
            if campo in fdef["cols"]: r[campo] = ""
        if "rs" in fdef["cols"]: r["rs"] = "CUANTIAS MENORES"
        if "dir" in fdef["cols"]: r["dir"] = ""
        if "dp" in fdef["cols"]: r["dp"] = ""
        if "mp" in fdef["cols"]: r["mp"] = ""
        if "pais" in fdef["cols"]: r["pais"] = "169"
        # Campos valor: asegurar "0" no vacío
        for cv in fdef["campos_valor"]:
            if not r.get(cv, ""): r[cv] = "0"
        return r

    # --- Exterior (td 42, 43, 44, 50, 41) ---
    if es_tipo_doc_extranjero(td):
        # Todo va en razón social, sin nombres
        if "rs" in fdef["cols"]:
            if not r.get("rs", ""):
                # Intentar armar rs desde nombres si los tiene
                nombre_completo = " ".join(filter(None, [r.get("a1",""), r.get("a2",""), r.get("n1",""), r.get("n2","")]))
                r["rs"] = nombre_completo if nombre_completo else nid
        for campo in ("a1", "a2", "n1", "n2"):
            if campo in fdef["cols"]: r[campo] = ""
        # Sin dirección/dpto/mpio para exterior
        if "dir" in fdef["cols"]: r["dir"] = ""
        if "dp" in fdef["cols"]: r["dp"] = ""
        if "mp" in fdef["cols"]: r["mp"] = ""
        # País no puede ser Colombia
        if "pais" in fdef["cols"]:
            pais = r.get("pais", "")
            if not pais or pais in ("169", "170"):
                r["pais"] = "840"  # Default USA si no detecta
        r["dv"] = ""
    # --- Persona natural ---
    elif es_persona_natural(td):
        # a1 y n1 obligatorios
        if "a1" in fdef["cols"] and not r.get("a1", ""):
            # Intentar extraer de razón social
            rs = r.get("rs", "")
            if rs:
                p = rs.split()
                if len(p) >= 1: r["a1"] = p[0]
                if len(p) >= 2 and not r.get("a2", ""): r["a2"] = p[1]
                if len(p) >= 3 and not r.get("n1", ""): r["n1"] = p[2]
                if len(p) >= 4 and not r.get("n2", ""): r["n2"] = " ".join(p[3:])
            else:
                r["a1"] = nid  # Último recurso
        if "n1" in fdef["cols"] and not r.get("n1", ""):
            r["n1"] = "NN"  # Último recurso para que DIAN no rechace
        # rs debe ir vacía para persona natural
        if "rs" in fdef["cols"]:
            r["rs"] = ""
    # --- Persona jurídica ---
    elif es_persona_juridica(td):
        if "rs" in fdef["cols"] and not r.get("rs", ""):
            # Intentar armar rs desde nombres si los tiene
            nombre_completo = " ".join(filter(None, [r.get("a1",""), r.get("a2",""), r.get("n1",""), r.get("n2","")]))
            r["rs"] = nombre_completo if nombre_completo else nid
        for campo in ("a1", "a2", "n1", "n2"):
            if campo in fdef["cols"]: r[campo] = ""

    # --- Dirección para nacionales ---
    if es_nacional(td) and nid != NM:
        if "dir" in fdef["cols"] and not r.get("dir", ""):
            r["dir"] = info_declarante.get("dir", "") or "SIN DIRECCION"
        if "dp" in fdef["cols"] and not r.get("dp", ""):
            r["dp"] = info_declarante.get("dp", "") or "11"
        if "mp" in fdef["cols"] and not r.get("mp", ""):
            r["mp"] = info_declarante.get("mp", "") or "11001"
    
    # --- País por defecto ---
    if "pais" in fdef["cols"] and not r.get("pais", ""):
        if es_tipo_doc_extranjero(td):
            r["pais"] = "840"
        else:
            r["pais"] = "169"

    # --- Campos numéricos: "0" en vez de vacío ---
    for cv in fdef["campos_valor"]:
        val = r.get(cv, "")
        if not val:
            r[cv] = "0"
        else:
            try:
                r[cv] = str(int(float(val)))
            except:
                r[cv] = "0"

    return r

FORMATO_DEFS = {
    "F1001 Pagos": {
        "formato": "1001", "version": "10", "concepto_global": "1",
        "cols": {"concepto": 0, "td": 1, "nid": 2, "dv": 3,
            "a1": 4, "a2": 5, "n1": 6, "n2": 7, "rs": 8,
            "dir": 9, "dp": 10, "mp": 11, "pais": 12,
            "pago_deducible": 13, "pago_no_deducible": 14,
            "iva_mayor_valor": 15, "retfte_practicada": 16,
            "iva_mayor_valor_nd": 17, "retica": 18,
            "retiva_practicada": 19, "retiva_asumida": 20},
        "campos_valor": ["pago_deducible", "pago_no_deducible", "iva_mayor_valor",
                         "retfte_practicada", "iva_mayor_valor_nd", "retica",
                         "retiva_practicada", "retiva_asumida"],
        "xml_tag": "pagos", "xml_row": "pag",
    },
    "F1003 Retenciones": {
        "formato": "1003", "version": "7", "concepto_global": "1",
        "cols": {"concepto": 0, "td": 1, "nid": 2, "dv": 3,
            "a1": 4, "a2": 5, "n1": 6, "n2": 7, "rs": 8,
            "dir": 9, "dp": 10, "mp": 11,
            "base_retencion": 12, "retencion": 13},
        "campos_valor": ["base_retencion", "retencion"],
        "xml_tag": "retenciones", "xml_row": "ret",
    },
    "F1005 IVA Descontable": {
        "formato": "1005", "version": "8", "concepto_global": "1",
        "cols": {"td": 0, "nid": 1, "dv": 2,
            "a1": 3, "a2": 4, "n1": 5, "n2": 6, "rs": 7,
            "dir": 8, "dp": 9, "mp": 10, "iva_descontable": 11},
        "campos_valor": ["iva_descontable"],
        "xml_tag": "ivadescontable", "xml_row": "ivd",
    },
    "F1006 IVA Generado": {
        "formato": "1006", "version": "8", "concepto_global": "1",
        "cols": {"td": 0, "nid": 1, "dv": 2,
            "a1": 3, "a2": 4, "n1": 5, "n2": 6, "rs": 7,
            "dir": 8, "dp": 9, "mp": 10, "iva_generado": 11},
        "campos_valor": ["iva_generado"],
        "xml_tag": "ivagenerado", "xml_row": "ivg",
    },
    "F1007 Ingresos": {
        "formato": "1007", "version": "9", "concepto_global": "1",
        "cols": {"concepto": 0, "td": 1, "nid": 2, "dv": 3,
            "a1": 4, "a2": 5, "n1": 6, "n2": 7, "rs": 8,
            "dir": 9, "dp": 10, "mp": 11, "pais": 12,
            "ingreso_recibido": 13, "devol_rebaja_desc": 14},
        "campos_valor": ["ingreso_recibido", "devol_rebaja_desc"],
        "xml_tag": "ingresos", "xml_row": "ing",
    },
    "F1008 CxC": {
        "formato": "1008", "version": "7", "concepto_global": "1",
        "cols": {"concepto": 0, "td": 1, "nid": 2, "dv": 3,
            "a1": 4, "a2": 5, "n1": 6, "n2": 7, "rs": 8,
            "dir": 9, "dp": 10, "mp": 11, "saldo_cxc": 12},
        "campos_valor": ["saldo_cxc"],
        "xml_tag": "cxcobrar", "xml_row": "cxc",
    },
    "F1009 CxP": {
        "formato": "1009", "version": "7", "concepto_global": "1",
        "cols": {"concepto": 0, "td": 1, "nid": 2, "dv": 3,
            "a1": 4, "a2": 5, "n1": 6, "n2": 7, "rs": 8,
            "dir": 9, "dp": 10, "mp": 11, "saldo_cxp": 12},
        "campos_valor": ["saldo_cxp"],
        "xml_tag": "cxpagar", "xml_row": "cxp",
    },
    "F1010 Socios": {
        "formato": "1010", "version": "8", "concepto_global": "1",
        "cols": {"td": 0, "nid": 1, "dv": 2,
            "a1": 3, "a2": 4, "n1": 5, "n2": 6, "rs": 7,
            "dir": 8, "dp": 9, "mp": 10, "pais": 11,
            "valor_patrimonial": 12, "pct_participacion": 13, "acciones": 14},
        "campos_valor": ["valor_patrimonial", "pct_participacion", "acciones"],
        "xml_tag": "socios", "xml_row": "soc",
    },
    "F1012 Inversiones": {
        "formato": "1012", "version": "8", "concepto_global": "1",
        "cols": {"concepto": 0, "td": 1, "nid": 2, "dv": 3,
            "a1": 4, "a2": 5, "n1": 6, "n2": 7, "rs": 8,
            "saldo_dic31": 9, "valor_patrimonial": 10},
        "campos_valor": ["saldo_dic31", "valor_patrimonial"],
        "xml_tag": "inversiones", "xml_row": "inv",
    },
    "F2276 Rentas Trabajo": {
        "formato": "2276", "version": "3", "concepto_global": "1",
        "cols": {"td": 0, "nid": 1, "dv": 2,
            "a1": 3, "a2": 4, "n1": 5, "n2": 6,
            "dir": 7, "dp": 8, "mp": 9, "pais": 10,
            "salarios": 11, "emol_ecles": 12, "honor_383": 13,
            "serv_383": 14, "comis_383": 15, "pensiones": 16,
            "vacaciones": 17, "cesantias_int": 18,
            "incapacidades": 19, "otros_pag_lab": 20,
            "total_bruto": 21, "aporte_salud": 22, "aporte_pension": 23,
            "sol_pensional": 24, "vol_empleador": 25,
            "vol_trabajador": 26, "afc": 27,
            "retfte": 28, "total_pagos": 29},
        "campos_valor": ["salarios", "emol_ecles", "honor_383", "serv_383",
                         "comis_383", "pensiones", "vacaciones", "cesantias_int",
                         "incapacidades", "otros_pag_lab", "total_bruto",
                         "aporte_salud", "aporte_pension", "sol_pensional",
                         "vol_empleador", "vol_trabajador", "afc",
                         "retfte", "total_pagos"],
        "xml_tag": "rentas", "xml_row": "ren",
    },
}

def leer_excel(uploaded_file):
    xls = pd.ExcelFile(uploaded_file)
    formatos = {}
    for nombre_hoja in xls.sheet_names:
        if nombre_hoja not in FORMATO_DEFS: continue
        fdef = FORMATO_DEFS[nombre_hoja]
        df = pd.read_excel(uploaded_file, sheet_name=nombre_hoja, header=None, skiprows=1)
        if df.empty: continue
        registros = []
        for idx, row in df.iterrows():
            reg = {}
            for campo, col_idx in fdef["cols"].items():
                if col_idx < len(row):
                    val = safe_str(row.iloc[col_idx])
                    if val.endswith('.0') and campo not in fdef.get("campos_valor", []):
                        val = val[:-2]
                    if val.lower() == 'nan': val = ""
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
        formatos[nombre_hoja] = {"def": fdef, "registros": registros, "hoja": nombre_hoja}
    return formatos

def contar_sin_direccion(formatos):
    resumen = {}
    nits_sin_dir = set()
    for nombre, datos in formatos.items():
        fdef = datos["def"]
        if "dir" not in fdef["cols"]: continue
        sin_dir = 0
        for reg in datos["registros"]:
            nid = reg.get("nid", "")
            dir_val = reg.get("dir", "")
            if nid and nid != NM and not dir_val:
                sin_dir += 1
                nits_sin_dir.add(nid)
        if sin_dir > 0: resumen[nombre] = sin_dir
    return resumen, nits_sin_dir

def rellenar_direcciones(formatos, direccion, dpto, mpio):
    formatos_mod = copy.deepcopy(formatos)
    total_rellenados = 0
    for nombre, datos in formatos_mod.items():
        fdef = datos["def"]
        if "dir" not in fdef["cols"]: continue
        for reg in datos["registros"]:
            nid = reg.get("nid", "")
            if nid and nid != NM:
                if not reg.get("dir", ""):
                    reg["dir"] = direccion
                    total_rellenados += 1
                if not reg.get("dp", "") and "dp" in fdef["cols"]:
                    reg["dp"] = dpto
                if not reg.get("mp", "") and "mp" in fdef["cols"]:
                    reg["mp"] = mpio
    return formatos_mod, total_rellenados

def validar_formato(nombre, datos):
    fdef = datos["def"]
    registros = datos["registros"]
    errores = []
    fmt_code = fdef["formato"]
    conceptos_validos = CONCEPTOS_VALIDOS.get("F" + fmt_code, [])
    for reg in registros:
        fila = reg["_fila"]
        nid = reg.get("nid", "")
        td = reg.get("td", "")
        dv = reg.get("dv", "")
        if not nid:
            errores.append((fila, "nid", "error", "NIT vacio"))
            continue
        # --- Tipo documento ---
        if not td:
            td_auto = detectar_tipo_doc(nid)
            errores.append((fila, "td", "warn", "Tipo doc vacio para NIT " + nid + " → se asignara '" + td_auto + "' al generar XML"))
            td = td_auto
        elif td not in TIPOS_DOC_VALIDOS:
            errores.append((fila, "td", "error", "Tipo doc '" + td + "' invalido para NIT " + nid))
        # --- DV ---
        if td == "31":
            dv_calc = calc_dv(nid)
            if dv and dv_calc and dv != dv_calc:
                errores.append((fila, "dv", "error", "DV incorrecto NIT " + nid + ": tiene '" + dv + "', debe ser '" + dv_calc + "'"))
            elif not dv:
                errores.append((fila, "dv", "warn", "DV vacio para NIT " + nid + " → se calculara al generar XML"))
        # --- Nombres / Razón social ---
        if nid != NM:
            if es_persona_natural(td):
                if not reg.get("a1", ""):
                    if reg.get("rs", ""):
                        errores.append((fila, "a1", "warn", "Primer apellido vacio - NIT " + nid + " → se extraera de razon social"))
                    else:
                        errores.append((fila, "a1", "error", "Primer apellido vacio y sin razon social - NIT " + nid))
                if not reg.get("n1", "") and not reg.get("rs", ""):
                    errores.append((fila, "n1", "warn", "Primer nombre vacio - NIT " + nid + " → se pondra 'NN' al generar"))
            elif es_persona_juridica(td):
                if not reg.get("rs", ""):
                    nombre_partes = " ".join(filter(None, [reg.get("a1",""), reg.get("a2",""), reg.get("n1",""), reg.get("n2","")]))
                    if nombre_partes:
                        errores.append((fila, "rs", "warn", "Razon social vacia - NIT " + nid + " → se armara desde nombres"))
                    else:
                        errores.append((fila, "rs", "error", "Razon social vacia y sin nombres - NIT " + nid))
            elif es_tipo_doc_extranjero(td):
                if not reg.get("rs", "") and not reg.get("a1", ""):
                    errores.append((fila, "rs", "error", "Razon social vacia para tercero exterior - NIT " + nid))
        # --- Dirección ---
        if "dir" in fdef["cols"] and nid != NM:
            if not es_tipo_doc_extranjero(td):
                if not reg.get("dir", ""):
                    errores.append((fila, "dir", "warn", "Direccion vacia - NIT " + nid + " → se usara dir. empresa al generar"))
            # Para exterior: dir debe ir vacía, no es error
        # --- Departamento ---
        dp = reg.get("dp", "")
        if "dp" in fdef["cols"] and nid != NM and not es_tipo_doc_extranjero(td):
            if dp and dp not in DPTOS_VALIDOS:
                errores.append((fila, "dp", "warn", "Dpto '" + dp + "' no reconocido - NIT " + nid))
            elif not dp:
                errores.append((fila, "dp", "warn", "Departamento vacio - NIT " + nid + " → se usara dpto empresa"))
        # --- Municipio ---
        mp = reg.get("mp", "")
        if "mp" in fdef["cols"] and nid != NM and not es_tipo_doc_extranjero(td):
            if not mp:
                errores.append((fila, "mp", "warn", "Municipio vacio - NIT " + nid + " → se usara mpio empresa"))
        # --- País ---
        if "pais" in fdef["cols"]:
            pais = reg.get("pais", "")
            if not pais and nid != NM:
                errores.append((fila, "pais", "warn", "Pais vacio - NIT " + nid + " → se asignara al generar"))
            elif pais in ("169", "170") and es_tipo_doc_extranjero(td):
                errores.append((fila, "pais", "warn", "Pais Colombia para tercero exterior - NIT " + nid + " → se corregira"))
        # --- Concepto ---
        if "concepto" in reg and conceptos_validos:
            conc = reg.get("concepto", "")
            if conc and conc not in conceptos_validos:
                errores.append((fila, "concepto", "warn", "Concepto '" + conc + "' no esta en lista estandar del F" + fmt_code))
        # --- Valores numéricos ---
        for campo_v in fdef["campos_valor"]:
            val = reg.get(campo_v, "")
            if val:
                try:
                    v = float(val)
                    if v < 0:
                        errores.append((fila, campo_v, "warn", "Valor negativo en " + campo_v + ": " + str(v) + " - NIT " + nid))
                except:
                    errores.append((fila, campo_v, "error", "Valor no numerico en " + campo_v + ": '" + val + "' - NIT " + nid))
    return errores

def resumen_validacion(formatos):
    resultados = {}
    for nombre, datos in formatos.items():
        errores = validar_formato(nombre, datos)
        criticos = sum(1 for e in errores if e[2] == "error")
        warnings = sum(1 for e in errores if e[2] == "warn")
        resultados[nombre] = {
            "registros": len(datos["registros"]), "errores": errores,
            "criticos": criticos, "warnings": warnings, "listo": criticos == 0,
        }
    return resultados

def generar_xml_formato(nombre_hoja, datos, info_declarante, num_envio):
    fdef = datos["def"]
    registros = datos["registros"]
    if not registros: return None

    # --- Sanitizar TODOS los registros antes de generar XML ---
    registros_limpios = []
    for reg in registros:
        r_limpio = sanitizar_registro(reg, fdef, info_declarante)
        registros_limpios.append(r_limpio)

    root = Element("mas")
    root.set("xmlns", "http://www.dian.gov.co/muisca/mas")

    # --- Cabecera: asegurar que no haya campos vacíos ---
    cab = SubElement(root, "Cab")
    td_decl = info_declarante.get("td", "31")
    nit_decl = info_declarante.get("nit", "")
    dv_decl = info_declarante.get("dv", "")
    if not dv_decl and nit_decl:
        dv_decl = calc_dv(nit_decl)

    campos_cab = [
        ("CodCpt", fdef["concepto_global"]), ("Formato", fdef["formato"]),
        ("Version", fdef["version"]), ("AnoGrav", ANO_GRAVABLE),
        ("NumEnvio", str(num_envio).zfill(5)),
        ("FecEnvio", datetime.now().strftime("%Y-%m-%d")),
        ("FecIni", ANO_GRAVABLE + "-01-01"), ("FecFin", ANO_GRAVABLE + "-12-31"),
        ("NumReg", str(len(registros_limpios))),
        ("TipoDoc", td_decl),
        ("NumNit", nit_decl),
        ("DV", dv_decl),
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

    # --- Registros ---
    sec = SubElement(root, fdef["xml_tag"])
    cols = fdef["cols"]
    campos_valor = fdef["campos_valor"]
    TAG_MAP = {"concepto": "co", "td": "tdoc", "nid": "nid", "dv": "dv",
        "a1": "ape1", "a2": "ape2", "n1": "nom1", "n2": "nom2",
        "rs": "raz", "dir": "dir", "dp": "dpto", "mp": "mpio", "pais": "pais"}

    for reg in registros_limpios:
        row_el = SubElement(sec, fdef["xml_row"])
        for campo in cols:
            if campo.startswith("_"): continue
            tag = TAG_MAP.get(campo, campo)
            val = reg.get(campo, "")
            # Campos valor ya sanitizados, pero doble-check
            if campo in campos_valor:
                try: val = str(int(float(val))) if val else "0"
                except: val = "0"
            el = SubElement(row_el, tag)
            el.text = str(val) if val else ""

    xml_str = tostring(root, encoding="unicode")
    try:
        dom = parseString(xml_str)
        xml_pretty = dom.toprettyxml(indent="  ", encoding="ISO-8859-1")
        lines = xml_pretty.decode("ISO-8859-1").split("\n")
        lines[0] = '<?xml version="1.0" encoding="ISO-8859-1"?>'
        return "\n".join(lines)
    except:
        return '<?xml version="1.0" encoding="ISO-8859-1"?>\n' + xml_str

def main():
    st.set_page_config(page_title="Prevalidador XML - Exogena DIAN", page_icon="magnifier", layout="wide")

    st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .stat-box { background: white; border-radius: 8px; padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12); text-align: center; margin: 4px; }
    .stat-num { font-size: 28px; font-weight: bold; }
    .stat-label { font-size: 12px; color: #666; margin-top: 4px; }
    .ok { color: #27ae60; }
    .err { color: #e74c3c; }
    .empresa-ok { background: #d4edda; border-left: 4px solid #28a745;
                  padding: 10px; border-radius: 4px; margin: 5px 0; }
    </style>
    """, unsafe_allow_html=True)

    st.title("Prevalidador y Generador XML - Exogena DIAN")
    st.caption("Cargue el Excel, valide los datos, rellene direcciones faltantes y genere los XML para el MUISCA")

    with st.sidebar:
        st.header("Datos de la Empresa")
        st.caption("Van en el encabezado de cada XML")

        st.subheader("Identificacion")
        decl_td = st.selectbox("Tipo de persona",
                               ["31 - NIT (Persona Juridica)", "13 - CC (Persona Natural)"], index=0)
        decl_td_code = decl_td[:2]
        decl_nit = st.text_input("NIT / Cedula", placeholder="900123456")
        decl_dv = ""
        if decl_nit:
            decl_dv = calc_dv(decl_nit)
            st.caption("DV calculado: **" + decl_dv + "**")
        if decl_td_code == "31":
            decl_rs = st.text_input("Razon Social", placeholder="MI EMPRESA S.A.S")
            decl_a1 = decl_a2 = decl_n1 = decl_n2 = ""
        else:
            decl_a1 = st.text_input("Primer Apellido")
            decl_a2 = st.text_input("Segundo Apellido")
            decl_n1 = st.text_input("Primer Nombre")
            decl_n2 = st.text_input("Segundo Nombre")
            decl_rs = ""

        st.subheader("Ubicacion")
        decl_dir = st.text_input("Direccion empresa", placeholder="CRA 10 # 20-30")
        dpto_opciones = [""] + [k + " - " + v for k, v in sorted(DPTOS_VALIDOS.items())]
        dpto_sel = st.selectbox("Departamento", dpto_opciones, index=0)
        decl_dp = dpto_sel[:2] if dpto_sel else ""
        decl_mp = st.text_input("Cod. Municipio", placeholder="05001", max_chars=5)
        if decl_dp and not decl_mp:
            st.caption("El municipio empieza con " + decl_dp + "...")

        st.divider()
        st.subheader("Representante Legal")
        rep_legal_td = st.text_input("Tipo Doc", value="13", max_chars=2)
        rep_legal_nit = st.text_input("CC Rep. Legal", placeholder="1234567890")
        if rep_legal_nit:
            st.caption("DV: **" + calc_dv(rep_legal_nit) + "**")
        rep_legal_a1 = st.text_input("Primer Apellido Rep.")
        rep_legal_a2 = st.text_input("Segundo Apellido Rep.")
        rep_legal_n1 = st.text_input("Primer Nombre Rep.")
        rep_legal_n2 = st.text_input("Segundo Nombre Rep.")

        st.divider()
        st.subheader("Consecutivo DIAN")
        st.caption("Numero de envio con el que empieza. Cada formato usa un consecutivo diferente.")
        num_envio_inicio = st.number_input("Envio inicial", min_value=1, value=1, step=1)
        st.caption("Ej: si el ultimo envio fue el 3, ponga 4.")

    info_declarante = {
        "td": decl_td_code, "nit": decl_nit, "dv": decl_dv,
        "a1": decl_a1 if decl_td_code != "31" else "",
        "a2": decl_a2 if decl_td_code != "31" else "",
        "n1": decl_n1 if decl_td_code != "31" else "",
        "n2": decl_n2 if decl_td_code != "31" else "",
        "rs": decl_rs, "dir": decl_dir, "dp": decl_dp, "mp": decl_mp,
    }

    uploaded = st.file_uploader("Suba el Excel de Exogena", type=["xlsx"])

    if not uploaded:
        st.info("Suba el archivo Excel generado por la App de Exogena para comenzar.")
        datos_ok = all([decl_nit, decl_dir, decl_dp, decl_mp,
                       (decl_rs if decl_td_code == "31" else decl_a1)])
        if datos_ok:
            nombre_mostrar = decl_rs if decl_td_code == "31" else (decl_a1 + " " + decl_n1)
            st.markdown('<div class="empresa-ok">Empresa configurada: <b>' + nombre_mostrar + '</b> - NIT ' + decl_nit + '-' + decl_dv + '<br>Direccion: ' + decl_dir + ' - ' + decl_dp + ' / ' + decl_mp + '</div>', unsafe_allow_html=True)
        else:
            st.warning("Complete los datos de la empresa en la barra lateral izquierda antes de generar los XML.")
        with st.expander("Como funciona?"):
            st.markdown("""
            **1.** Complete los datos de la empresa en la barra lateral

            **2.** Suba el Excel generado por la App de Exogena

            **3.** Revise los errores

            **4.** Si hay direcciones faltantes, use el boton para rellenarlas con la direccion de la empresa

            **5.** Configure el consecutivo DIAN

            **6.** Genere los XML y carguelos al portal MUISCA
            """)
        return

    if "formatos_originales" not in st.session_state: st.session_state.formatos_originales = None
    if "formatos_trabajo" not in st.session_state: st.session_state.formatos_trabajo = None
    if "direcciones_rellenadas" not in st.session_state: st.session_state.direcciones_rellenadas = False

    file_id = uploaded.name + "_" + str(uploaded.size)
    if st.session_state.get("file_id") != file_id:
        formatos = leer_excel(uploaded)
        st.session_state.formatos_originales = formatos
        st.session_state.formatos_trabajo = copy.deepcopy(formatos)
        st.session_state.file_id = file_id
        st.session_state.direcciones_rellenadas = False

    formatos = st.session_state.formatos_trabajo
    if not formatos:
        st.error("No se encontraron hojas con formatos validos.")
        return

    # RELLENO DE DIRECCIONES
    sin_dir_resumen, nits_sin_dir = contar_sin_direccion(formatos)
    if sin_dir_resumen and not st.session_state.direcciones_rellenadas:
        total_sin = sum(sin_dir_resumen.values())
        st.warning("**" + str(total_sin) + " registros** de " + str(len(nits_sin_dir)) + " terceros no tienen direccion")
        with st.expander("Ver detalle y rellenar direcciones", expanded=True):
            for fmt, cant in sin_dir_resumen.items():
                st.markdown("- **" + fmt + "**: " + str(cant) + " registros sin direccion")
            st.divider()
            if decl_dir and decl_dp and decl_mp:
                st.markdown("**Direccion de la empresa:** " + decl_dir + " (Dpto " + decl_dp + ", Mpio " + decl_mp + ")")
                st.markdown("Se rellenaran direccion, departamento y municipio de todos los terceros que no tengan estos datos.")
                if st.button("Rellenar " + str(total_sin) + " registros con direccion de la empresa", type="primary"):
                    formatos_mod, n_rellenados = rellenar_direcciones(formatos, decl_dir, decl_dp, decl_mp)
                    st.session_state.formatos_trabajo = formatos_mod
                    st.session_state.direcciones_rellenadas = True
                    st.rerun()
            else:
                st.error("Para rellenar direcciones, primero complete la direccion, departamento y municipio en la barra lateral.")
    elif st.session_state.direcciones_rellenadas:
        st.success("Direcciones ya rellenadas con datos de la empresa")
        if st.button("Deshacer relleno de direcciones"):
            st.session_state.formatos_trabajo = copy.deepcopy(st.session_state.formatos_originales)
            st.session_state.direcciones_rellenadas = False
            st.rerun()

    st.divider()

    # VALIDACION
    resultados = resumen_validacion(formatos)
    total_regs = sum(r["registros"] for r in resultados.values())
    total_criticos = sum(r["criticos"] for r in resultados.values())
    total_warnings = sum(r["warnings"] for r in resultados.values())
    formatos_listos = sum(1 for r in resultados.values() if r["listo"])
    total_formatos = len(resultados)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown('<div class="stat-box"><div class="stat-num">' + str(total_formatos) + '</div><div class="stat-label">Formatos</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="stat-box"><div class="stat-num">' + "{:,}".format(total_regs) + '</div><div class="stat-label">Registros</div></div>', unsafe_allow_html=True)
    with c3:
        color = "ok" if total_criticos == 0 else "err"
        st.markdown('<div class="stat-box"><div class="stat-num ' + color + '">' + str(total_criticos) + '</div><div class="stat-label">Errores</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="stat-box"><div class="stat-num ok">' + str(formatos_listos) + '/' + str(total_formatos) + '</div><div class="stat-label">Listos</div></div>', unsafe_allow_html=True)

    st.subheader("Estado por formato")
    tabla_data = []
    for nombre, res in resultados.items():
        estado = "Listo" if res["listo"] else (str(res["criticos"]) + " errores")
        tabla_data.append({"Formato": nombre, "Registros": res["registros"],
            "Errores": res["criticos"], "Advertencias": res["warnings"], "Estado": estado})
    st.dataframe(pd.DataFrame(tabla_data), use_container_width=True, hide_index=True)

    formatos_con_errores = {k: v for k, v in resultados.items() if v["errores"]}
    if not formatos_con_errores:
        st.success("Sin errores criticos! Listo para generar XML.")
    else:
        if total_criticos == 0 and total_warnings > 0:
            st.success("Sin errores criticos. Las **" + str(total_warnings) + " advertencias** se corregiran automaticamente al generar el XML.")
        elif total_criticos > 0:
            st.error("Hay **" + str(total_criticos) + " errores criticos** que deben corregirse en el Excel antes de generar.")
            if total_warnings > 0:
                st.info("Las " + str(total_warnings) + " advertencias se corregiran automaticamente al generar.")
        st.subheader("Detalle de errores")
        for nombre, res in formatos_con_errores.items():
            tipo_icono = "error" if res["criticos"] > 0 else "warn"
            with st.expander(nombre + " - " + str(res["criticos"]) + " errores, " + str(res["warnings"]) + " advertencias", expanded=(res["criticos"] > 0)):
                errores_por_campo = defaultdict(list)
                for fila, campo, tipo, msg in res["errores"]:
                    errores_por_campo[campo].append((fila, tipo, msg))
                for campo, errs in errores_por_campo.items():
                    st.markdown("**Campo: " + campo + "** (" + str(len(errs)) + " problemas)")
                    for fila, tipo, msg in errs[:10]:
                        icono = "❌" if tipo == "error" else "⚠️"
                        st.markdown("  " + icono + " Fila " + str(fila) + ": " + msg)
                    if len(errs) > 10:
                        st.caption("  ... y " + str(len(errs) - 10) + " mas")

    st.divider()
    st.subheader("Datos de la empresa para XML")
    errores_decl = []
    if not decl_nit: errores_decl.append("NIT vacio")
    elif not decl_nit.isdigit(): errores_decl.append("NIT debe ser numerico")
    if decl_td_code == "31" and not decl_rs: errores_decl.append("Razon social vacia")
    if decl_td_code == "13" and not decl_a1: errores_decl.append("Primer apellido vacio")
    if not decl_dir: errores_decl.append("Direccion vacia")
    if not decl_dp: errores_decl.append("Departamento vacio")
    if not decl_mp: errores_decl.append("Municipio vacio")

    if errores_decl:
        for e in errores_decl: st.error("❌ " + e)
        st.warning("Complete los datos en la barra lateral izquierda")
    else:
        nombre_mostrar = decl_rs if decl_td_code == "31" else (decl_a1 + " " + decl_n1)
        st.markdown('<div class="empresa-ok"><b>' + nombre_mostrar + '</b> - NIT ' + decl_nit + '-' + decl_dv + '<br>Direccion: ' + decl_dir + ' - Dpto ' + decl_dp + ', Mpio ' + decl_mp + '<br>Consecutivo inicial: <b>' + str(num_envio_inicio) + '</b></div>', unsafe_allow_html=True)

    formatos_disponibles = [f for f in ORDEN_FORMATOS if f in formatos]
    if not errores_decl and formatos_disponibles:
        with st.expander("Ver asignacion de consecutivos"):
            consec_data = []
            n = num_envio_inicio
            for f in formatos_disponibles:
                fmt_num = FORMATO_DEFS[f]["formato"]
                consec_data.append({"Formato": f, "Codigo": fmt_num,
                    "Archivo XML": fmt_num + "_" + ANO_GRAVABLE + "_" + str(n).zfill(5) + ".xml", "Envio #": n})
                n += 1
            st.dataframe(pd.DataFrame(consec_data), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Generar XML para DIAN")
    puede_generar = (total_criticos == 0 and len(errores_decl) == 0)
    puede_forzar = (len(errores_decl) == 0 and total_criticos > 0)
    if puede_generar: st.success("Todo listo para generar los XML")
    elif puede_forzar: st.warning("Hay " + str(total_criticos) + " errores criticos. Puede forzar la generacion.")
    elif errores_decl: st.error("Complete los datos de la empresa primero.")

    formatos_seleccionados = st.multiselect("Formatos a generar", formatos_disponibles, default=formatos_disponibles)
    generar = False
    if puede_generar: generar = st.button("Generar XML", type="primary", use_container_width=True)
    elif puede_forzar: generar = st.button("Generar con errores", type="secondary", use_container_width=True)

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
                filename = fmt_num + "_" + ANO_GRAVABLE + "_" + str(num_envio).zfill(5) + ".xml"
                xmls_generados[filename] = xml_content
                num_envio += 1
            progress.progress((i + 1) / len(formatos_seleccionados), text="Generando " + nombre_hoja + "...")
        progress.empty()

        if xmls_generados:
            st.success(str(len(xmls_generados)) + " archivos XML generados")
            tabla_xml = []
            for fn, content in xmls_generados.items():
                tabla_xml.append({"Archivo": fn, "Tamano": "{:,}".format(len(content)) + " bytes",
                    "Envio #": fn.split("_")[-1].replace(".xml", "")})
            st.dataframe(pd.DataFrame(tabla_xml), use_container_width=True, hide_index=True)

            st.markdown("**Descargar individual:**")
            cols_dl = st.columns(min(len(xmls_generados), 4))
            for i, (fn, content) in enumerate(xmls_generados.items()):
                with cols_dl[i % len(cols_dl)]:
                    st.download_button(fn, data=content.encode("ISO-8859-1"),
                        file_name=fn, mime="application/xml", use_container_width=True)

            st.divider()
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for fn, content in xmls_generados.items():
                    zf.writestr(fn, content.encode("ISO-8859-1"))
            zip_buffer.seek(0)
            st.download_button("Descargar TODOS los XML (ZIP)", data=zip_buffer,
                file_name="Exogena_XML_" + ANO_GRAVABLE + "_" + decl_nit + ".zip",
                mime="application/zip", type="primary", use_container_width=True)

            with st.expander("Previsualizar XML"):
                xml_preview = st.selectbox("Seleccionar archivo", list(xmls_generados.keys()))
                if xml_preview:
                    st.code(xmls_generados[xml_preview][:5000], language="xml")
                    if len(xmls_generados[xml_preview]) > 5000:
                        st.caption("... primeros 5,000 de " + "{:,}".format(len(xmls_generados[xml_preview])) + " chars")

    st.divider()
    with st.expander("Analisis de calidad de datos"):
        todos_errores = []
        for nombre, res in resultados.items():
            for e in res["errores"]: todos_errores.append((nombre,) + e)
        if todos_errores:
            tipos_error = defaultdict(int)
            for row in todos_errores: tipos_error[row[2]] += 1
            st.markdown("**Errores por campo:**")
            st.dataframe(pd.DataFrame([{"Campo": k, "Cantidad": v} for k, v in sorted(tipos_error.items(), key=lambda x: -x[1])]), use_container_width=True, hide_index=True)
            nits_errores = defaultdict(int)
            for row in todos_errores:
                nit_match = re.search(r'NIT (\d+)', row[4])
                if nit_match: nits_errores[nit_match.group(1)] += 1
            if nits_errores:
                st.markdown("**Top 10 terceros con problemas:**")
                top_nits = sorted(nits_errores.items(), key=lambda x: -x[1])[:10]
                st.dataframe(pd.DataFrame([{"NIT": k, "Errores": v} for k, v in top_nits]), use_container_width=True, hide_index=True)
        else:
            st.success("Sin errores. Datos limpios!")

if __name__ == "__main__":
    main()

