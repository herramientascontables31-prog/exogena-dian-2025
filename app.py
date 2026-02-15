import streamlit as st
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from collections import defaultdict
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="Exógena DIAN 2025", page_icon="📊", layout="wide")

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

def safe_num(v):
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").replace("$", "").replace(" ", ""))
    except:
        return 0.0

def safe_str(v):
    if v is None:
        return ""
    return str(v).strip()

def en_rango(cta, d, h):
    n = len(d)
    return cta[:n] >= d and cta[:n] <= h

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
    ("5004", "5110", "5139", True), ("5005", "5120", "5120", True),
    ("5005", "5220", "5220", True), ("5011", "5230", "5230", True),
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

def concepto_1001(cta):
    if en_rango(cta, "5105", "5105"):
        sc = cta[4:6] if len(cta) >= 6 else cta[4:] if len(cta) > 4 else ""
        for conc, subs in PARAM_1001_NOMINA_SUB.items():
            if sc in subs:
                return conc, True
        return "5016", True
    for conc, d, h, ded in PARAM_1001_RANGOS:
        if en_rango(cta, d, h):
            return conc, ded
    if cta[:2] in ("51", "52", "53"):
        return "5016", True
    return None, True

def buscar_concepto(cta, params):
    for c, d, h in params:
        if en_rango(cta, d, h):
            return c
    return ""

# === PROCESAMIENTO PRINCIPAL ===
def procesar_balance(df_balance):
    """Procesa el balance y retorna un workbook con todos los formatos"""

    # Leer balance
    bal = []
    for _, row in df_balance.iterrows():
        cta = safe_str(row.iloc[0])
        nit = safe_str(row.iloc[3])
        if not cta or not nit:
            continue
        bal.append({
            'cta': cta,
            'nom_cta': safe_str(row.iloc[1]),
            'td': safe_str(row.iloc[2]) if len(row) > 2 else "31",
            'nit': nit,
            'razon': safe_str(row.iloc[4]) if len(row) > 4 else "",
            'deb': safe_num(row.iloc[5]) if len(row) > 5 else 0,
            'cred': safe_num(row.iloc[6]) if len(row) > 6 else 0,
            'saldo': safe_num(row.iloc[7]) if len(row) > 7 else 0,
            'base': safe_num(row.iloc[9]) if len(row) > 9 else 0,
            'ret': safe_num(row.iloc[11]) if len(row) > 11 else 0,
        })

    # Directorio
    direc = {}
    for f in bal:
        if f['nit'] not in direc:
            td = f['td'] if f['td'] else "31"
            r = f['razon']
            d = {'td': td, 'dv': calc_dv(f['nit']),
                 'a1': '', 'a2': '', 'n1': '', 'n2': '',
                 'rs': '', 'dir': '', 'dp': '', 'mp': ''}
            if td == "13":
                p = r.split()
                if len(p) >= 1: d['a1'] = p[0]
                if len(p) >= 2: d['a2'] = p[1]
                if len(p) >= 3: d['n1'] = p[2]
                if len(p) >= 4: d['n2'] = ' '.join(p[3:])
            else:
                d['rs'] = r
            direc[f['nit']] = d
    direc[NM] = {'td': TDM, 'dv': '', 'a1': '', 'a2': '', 'n1': '', 'n2': '',
                 'rs': 'CUANTIAS MENORES', 'dir': '', 'dp': '', 'mp': ''}

    def t(nit):
        return direc.get(nit, {'td': '31', 'dv': calc_dv(nit),
                                'a1': '', 'a2': '', 'n1': '', 'n2': '',
                                'rs': nit, 'dir': '', 'dp': '', 'mp': ''})

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
        for v in [d['td'], nit, d['dv'], d['a1'], d['a2'], d['n1'], d['n2'], d['rs'], d['dir'], d['dp'], d['mp']]:
            ws.cell(fila, c).value = v
            c += 1
        if con_pais:
            ws.cell(fila, c).value = "169"
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

    # ========== F1001 ==========
    h = ["Concepto", "Tipo Doc", "No ID", "DV", "Apellido1", "Apellido2", "Nombre1", "Nombre2",
         "Razon Social", "Direccion", "Dpto", "Mpio", "Pais", "Pago Deducible", "Pago No Deducible",
         "IVA Ded", "IVA No Ded", "Ret Fte Renta", "Ret Fte Asumida", "Ret IVA R.Comun", "Ret IVA No Dom"]
    ws = nueva_hoja("F1001 Pagos", h)

    dic = defaultdict(lambda: [0.0] * 5)
    for f in bal:
        conc, ded = concepto_1001(f['cta'])
        if not conc or conc == "5001":
            continue
        k = (conc, f['nit'])
        if ded:
            dic[k][0] += f['deb']
        else:
            dic[k][1] += f['deb']
        dic[k][2] += f['ret']

    final = {}
    menores = defaultdict(lambda: [0.0] * 5)
    for (c, n), v in dic.items():
        if v[0] + v[1] < C3UVT and v[2] == 0:
            for i in range(5):
                menores[(c, NM)][i] += v[i]
        else:
            final[(c, n)] = v
    for k, v in menores.items():
        if k not in final:
            final[k] = v

    fila = 2
    for (conc, nit), v in sorted(final.items()):
        ws.cell(fila, 1).value = conc
        escribir_tercero(ws, fila, 2, nit, True)
        ws.cell(fila, 14).value = int(v[0])
        ws.cell(fila, 15).value = int(v[1])
        for c in [16, 17, 19, 20, 21]:
            ws.cell(fila, c).value = 0
        ws.cell(fila, 18).value = int(v[2])
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
        conc = buscar_concepto(f['cta'], PARAM_1003)
        if not conc:
            continue
        dic3[(conc, f['nit'])][0] += f['base']
        dic3[(conc, f['nit'])][1] += f['cred']

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
        conc = buscar_concepto(f['cta'], PARAM_1007)
        if not conc:
            continue
        dic7[(conc, f['nit'])] += f['cred']

    final7 = {}
    men7 = defaultdict(float)
    for (c, n), v in dic7.items():
        if v < C3UVT:
            men7[(c, NM)] += v
        else:
            final7[(c, n)] = v
    for k, v in men7.items():
        if k not in final7:
            final7[k] = v

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
        conc = buscar_concepto(f['cta'], PARAM_1008)
        if not conc:
            continue
        s = abs(f['saldo'])
        if s == 0:
            continue
        dic8[(conc, f['nit'])] += s

    final8 = {}
    men8 = defaultdict(float)
    for (c, n), v in dic8.items():
        if v < C12UVT:
            men8[(c, NM)] += v
        else:
            final8[(c, n)] = v
    for k, v in men8.items():
        if k not in final8:
            final8[k] = v

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
        conc = buscar_concepto(f['cta'], PARAM_1009)
        if not conc:
            continue
        s = abs(f['saldo'])
        if s == 0:
            continue
        dic9[(conc, f['nit'])] += s

    final9 = {}
    men9 = defaultdict(float)
    for (c, n), v in dic9.items():
        if v < C12UVT:
            men9[(c, NM)] += v
        else:
            final9[(c, n)] = v
    for k, v in men9.items():
        if k not in final9:
            final9[k] = v

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
        if not en_rango(f['cta'], "5105", "5105") or f['deb'] == 0:
            continue
        nit = f['nit']
        sc = f['cta'][4:6] if len(f['cta']) >= 6 else ""
        if sc in ("06", "07", "08", "09", "10", "15"):
            dic26[nit][0] += f['deb']
        elif sc in ("27",):
            dic26[nit][10] += f['deb']
        elif sc in ("30", "33"):
            dic26[nit][8] += f['deb']
        elif sc in ("36",):
            dic26[nit][10] += f['deb']
        elif sc in ("39",):
            dic26[nit][7] += f['deb']
        elif sc in ("42", "45"):
            dic26[nit][10] += f['deb']
        elif sc in ("01", "03", "05"):
            d = t(nit)
            if d['td'] == "13":
                dic26[nit][3] += f['deb']
        elif sc not in ("02", "04", "68", "72", "75"):
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
        ws.cell(fila, 1).value = d['td']
        ws.cell(fila, 2).value = nit
        ws.cell(fila, 3).value = d['dv']
        ws.cell(fila, 4).value = d['a1']
        ws.cell(fila, 5).value = d['a2']
        ws.cell(fila, 6).value = d['n1']
        ws.cell(fila, 7).value = d['n2']
        ws.cell(fila, 8).value = d['dir']
        ws.cell(fila, 9).value = d['dp']
        ws.cell(fila, 10).value = d['mp']
        ws.cell(fila, 11).value = "169"
        for i in range(19):
            ws.cell(fila, 12 + i).value = int(v[i])
            ws.cell(fila, 12 + i).number_format = '#,##0'
        zebra(ws, fila)
        fila += 1
    resultados['F2276 Rentas Trabajo'] = len(dic26)

    # ========== RESUMEN ==========
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
    wsr['A7'] = "Formato"
    wsr['B7'] = "Registros"
    wsr['A7'].font = Font(bold=True)
    wsr['B7'].font = Font(bold=True)
    row = 8
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

    return wb, resultados, len(bal), len(direc)


# === INTERFAZ ===
st.markdown('<p class="main-header">📊 Exógena DIAN — AG 2025</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Genera automáticamente los formatos de información exógena a partir del balance de prueba por tercero</p>', unsafe_allow_html=True)

st.divider()

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 📁 Sube el Balance de Prueba por Tercero")
    st.markdown("""
    El archivo Excel debe tener esta estructura desde la **fila de datos** (puede tener encabezados arriba):

    | Col A | Col B | Col C | Col D | Col E | Col F | Col G | Col H |
    |-------|-------|-------|-------|-------|-------|-------|-------|
    | Cuenta | Nombre | Tipo Doc | NIT | Razón Social | Débito | Crédito | Saldo |

    Columnas opcionales: I=Centro Costo, J=Base Gravable, K=Tarifa Ret, L=Valor Retención
    """)

    uploaded_file = st.file_uploader("Selecciona el archivo Excel", type=['xlsx', 'xls', 'csv'])

with col2:
    st.markdown("### ⚙️ Configuración")
    fila_encabezado = st.number_input("Fila del encabezado", min_value=1, max_value=20, value=3,
                                       help="Fila donde están los títulos de columna (ej: 1, 3)")
    nombre_hoja = st.text_input("Nombre de la hoja (dejar vacío = primera hoja)", value="",
                                 help="Si tu archivo tiene varias hojas, escribe el nombre de la del balance")

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

        st.divider()

        if st.button("🚀 PROCESAR EXÓGENA", type="primary", use_container_width=True):
            with st.spinner("Procesando formatos..."):
                wb, resultados, n_filas, n_terceros = procesar_balance(df)

            st.markdown('<div class="success-box">', unsafe_allow_html=True)
            st.markdown("### ✅ Procesamiento completado")
            st.markdown('</div>', unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            c1.metric("Filas procesadas", f"{n_filas:,}")
            c2.metric("Terceros identificados", f"{n_terceros:,}")
            c3.metric("Registros generados", f"{sum(resultados.values()):,}")

            st.markdown("### 📋 Resultados por formato")
            cols = st.columns(5)
            for i, (nombre, n) in enumerate(resultados.items()):
                with cols[i % 5]:
                    st.metric(nombre.split(" ", 1)[0], f"{n} reg")

            # Generar descarga
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
