/**
 * ═══════════════════════════════════════════════════════════
 * ExógenaDIAN — Apps Script Backend (Fase 2.1)
 * ═══════════════════════════════════════════════════════════
 *
 * Endpoints:
 *   ?action=generateKey&transactionId=X&ref=Y  → Verifica pago Wompi y genera clave
 *   ?action=validateKey&key=X&device=FP         → Valida clave PRO (privado)
 *   ?action=validateEmail&email=X&device=FP     → Valida por email (público)
 *   ?action=wompiSignature&ref=X&amount=Y       → Genera firma de integridad Wompi
 *
 * Configurar:
 *   1. Pegar este código en Google Apps Script
 *   2. Deploy → Manage deployments → Edit → New version → Deploy
 *   3. Trigger diario: expirarClaves (ya configurado)
 * ═══════════════════════════════════════════════════════════
 */

// ── CONFIGURACIÓN ──
// ⚠️ Las credenciales se leen de PropertiesService (Script Properties).
//   Configurar en: Apps Script → ⚙️ Project Settings → Script Properties:
//     WOMPI_PRIVATE_KEY      = tu clave privada de Wompi producción
//     WOMPI_INTEGRITY_SECRET = secreto de integridad Wompi (Dashboard → Desarrolladores)
//     SPREADSHEET_ID         = ID de la hoja de Google Sheets
const WOMPI_PRIVATE_KEY = PropertiesService.getScriptProperties().getProperty('WOMPI_PRIVATE_KEY');
const WOMPI_INTEGRITY_SECRET = PropertiesService.getScriptProperties().getProperty('WOMPI_INTEGRITY_SECRET');
const SPREADSHEET_ID = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
const SHEET_NAME = 'Claves';
const MONTO_MINIMO_COP = 1990000; // $19,900 en centavos
const DIAS_VIGENCIA_MENSUAL = 30;
const DIAS_VIGENCIA_ANUAL = 365;
const MAX_DISPOSITIVOS = 2;
const EMAIL_REMINDER_DAYS = 3;

// ── PLANES ──
// Prefijo de referencia → tipo de plan
// M-xxx  = PRO mensual (sin Escuela)
// PE-xxx = PRO + Escuela mensual
// A-xxx  = PRO Anual (incluye Escuela gratis)
// ADMIN  = Acceso total (admin interno)
// Sin prefijo (legacy) = PRO mensual sin Escuela
function detectarPlan(ref) {
  ref = String(ref || '').trim().toUpperCase();
  if (ref === 'ADMIN')            return { planType: 'pro-anual',    dias: DIAS_VIGENCIA_ANUAL,   escuela: true };
  if (ref.indexOf('PE-') === 0)   return { planType: 'pro+escuela', dias: DIAS_VIGENCIA_MENSUAL, escuela: true };
  if (ref.indexOf('A-') === 0)    return { planType: 'pro-anual',    dias: DIAS_VIGENCIA_ANUAL,   escuela: true };
  return                                  { planType: 'pro',           dias: DIAS_VIGENCIA_MENSUAL, escuela: false };
}

// ── ENDPOINT PRINCIPAL ──
function doGet(e) {
  const action = e.parameter.action || 'generateKey';
  let result;

  try {
    switch (action) {
      case 'generateKey':
        result = handleGenerateKey(e.parameter);
        break;
      case 'validateKey':
        result = handleValidateKey(e.parameter);
        break;
      case 'validateEmail':
        result = handleValidateEmail(e.parameter);
        break;
      case 'sendAlert':
        result = handleSendAlert(e.parameter);
        break;
      case 'wompiSignature':
        result = handleWompiSignature(e.parameter);
        break;
      case 'newsletter':
        result = handleNewsletter(e.parameter);
        break;
      default:
        result = { success: false, error: 'Acción no válida' };
    }
  } catch (err) {
    result = { success: false, error: err.message };
  }

  return ContentService
    .createTextOutput(JSON.stringify(result))
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  return doGet(e);
}

// ═══════════════════════════════════════════════════════════
// 2.1 — GENERAR CLAVE (con LockService para evitar race condition)
// ═══════════════════════════════════════════════════════════
function handleGenerateKey(params) {
  const transactionId = params.transactionId;
  const ref = params.ref || '';

  if (!transactionId) {
    return { success: false, error: 'Falta transactionId' };
  }

  // Lock para evitar que dos requests simultáneos generen dos claves
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(15000); // Espera máximo 15 segundos
  } catch (e) {
    return { success: false, error: 'Servidor ocupado, intenta de nuevo' };
  }

  try {
    var sheet = getSheet();

    // Idempotente: si ya existe clave para esta transacción, devolverla
    var existente = buscarPorTransaccion(sheet, transactionId);
    if (existente) {
      return { success: true, clave: existente.clave, mensaje: 'Clave ya generada previamente' };
    }

    // Verificar pago con Wompi API
    var txData = verificarTransaccionWompi(transactionId);
    if (!txData.valid) {
      return { success: false, error: txData.reason };
    }

    // Detectar plan desde la referencia
    var plan = detectarPlan(ref);

    // Generar clave única
    var clave = generarClaveUnica(sheet);
    var hoy = new Date();
    var vencimiento = new Date(hoy);
    vencimiento.setDate(vencimiento.getDate() + plan.dias);

    // Escribir en el Sheet (columnas A-J)
    sheet.appendRow([
      clave,                                                              // A: Clave
      Utilities.formatDate(hoy, 'America/Bogota', 'yyyy-MM-dd'),         // B: FechaCompra
      'activo',                                                           // C: Estado
      transactionId,                                                      // D: TransactionId
      ref,                                                                // E: Reference
      txData.email || '',                                                 // F: Email
      Utilities.formatDate(vencimiento, 'America/Bogota', 'yyyy-MM-dd'), // G: FechaVencimiento
      0,                                                                  // H: NumDispositivos
      '',                                                                 // I: Dispositivos
      ''                                                                  // J: ReminderSent
    ]);

    return {
      success: true,
      clave: clave,
      expiry: Utilities.formatDate(vencimiento, 'America/Bogota', 'yyyy-MM-dd'),
      daysLeft: plan.dias,
      planType: plan.planType,
      escuela: plan.escuela
    };
  } finally {
    lock.releaseLock();
  }
}

// ═══════════════════════════════════════════════════════════
// 2.2 — VALIDAR CLAVE (endpoint privado)
// ═══════════════════════════════════════════════════════════
function handleValidateKey(params) {
  var key = params.key;
  var device = params.device || '';

  if (!key) {
    return { success: false, valid: false, reason: 'Falta clave' };
  }

  var sheet = getSheet();
  var data = sheet.getDataRange().getValues();

  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    var clave = String(row[0]).trim();

    if (clave !== key) continue;

    var estado = String(row[2]).trim().toLowerCase();
    var ref = String(row[4]).trim();
    var fechaVenc = row[6];
    var numDisp = Number(row[7]) || 0;
    var dispositivos = String(row[8]).trim();
    var plan = detectarPlan(ref);

    // Verificar estado
    if (estado === 'cancelado') {
      return { success: true, valid: false, reason: 'Clave cancelada' };
    }

    // Verificar expiración
    var hoy = new Date();
    var venc = new Date(fechaVenc);
    if (hoy > venc) {
      if (estado !== 'expirado') {
        sheet.getRange(i + 1, 3).setValue('expirado');
      }
      return { success: true, valid: false, reason: 'Clave expirada', expiry: Utilities.formatDate(venc, 'America/Bogota', 'yyyy-MM-dd') };
    }

    // Verificar/registrar dispositivo
    if (device) {
      var dispList = dispositivos ? dispositivos.split('|') : [];

      if (dispList.indexOf(device) === -1) {
        if (numDisp >= MAX_DISPOSITIVOS) {
          return {
            success: true,
            valid: false,
            reason: 'Límite de dispositivos alcanzado (' + MAX_DISPOSITIVOS + ')',
            expiry: Utilities.formatDate(venc, 'America/Bogota', 'yyyy-MM-dd')
          };
        }
        dispList.push(device);
        sheet.getRange(i + 1, 8).setValue(dispList.length);
        sheet.getRange(i + 1, 9).setValue(dispList.join('|'));
      }
    }

    var diasRestantes = Math.ceil((venc - hoy) / (1000 * 60 * 60 * 24));

    return {
      success: true,
      valid: true,
      reason: 'Clave activa',
      daysLeft: diasRestantes,
      expiry: Utilities.formatDate(venc, 'America/Bogota', 'yyyy-MM-dd'),
      planType: plan.planType,
      escuela: plan.escuela
    };
  }

  return { success: true, valid: false, reason: 'Clave no encontrada' };
}

// ═══════════════════════════════════════════════════════════
// 2.3 — VALIDAR POR EMAIL (busca la suscripción activa más reciente)
// ═══════════════════════════════════════════════════════════
function handleValidateEmail(params) {
  var email = (params.email || '').trim().toLowerCase();
  var device = params.device || '';

  if (!email) {
    return { success: false, valid: false, reason: 'Falta email' };
  }

  var sheet = getSheet();
  var data = sheet.getDataRange().getValues();
  var hoy = new Date();

  // Buscar la mejor suscripción activa para este email
  // Prioridad: 1) incluye escuela, 2) vencimiento más lejano
  var bestRow = -1;
  var bestVenc = null;
  var bestEscuela = false;

  for (var i = 1; i < data.length; i++) {
    var rowEmail = String(data[i][5]).trim().toLowerCase();
    if (rowEmail !== email) continue;

    var estado = String(data[i][2]).trim().toLowerCase();
    if (estado === 'cancelado') continue;

    var fechaVenc = new Date(data[i][6]);

    // Si está expirada, marcar y saltar
    if (hoy > fechaVenc) {
      if (estado !== 'expirado') {
        sheet.getRange(i + 1, 3).setValue('expirado');
      }
      continue;
    }

    var rowPlan = detectarPlan(String(data[i][4]).trim());

    // Preferir suscripción con escuela, luego la de mayor vencimiento
    var dominated = false;
    if (bestRow !== -1) {
      if (bestEscuela && !rowPlan.escuela) dominated = true;
      if (!dominated && !bestEscuela && !rowPlan.escuela && fechaVenc <= bestVenc) dominated = true;
      if (!dominated && bestEscuela && rowPlan.escuela && fechaVenc <= bestVenc) dominated = true;
    }

    if (!dominated) {
      bestRow = i;
      bestVenc = fechaVenc;
      bestEscuela = rowPlan.escuela;
    }
  }

  if (bestRow === -1) {
    return { success: true, valid: false, reason: 'No se encontró suscripción activa para este email' };
  }

  // Detectar plan de la mejor suscripción
  var bestRef = String(data[bestRow][4]).trim();
  var plan = detectarPlan(bestRef);

  // Registrar dispositivo
  var numDisp = Number(data[bestRow][7]) || 0;
  var dispositivos = String(data[bestRow][8]).trim();

  if (device) {
    var dispList = dispositivos ? dispositivos.split('|') : [];
    if (dispList.indexOf(device) === -1) {
      if (numDisp >= MAX_DISPOSITIVOS) {
        return {
          success: true,
          valid: false,
          reason: 'Límite de dispositivos alcanzado (' + MAX_DISPOSITIVOS + ')',
          expiry: Utilities.formatDate(bestVenc, 'America/Bogota', 'yyyy-MM-dd')
        };
      }
      dispList.push(device);
      sheet.getRange(bestRow + 1, 8).setValue(dispList.length);
      sheet.getRange(bestRow + 1, 9).setValue(dispList.join('|'));
    }
  }

  var diasRestantes = Math.ceil((bestVenc - hoy) / (1000 * 60 * 60 * 24));

  return {
    success: true,
    valid: true,
    reason: 'Suscripción activa',
    daysLeft: diasRestantes,
    expiry: Utilities.formatDate(bestVenc, 'America/Bogota', 'yyyy-MM-dd'),
    planType: plan.planType,
    escuela: plan.escuela
  };
}

// ═══════════════════════════════════════════════════════════
// VERIFICACIÓN WOMPI
// ═══════════════════════════════════════════════════════════
function verificarTransaccionWompi(transactionId) {
  try {
    var url = 'https://production.wompi.co/v1/transactions/' + transactionId;
    var response = UrlFetchApp.fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': 'Bearer ' + WOMPI_PRIVATE_KEY
      },
      muteHttpExceptions: true
    });

    var json = JSON.parse(response.getContentText());
    var tx = json.data;

    if (!tx) {
      return { valid: false, reason: 'Transacción no encontrada en Wompi' };
    }

    if (tx.status !== 'APPROVED') {
      return { valid: false, reason: 'Transacción no aprobada. Estado: ' + tx.status };
    }

    if (tx.amount_in_cents < MONTO_MINIMO_COP) {
      return { valid: false, reason: 'Monto insuficiente: $' + (tx.amount_in_cents / 100) };
    }

    return {
      valid: true,
      email: tx.customer_email || '',
      amount: tx.amount_in_cents,
      reference: tx.reference
    };
  } catch (e) {
    return { valid: false, reason: 'Error verificando con Wompi: ' + e.message };
  }
}

// ═══════════════════════════════════════════════════════════
// 2.4 — TRIGGER DIARIO (sin emails duplicados)
// ═══════════════════════════════════════════════════════════
function expirarClaves() {
  var sheet = getSheet();
  var data = sheet.getDataRange().getValues();
  var hoy = new Date();

  for (var i = 1; i < data.length; i++) {
    var estado = String(data[i][2]).trim().toLowerCase();
    if (estado !== 'activo') continue;

    var fechaVenc = new Date(data[i][6]);
    var email = String(data[i][5]).trim();
    var clave = String(data[i][0]).trim();
    var reminderSent = String(data[i][9] || '').trim(); // J: ReminderSent
    var diasRestantes = Math.ceil((fechaVenc - hoy) / (1000 * 60 * 60 * 24));

    // Expirar claves vencidas
    if (hoy > fechaVenc) {
      sheet.getRange(i + 1, 3).setValue('expirado');
      // Solo enviar email de expiración si no se envió antes
      if (email && reminderSent !== 'expirado') {
        enviarEmailExpiracion(email, clave);
        sheet.getRange(i + 1, 10).setValue('expirado'); // J: marcar enviado
      }
      continue;
    }

    // Recordatorio 3 días antes (solo una vez)
    if (diasRestantes <= EMAIL_REMINDER_DAYS && diasRestantes > 0 && email && reminderSent !== 'recordatorio') {
      enviarEmailRecordatorio(email, clave, diasRestantes, Utilities.formatDate(fechaVenc, 'America/Bogota', 'yyyy-MM-dd'));
      sheet.getRange(i + 1, 10).setValue('recordatorio'); // J: marcar enviado
    }
  }
}

// ═══════════════════════════════════════════════════════════
// EMAILS
// ═══════════════════════════════════════════════════════════
function enviarEmailRecordatorio(email, clave, diasRestantes, fechaVenc) {
  var subject = 'Tu suscripción PRO vence en ' + diasRestantes + ' día(s) — ExógenaDIAN';
  var body = 'Hola,\n\n'
    + 'Tu clave PRO (' + clave + ') vence el ' + fechaVenc + '.\n\n'
    + 'Para seguir usando las funciones PRO sin interrupción, renueva tu suscripción en:\n'
    + 'https://exogenadian.com/precios.html\n\n'
    + 'Si ya renovaste, ignora este mensaje.\n\n'
    + 'Gracias por usar ExógenaDIAN.\n'
    + '---\nExógenaDIAN · exogenadian.com';

  try {
    MailApp.sendEmail(email, subject, body);
  } catch (e) {
    Logger.log('Error enviando email a ' + email + ': ' + e.message);
  }
}

function enviarEmailExpiracion(email, clave) {
  var subject = 'Tu suscripción PRO ha expirado — ExógenaDIAN';
  var body = 'Hola,\n\n'
    + 'Tu clave PRO (' + clave + ') ha expirado.\n\n'
    + 'Las funciones PRO están bloqueadas hasta que renueves.\n'
    + 'Renueva aquí: https://exogenadian.com/precios.html\n\n'
    + 'Si tienes alguna pregunta, escríbenos por WhatsApp.\n\n'
    + 'Gracias por usar ExógenaDIAN.\n'
    + '---\nExógenaDIAN · exogenadian.com';

  try {
    MailApp.sendEmail(email, subject, body);
  } catch (e) {
    Logger.log('Error enviando email a ' + email + ': ' + e.message);
  }
}

// ═══════════════════════════════════════════════════════════
// ALERTAS (usadas por el backend para notificar presupuesto)
// ═══════════════════════════════════════════════════════════
function handleSendAlert(params) {
  var email = params.email || 'soporte@exogenadian.com';
  var subject = params.subject || 'Alerta ExógenaDIAN';
  var body = params.body || 'Alerta sin contenido';

  try {
    MailApp.sendEmail(email, subject, body);
    return { success: true, message: 'Alerta enviada a ' + email };
  } catch (e) {
    Logger.log('Error enviando alerta a ' + email + ': ' + e.message);
    return { success: false, error: e.message };
  }
}

// ═══════════════════════════════════════════════════════════
// UTILIDADES
// ═══════════════════════════════════════════════════════════
function getSheet() {
  return SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SHEET_NAME);
}

function buscarPorTransaccion(sheet, transactionId) {
  var data = sheet.getDataRange().getValues();
  for (var i = 1; i < data.length; i++) {
    if (String(data[i][3]).trim() === transactionId) {
      return { clave: String(data[i][0]).trim(), estado: String(data[i][2]).trim() };
    }
  }
  return null;
}

function generarClaveUnica(sheet) {
  var chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  var intentos = 0;
  while (intentos < 100) {
    var clave = 'PRO-';
    for (var g = 0; g < 3; g++) {
      if (g > 0) clave += '-';
      for (var c = 0; c < 4; c++) {
        clave += chars.charAt(Math.floor(Math.random() * chars.length));
      }
    }
    if (!buscarPorClave(sheet, clave)) {
      return clave;
    }
    intentos++;
  }
  return 'PRO-' + Date.now().toString(36).toUpperCase();
}

function buscarPorClave(sheet, clave) {
  var data = sheet.getDataRange().getValues();
  for (var i = 1; i < data.length; i++) {
    if (String(data[i][0]).trim() === clave) return true;
  }
  return false;
}

// ═══════════════════════════════════════════════════════════
// MONITOR — Verificar que los servicios de IA estén activos
// Configurar trigger cada 5 minutos: monitorHealth
// ═══════════════════════════════════════════════════════════
var BACKEND_URL = 'https://dian-proxy-337146111457.southamerica-east1.run.app';
var ALERT_EMAIL = 'soporte@exogenadian.com';

/**
 * Ejecutar cada 5 minutos con trigger.
 * 1. Llama a /api/health y verifica que todos los servicios estén OK.
 * 2. Hace un POST ligero a cada endpoint de IA para confirmar que responden (no 404/500).
 * 3. Si algo falla, envía email. No repite la alerta si ya se envió en las últimas 2 horas.
 */
function monitorHealth() {
  var props = PropertiesService.getScriptProperties();
  var lastAlert = Number(props.getProperty('MONITOR_LAST_ALERT') || '0');
  var now = new Date().getTime();
  var cooldown = 2 * 60 * 60 * 1000; // 2 horas entre alertas

  var errores = [];

  // 1. Health check general
  try {
    var resp = UrlFetchApp.fetch(BACKEND_URL + '/api/health', { muteHttpExceptions: true });
    var code = resp.getResponseCode();
    if (code !== 200) {
      errores.push('Health endpoint retornó HTTP ' + code);
    } else {
      var data = JSON.parse(resp.getContentText());
      if (data.status !== 'ok') {
        errores.push('Health status: ' + data.status);
      }
      // Verificar cada servicio
      var services = data.services || {};
      for (var svc in services) {
        if (!services[svc]) {
          errores.push('Servicio caído: ' + svc);
        }
      }
    }
  } catch (e) {
    errores.push('Health check falló: ' + e.message);
  }

  // 2. Verificar que los endpoints de IA respondan (POST mínimo, esperamos 400/422, NO 404)
  var endpoints = [
    { name: 'Chat Exa', path: '/api/chat' },
    { name: 'IA Asistente', path: '/api/ia/asistente' },
    { name: 'IA Balance', path: '/api/ia/analisis-balance' },
    { name: 'IA Chat ET', path: '/api/ia/chat-et' },
    { name: 'IA Inconsistencias', path: '/api/ia/inconsistencias' },
    { name: 'IA Resumen', path: '/api/ia/resumen-declaracion' },
    { name: 'IA Requerimiento', path: '/api/ia/respuesta-requerimiento' },
    { name: 'IA Verificar Artículos', path: '/api/ia/verificar-articulos' }
  ];

  for (var i = 0; i < endpoints.length; i++) {
    try {
      var r = UrlFetchApp.fetch(BACKEND_URL + endpoints[i].path, {
        method: 'POST',
        contentType: 'application/json',
        payload: JSON.stringify({}),
        muteHttpExceptions: true
      });
      var status = r.getResponseCode();
      // 404 o 500+ = endpoint no registrado o servidor roto
      if (status === 404 || status >= 500) {
        errores.push(endpoints[i].name + ' (' + endpoints[i].path + ') → HTTP ' + status);
      }
      // 422 (validation error) o 400 es esperado con body vacío = endpoint existe
    } catch (e) {
      errores.push(endpoints[i].name + ' no responde: ' + e.message);
    }
  }

  // 3. Si hay errores, enviar alerta (respetando cooldown)
  if (errores.length > 0) {
    Logger.log('Monitor detectó ' + errores.length + ' error(es): ' + errores.join('; '));

    if (now - lastAlert > cooldown) {
      var subject = '🚨 ExógenaDIAN — Servicios caídos (' + errores.length + ' errores)';
      var body = 'El monitor automático detectó los siguientes problemas:\n\n'
        + errores.map(function(e, i) { return (i+1) + '. ' + e; }).join('\n')
        + '\n\nURL backend: ' + BACKEND_URL
        + '\nRevisa Cloud Run: https://console.cloud.google.com/run'
        + '\n\nFecha: ' + new Date().toLocaleString('es-CO', { timeZone: 'America/Bogota' });

      try {
        MailApp.sendEmail(ALERT_EMAIL, subject, body);
        props.setProperty('MONITOR_LAST_ALERT', String(now));
        Logger.log('Alerta enviada a ' + ALERT_EMAIL);
      } catch (e) {
        Logger.log('Error enviando alerta: ' + e.message);
      }
    } else {
      Logger.log('Cooldown activo, no se reenvía alerta.');
    }
  } else {
    Logger.log('Monitor OK — todos los servicios activos.');
  }
}

// ═══════════════════════════════════════════════════════════
// MONITOR DIAN — Detectar cambios en el portal MUISCA
// Configurar trigger diario: monitorDIAN
// ═══════════════════════════════════════════════════════════
/**
 * Verifica que el portal MUISCA de la DIAN no haya cambiado su estructura.
 * Consulta un NIT conocido (DIAN misma: 800197268) y verifica que el scraper
 * pueda extraer razón social y estado. Si falla, envía alerta.
 * Ejecutar 1 vez al día con trigger.
 */
function monitorDIAN() {
  var props = PropertiesService.getScriptProperties();
  var lastAlert = Number(props.getProperty('DIAN_MONITOR_LAST_ALERT') || '0');
  var now = new Date().getTime();
  var cooldown = 12 * 60 * 60 * 1000; // 12 horas entre alertas

  // NIT de prueba: la DIAN misma
  var testNit = '800197268';
  var errores = [];

  try {
    var resp = UrlFetchApp.fetch(BACKEND_URL + '/api/debug/' + testNit, {
      muteHttpExceptions: true,
      headers: { 'Origin': 'https://exogenadian.com' }
    });
    var code = resp.getResponseCode();

    if (code !== 200) {
      errores.push('Debug endpoint retornó HTTP ' + code);
    } else {
      var data = JSON.parse(resp.getContentText());
      var dian = data.dian || {};

      // Verificar que el scraper DIAN funcione
      if (dian.error) {
        errores.push('Scraper DIAN error: ' + (dian.error || '').substring(0, 200));
      }
      if (!dian.razon_social || dian.razon_social.length < 3) {
        errores.push('Scraper DIAN no extrajo razón social para NIT ' + testNit);
      }
      if (!dian.estado_rut) {
        errores.push('Scraper DIAN no extrajo estado RUT para NIT ' + testNit);
      }

      // Si la razón social cambió, podría ser un falso positivo pero vale alertar
      if (dian.razon_social && dian.razon_social.indexOf('IMPUESTOS') === -1 && dian.razon_social.indexOf('DIAN') === -1) {
        errores.push('Razón social inesperada para NIT DIAN: ' + dian.razon_social);
      }
    }
  } catch (e) {
    errores.push('Error consultando debug endpoint: ' + e.message);
  }

  if (errores.length > 0) {
    Logger.log('Monitor DIAN detectó ' + errores.length + ' problema(s): ' + errores.join('; '));

    if (now - lastAlert > cooldown) {
      var subject = '🔴 ExógenaDIAN — Scraper DIAN posiblemente roto';
      var body = 'El monitor diario detectó que el scraper de DIAN MUISCA puede estar fallando:\n\n'
        + errores.map(function(e, i) { return (i+1) + '. ' + e; }).join('\n')
        + '\n\nPosibles causas:'
        + '\n  - La DIAN cambió la estructura del portal MUISCA'
        + '\n  - Cloudflare actualizó el Turnstile/CAPTCHA'
        + '\n  - CapSolver no puede resolver el nuevo tipo de CAPTCHA'
        + '\n\nAcciones:'
        + '\n  1. Verificar manualmente: https://muisca.dian.gov.co/WebRutMuisca/DefConsultaEstadoRUT.faces'
        + '\n  2. Revisar logs: https://console.cloud.google.com/run?project=exogenadian-492122'
        + '\n  3. Si la DIAN cambió, actualizar los selectores en dian_scraper.py'
        + '\n\nFecha: ' + new Date().toLocaleString('es-CO', { timeZone: 'America/Bogota' });

      try {
        MailApp.sendEmail(ALERT_EMAIL, subject, body);
        props.setProperty('DIAN_MONITOR_LAST_ALERT', String(now));
        Logger.log('Alerta DIAN enviada a ' + ALERT_EMAIL);
      } catch (e) {
        Logger.log('Error enviando alerta DIAN: ' + e.message);
      }
    } else {
      Logger.log('Cooldown DIAN activo, no se reenvía alerta.');
    }
  } else {
    Logger.log('Monitor DIAN OK — scraper funcionando correctamente.');
  }
}

// ═══════════════════════════════════════════════════════════
// SETUP — solo ejecutar si necesitas recrear headers
// ═══════════════════════════════════════════════════════════
function setupSheet() {
  var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  var sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
  }
  // Verificar si ya tiene datos para no sobrescribir
  if (sheet.getLastRow() > 1) {
    Logger.log('Sheet ya tiene datos (' + (sheet.getLastRow()-1) + ' filas). No se sobrescribe.');
    return;
  }
  sheet.getRange(1, 1, 1, 10).setValues([[
    'Clave', 'FechaCompra', 'Estado', 'TransactionId',
    'Reference', 'Email', 'FechaVencimiento', 'NumDispositivos', 'Dispositivos', 'ReminderSent'
  ]]);
  sheet.getRange(1, 1, 1, 10).setFontWeight('bold');
  sheet.setFrozenRows(1);

  // Para crear una clave admin, usa PropertiesService:
  //   Script Properties → ADMIN_KEY = tu-clave-segura
  // Luego inserta manualmente en la hoja.
  // NO hardcodear claves en el código fuente.

  Logger.log('Sheet configurado correctamente. Agrega la clave admin manualmente desde la hoja.');
}

// ═══════════════════════════════════════════════════════════
// NEWSLETTER — Guardar emails de suscriptores
// ═══════════════════════════════════════════════════════════
function handleNewsletter(params) {
  var email = (params.email || '').trim().toLowerCase();
  if (!email || email.indexOf('@') === -1) {
    return { success: false, error: 'Email inválido' };
  }

  var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  var sheet = ss.getSheetByName('Newsletter');

  // Crear hoja si no existe
  if (!sheet) {
    sheet = ss.insertSheet('Newsletter');
    sheet.getRange(1, 1, 1, 3).setValues([['Email', 'Fecha', 'Origen']]);
    sheet.getRange(1, 1, 1, 3).setFontWeight('bold');
    sheet.setFrozenRows(1);
  }

  // Verificar duplicado
  var data = sheet.getDataRange().getValues();
  for (var i = 1; i < data.length; i++) {
    if (String(data[i][0]).trim().toLowerCase() === email) {
      return { success: true, message: 'Ya estás suscrito' };
    }
  }

  // Guardar
  sheet.appendRow([
    email,
    Utilities.formatDate(new Date(), 'America/Bogota', 'yyyy-MM-dd HH:mm'),
    'web'
  ]);

  return { success: true, message: 'Suscrito correctamente' };
}

// ═══════════════════════════════════════════════════════════
// FIRMA DE INTEGRIDAD WOMPI
// ═══════════════════════════════════════════════════════════
function handleWompiSignature(params) {
  var ref = params.ref || '';
  var amount = params.amount || '';
  var currency = params.currency || 'COP';

  if (!ref || !amount) {
    return { success: false, error: 'Faltan parámetros ref y amount' };
  }
  if (!WOMPI_INTEGRITY_SECRET) {
    return { success: false, error: 'WOMPI_INTEGRITY_SECRET no configurado' };
  }

  var cadena = ref + amount + currency + WOMPI_INTEGRITY_SECRET;
  var hash = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, cadena);
  var signature = hash.map(function(b) {
    return ('0' + ((b < 0 ? b + 256 : b).toString(16))).slice(-2);
  }).join('');

  return { success: true, signature: signature };
}
