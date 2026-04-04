/**
 * ═══════════════════════════════════════════════════════════
 * ExógenaDIAN — Apps Script Backend (Fase 2.1)
 * ═══════════════════════════════════════════════════════════
 *
 * Endpoints:
 *   ?action=generateKey&transactionId=X&ref=Y  → Verifica pago Wompi y genera clave
 *   ?action=validateKey&key=X&device=FP         → Valida clave PRO (privado)
 *   ?action=validateEmail&email=X&device=FP     → Valida por email (público)
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
//     WOMPI_PRIVATE_KEY = tu clave privada de Wompi producción
//     SPREADSHEET_ID    = ID de la hoja de Google Sheets
const WOMPI_PRIVATE_KEY = PropertiesService.getScriptProperties().getProperty('WOMPI_PRIVATE_KEY');
const SPREADSHEET_ID = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
const SHEET_NAME = 'Claves';
const MONTO_MINIMO_COP = 1990000; // $19,900 en centavos
const DIAS_VIGENCIA = 30;
const MAX_DISPOSITIVOS = 2;
const EMAIL_REMINDER_DAYS = 3;

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

    // Generar clave única
    var clave = generarClaveUnica(sheet);
    var hoy = new Date();
    var vencimiento = new Date(hoy);
    vencimiento.setDate(vencimiento.getDate() + DIAS_VIGENCIA);

    // Escribir en el Sheet (columnas A-J, ahora con ReminderSent)
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
      daysLeft: DIAS_VIGENCIA
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
    var fechaVenc = row[6];
    var numDisp = Number(row[7]) || 0;
    var dispositivos = String(row[8]).trim();

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
      expiry: Utilities.formatDate(venc, 'America/Bogota', 'yyyy-MM-dd')
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

  // Buscar la suscripción activa más reciente para este email
  var bestRow = -1;
  var bestVenc = null;

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

    // Si está activa y es más reciente que la anterior encontrada
    if (bestVenc === null || fechaVenc > bestVenc) {
      bestRow = i;
      bestVenc = fechaVenc;
    }
  }

  if (bestRow === -1) {
    return { success: true, valid: false, reason: 'No se encontró suscripción activa para este email' };
  }

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
    expiry: Utilities.formatDate(bestVenc, 'America/Bogota', 'yyyy-MM-dd')
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
    + 'https://exogenadian.com/#planes\n\n'
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
    + 'Renueva aquí: https://exogenadian.com/#planes\n\n'
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
