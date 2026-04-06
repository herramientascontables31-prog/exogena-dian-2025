"""
EXÓGENA DIAN — App Principal
Página de inicio con navegación a los módulos.
"""
import streamlit as st

st.set_page_config(
    page_title="Exógena DIAN AG 2026",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
.big-title { font-size: 42px; font-weight: bold; color: #1a5276; margin-bottom: 0; }
.subtitle { font-size: 18px; color: #5d6d7e; margin-top: 0; }
.card {
    background: white; border-radius: 12px; padding: 30px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin: 10px 0; transition: transform 0.2s;
    border-left: 5px solid #2c3e50;
}
.card:hover { transform: translateY(-2px); }
.card h3 { margin-top: 0; color: #1a5276; }
.card p { color: #5d6d7e; }
.step { display: inline-block; background: #2c3e50; color: white;
        border-radius: 50%; width: 30px; height: 30px; text-align: center;
        line-height: 30px; font-weight: bold; margin-right: 10px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-title">📊 Exógena DIAN</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Año Gravable 2026 — Generación y validación de información exógena</p>',
            unsafe_allow_html=True)

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="card">
        <h3>📋 Paso 1 — Generar Formatos</h3>
        <p>Suba el balance de prueba con terceros y genere automáticamente
        todos los formatos de exógena en Excel:</p>
        <p>F1001, F1003, F1005, F1006, F1007, F1008, F1009, F1010, F1012, F2276</p>
        <p>Incluye dashboard de confrontación Balance vs Exógena.</p>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/1_Generar_Formatos.py", label="Ir a Generar Formatos →", icon="📋")

with col2:
    st.markdown("""
    <div class="card">
        <h3>🔍 Paso 2 — Prevalidar y Generar XML</h3>
        <p>Suba el Excel generado en el Paso 1.
        El prevalidador revisa todos los campos, muestra errores
        y genera los XML listos para cargar al MUISCA.</p>
        <p>Reemplaza el prevalidador de escritorio de la DIAN.</p>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/2_Prevalidador_XML.py", label="Ir a Prevalidador XML →", icon="🔍")

st.divider()

st.markdown("""
### Flujo de trabajo

<span class="step">1</span> **Exporte** el balance de prueba con terceros de su software contable (Excel)

<span class="step">2</span> **Genere** los formatos de exógena con el módulo **Generar Formatos**

<span class="step">3</span> **Revise** el Excel — corrija terceros sin datos, valide los cruces con el balance

<span class="step">4</span> **Valide** con el **Prevalidador XML** — complete datos del declarante

<span class="step">5</span> **Descargue** los XML y **cárguelos** al portal MUISCA de la DIAN
""", unsafe_allow_html=True)

st.divider()
st.caption("Versión 2.0 — Febrero 2026 | Solo dependencias: streamlit, pandas, openpyxl")
