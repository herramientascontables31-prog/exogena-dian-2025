# Cambios realizados y guía de lanzamiento — ExógenaDIAN

## ✅ Cambios aplicados

### 1. Excel robusto (ya no se rompe al editarlo)

**Archivo:** `2_Prevalidador_XML.py`

El prevalidador ahora lee el Excel **por nombre de columna**, no por posición. Esto significa que si alguien agrega, elimina o reordena columnas en el Excel, el sistema seguirá funcionando correctamente siempre que los headers estén presentes.

- Se agregó un diccionario `HEADER_ALIASES` con 80+ variaciones de nombres de columna aceptadas (por ejemplo, acepta "Tipo Doc", "Tipo Documento", "tdoc", "tipo id")
- Si los headers no se reconocen, cae a modo de compatibilidad por posición (como antes)
- Se corrigió un **bug crítico**: las columnas 16 y 17 del F1001 estaban invertidas (IVA No Ded y RetFte Renta)

### 2. Links funcionando

**Archivo:** `index.html`

- Las tarjetas de herramientas ahora son enlaces clickeables:
  - **Retención en la Fuente** → `retencion350.html`
  - **Conciliación Bancaria** → `conciliacion.html`
  - **Exógena** → `precios.html` (página de precios)
- Se agregó menú hamburguesa para móvil (antes los links del nav desaparecían)

### 3. IVA, Renta y Estados Financieros como "Próximamente"

**Archivo:** `index.html`

- Las 3 herramientas que aún no existen se muestran con badge "Pronto" y opacidad reducida
- Se actualizó el footer para reflejar esto
- El stat del hero se cambió de "4 herramientas gratis" a "2 herramientas gratis"

### 4. Botón de Contratar

**Archivo:** `index.html`

- Se agregó CSS para estilizar los botones de Wompi dentro de las tarjetas de precio
- Los botones ahora tienen el estilo verde del sitio, bordes redondeados y hover
- Se redujo el tamaño del botón "Contratar →" en el nav para que no domine visualmente

### 5. Botones de pago (Wompi)

**Archivo:** `index.html`

- Se agregaron botones de fallback "Contratar por WhatsApp →" que aparecen si Wompi no carga después de 5 segundos
- Se mejoró el CSS de los botones renderizados por Wompi
- **⚠️ ACCIÓN PENDIENTE:** Estás usando la llave de **prueba** (`pub_test_...`). Para pagos reales necesitas la llave de **producción**. Ver sección "Pasos para lanzar" abajo.

### 6. XML corregido

**Archivo:** `2_Prevalidador_XML.py`

Tres correcciones importantes:

**a) Nombre del archivo:** Ahora usa la convención DIAN:
```
Dmuisca_CCFFFFFVVYYYYNNNNNNNN.xml
```
Ejemplo: `Dmuisca_010100110202500000001.xml` (F1001, versión 10, año 2025, envío 1)

**b) Estructura XML:** Se corrigió el namespace para que coincida con lo que espera el MUISCA:
```xml
<mas xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
     xsi:noNamespaceSchemaLocation="../xsd/1001.xsd">
```

**c) Bloqueo de generación con errores:** Se eliminó el botón "Generar con errores". Ahora es obligatorio corregir todos los errores críticos antes de generar XML, evitando que se suban archivos rechazados al MUISCA.

---

## ⚡ Pasos para lanzar

### Paso 1: Llave de producción Wompi

En tu panel de Wompi (comercios.wompi.co):
1. Ve a **Configuración** → **Llaves de API**
2. Copia tu **llave pública de producción** (empieza con `pub_prod_...`)
3. En el archivo `index.html`, busca y reemplaza TODAS las ocurrencias de:
   ```
   pub_test_ocKLD2EUwi1h0QHmcOCkXJc2p41i5hgN
   ```
   por tu llave de producción `pub_prod_...`

### Paso 2: Crear correo profesional

Tienes varias opciones según tu presupuesto:

| Opción | Precio/mes | Cómo |
|--------|-----------|------|
| **Zoho Mail** | Gratis (1 usuario) | zoho.com/mail → registrar dominio exogenadian.com |
| **Google Workspace** | ~$6 USD | workspace.google.com → agregar dominio |
| **ImprovMX** | Gratis (reenvío) | improvmx.com → reenvía info@exogenadian.com a tu Gmail |

**Recomendación para empezar:** ImprovMX (gratis). Configuras que `info@exogenadian.com` reenvíe a tu Gmail personal. Necesitas agregar estos registros DNS en Cloudflare:

```
Tipo: MX  |  Nombre: @  |  Valor: mx1.improvmx.com  |  Prioridad: 10
Tipo: MX  |  Nombre: @  |  Valor: mx2.improvmx.com  |  Prioridad: 20
```

### Paso 3: Verificar estructura de archivos en Cloudflare

Tu sitio debe tener esta estructura:
```
/index.html              ← Página principal (actualizada)
/retencion350.html       ← Calculadora retención
/conciliacion.html       ← Conciliación bancaria
/gracias.html            ← Página post-pago
```

### Paso 4: Probar el flujo completo

1. Abre la página en incógnito
2. Haz clic en cada enlace de herramienta → debe abrir la página correcta
3. Haz clic en "Contratar →" → debe hacer scroll a precios
4. Prueba un pago de prueba con Wompi (con llave test)
5. Verifica que la página de gracias cargue con el botón de WhatsApp
6. Una vez todo funcione, cambia a la llave de producción
