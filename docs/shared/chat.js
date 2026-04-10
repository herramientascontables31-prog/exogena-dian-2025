/* ═══ ExógenaDIAN — Exa Chat Widget v2 ═══
   Uso:
     <link rel="stylesheet" href="shared/chat.css">
     <script src="shared/chat.js"></script>

   Config (opcional, antes del script):
     window.EXA_CONFIG = { apiUrl: 'https://tu-backend.com' };

   v2: Chat contextual — Exa sabe en qué página estás,
       ofrece ayuda específica y sugiere acciones relevantes.
*/
(function () {
  'use strict';

  var WA = 'https://wa.me/573054559574';
  var BASE = 'https://exogenadian.com';

  // ─── Config ───
  var CFG = Object.assign({
    apiUrl: 'https://dian-proxy-337146111457.southamerica-east1.run.app',
    maxHistory: 10,
    storageKey: 'exa_chat_history',
    whatsapp: WA,
  }, window.EXA_CONFIG || {});

  // ═══════════════════════════════════════════════════════════════
  //  CONTEXTO DE PÁGINA — Exa sabe dónde estás
  // ═══════════════════════════════════════════════════════════════

  var PAGE_CONTEXT = {
    'index': {
      id: 'inicio',
      name: 'Inicio',
      greeting: 'Hola, soy **Exa** — tu asistente contable con IA. Cuéntame qué necesitas hacer y te llevo a la herramienta exacta.',
      suggestions: [
        '¿Cómo genero la exógena?',
        '¿Qué herramientas son gratis?',
        '¿Cuándo vence la exógena?',
        '¿Qué incluye PRO?'
      ],
      placeholder: 'Cuéntame qué necesitas hacer...'
    },
    'exogena': {
      id: 'exogena',
      name: 'Exógena DIAN',
      greeting: 'Estás en el **generador de exógena**. Te puedo ayudar con la carga de tu balance, clasificación de cuentas o cualquier duda sobre los formatos F1001-F2276.',
      suggestions: [
        '¿Qué formato necesito para mi balance?',
        '¿Cómo clasifico gastos de representación?',
        'Error en el NIT de un tercero',
        '¿Qué cuentas van en F1001?'
      ],
      placeholder: 'Pregunta sobre exógena, formatos, clasificación...'
    },
    'iva300': {
      id: 'iva300',
      name: 'Formulario 300 IVA',
      greeting: 'Estás en el **formulario 300 de IVA**. Te ayudo con la clasificación de IVA descontable/generado, tarifas o cualquier casilla del formulario.',
      suggestions: [
        '¿Qué tarifa de IVA aplica a...?',
        '¿Cómo funciona el IVA proporcional?',
        '¿Cuándo soy bimestral vs cuatrimestral?',
        'IVA en servicios del exterior'
      ],
      placeholder: 'Pregunta sobre IVA, tarifas, casillas...'
    },
    'retencion350': {
      id: 'retencion350',
      name: 'Retención 350',
      greeting: 'Estás en el **formulario 350 de retención**. Te ayudo con bases, tarifas de retención o la clasificación de conceptos.',
      suggestions: [
        '¿Cuál es la base para servicios?',
        'Retención a no declarantes',
        '¿Cuándo aplica autorretención?',
        'Tarifa de honorarios personas naturales'
      ],
      placeholder: 'Pregunta sobre retención, bases, tarifas...'
    },
    'renta110': {
      id: 'renta110',
      name: 'Renta 110',
      greeting: 'Estás en la **declaración de renta (F110)**. Te ayudo con rentas exentas, deducciones, depreciación fiscal o cálculo del impuesto.',
      suggestions: [
        '¿Qué gastos son deducibles?',
        'Límite de rentas exentas PN',
        '¿Cómo funciona la depreciación fiscal?',
        'Tasa mínima de tributación 15%'
      ],
      placeholder: 'Pregunta sobre renta, deducciones, impuesto...'
    },
    'estadosfinancieros': {
      id: 'estadosfinancieros',
      name: 'Estados Financieros NIIF',
      greeting: 'Estás en los **estados financieros NIIF**. Te ayudo con clasificación de cuentas, revelaciones, políticas contables o el flujo de efectivo.',
      suggestions: [
        '¿Qué revelaciones son obligatorias?',
        '¿Cómo clasifico un leasing?',
        'Método indirecto del flujo de efectivo',
        'Políticas contables para PYMES'
      ],
      placeholder: 'Pregunta sobre NIIF, revelaciones, estados...'
    },
    'conciliacion': {
      id: 'conciliacion',
      name: 'Conciliación Bancaria',
      greeting: 'Estás en la **conciliación bancaria**. Te ayudo a identificar partidas conciliatorias o diferencias entre tu contabilidad y el extracto.',
      suggestions: [
        '¿Cómo trato cheques pendientes?',
        'Notas débito/crédito no registradas',
        '¿Cada cuánto conciliar?',
        'Diferencias en GMF'
      ],
      placeholder: 'Pregunta sobre conciliación, partidas...'
    },
    'consultanit': {
      id: 'consultanit',
      name: 'Consulta NIT',
      greeting: 'Estás en **consulta NIT**. Te ayudo a verificar información de terceros, razón social, DV o estado del RUT.',
      suggestions: [
        '¿Cómo calculo el dígito de verificación?',
        '¿Qué es un autorretenedor?',
        '¿Cómo verifico un gran contribuyente?',
        'NIT de proveedores ficticios'
      ],
      placeholder: 'Pregunta sobre NIT, RUT, verificación...'
    },
    'vencimientos': {
      id: 'vencimientos',
      name: 'Calendario Tributario',
      greeting: 'Estás en el **calendario de vencimientos 2026**. Te ayudo con fechas específicas según tu tipo de contribuyente y último dígito del NIT.',
      suggestions: [
        '¿Cuándo vence mi exógena?',
        'Vencimiento renta personas naturales',
        '¿Cuándo presento el IVA bimestral?',
        'Fechas de retención mensual'
      ],
      placeholder: 'Pregunta sobre vencimientos, plazos, fechas...'
    },
    'sanciones': {
      id: 'sanciones',
      name: 'Sanciones Exógena',
      greeting: 'Estás en **sanciones por exógena** (Art. 651 ET). Te ayudo a calcular multas, revisar reducciones o entender la gradualidad.',
      suggestions: [
        '¿Cuánto es la multa por no presentar?',
        'Reducción de sanciones Art. 640',
        '¿Puedo corregir sin sanción?',
        'Sanción mínima 2026'
      ],
      placeholder: 'Pregunta sobre sanciones, multas, reducción...'
    },
    'sanciones-dian': {
      id: 'sanciones-dian',
      name: 'Sanciones DIAN',
      greeting: 'Estás en **sanciones DIAN**. Te ayudo con extemporaneidad, inexactitud, correcciones o reducción de sanciones según Art. 640 ET.',
      suggestions: [
        'Sanción por extemporaneidad',
        '¿Cómo funciona el Art. 640?',
        'Sanción por corrección voluntaria',
        'Sanción por inexactitud'
      ],
      placeholder: 'Pregunta sobre sanciones, correcciones...'
    },
    'intereses': {
      id: 'intereses',
      name: 'Intereses de Mora',
      greeting: 'Estás en el **calculador de intereses de mora**. Te ayudo con las tasas vigentes, períodos de cálculo o el Decreto 0240/2026.',
      suggestions: [
        '¿Cuál es la tasa de mora actual?',
        '¿Se pagan intereses sobre sanciones?',
        '¿Cómo funciona el Decreto 0240?',
        'Facilidades de pago DIAN'
      ],
      placeholder: 'Pregunta sobre intereses, mora, tasas...'
    },
    'liquidador': {
      id: 'liquidador',
      name: 'Liquidador Laboral',
      greeting: 'Estás en el **liquidador laboral**. Te ayudo con prestaciones, indemnización, seguridad social o cualquier cálculo laboral.',
      suggestions: [
        '¿Cómo liquido las cesantías?',
        'Indemnización por despido sin justa causa',
        '¿Cuándo pago prima de servicios?',
        'Dotación: ¿quién tiene derecho?'
      ],
      placeholder: 'Pregunta sobre liquidación, prestaciones...'
    },
    'ia': {
      id: 'ia',
      name: 'Herramientas IA',
      greeting: 'Bienvenido a las **herramientas de IA**. Tenemos un auditor de balance, chat con el Estatuto Tributario y detector de inconsistencias. ¿Cuál necesitas?',
      suggestions: [
        '¿Qué hace el auditor de balance?',
        'Quiero consultar el Estatuto Tributario',
        '¿Cómo detecta inconsistencias?',
        '¿Cuántas consultas tengo gratis?'
      ],
      placeholder: 'Pregunta sobre las herramientas de IA...'
    },
    'precios': {
      id: 'precios',
      name: 'Precios',
      greeting: 'Estás en la página de **precios**. Te ayudo a entender qué incluye cada plan y cuál te conviene según tu volumen de trabajo.',
      suggestions: [
        '¿Qué incluye el plan gratis?',
        '¿Puedo cancelar en cualquier momento?',
        '¿El pago es seguro?',
        '¿Qué diferencia hay entre mensual y anual?'
      ],
      placeholder: 'Pregunta sobre planes, precios, pagos...'
    }
  };

  // Detectar página actual
  function detectPage() {
    var path = location.pathname.replace(/^\/|\.html$/g, '').replace(/\/+$/, '') || 'index';
    // Limpiar /docs/ prefix si existe
    path = path.replace(/^docs\//, '');
    // Buscar coincidencia exacta o parcial
    if (PAGE_CONTEXT[path]) return PAGE_CONTEXT[path];
    // Buscar por prefijo (ia-analisis-balance → ia)
    var prefix = path.split('-')[0];
    if (PAGE_CONTEXT[prefix]) return PAGE_CONTEXT[prefix];
    // Fallback al contexto de inicio
    return PAGE_CONTEXT['index'];
  }

  var currentPage = null;
  var isPro = false; // Se actualiza al init con exoPro.check()

  // ─── State ───
  var isOpen = false;
  var isStreaming = false;
  var messages = [];
  var abortCtrl = null;

  // ─── Minimal markdown → HTML ───
  function md(text) {
    if (!text) return '';
    var html = text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/^####\s+(.+)$/gm, '<h4>$1</h4>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/`(.+?)`/g, '<code>$1</code>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, function(_, label, url) {
        if (/^https?:\/\/|^\//.test(url)) return '<a href="' + url + '" target="_blank" rel="noopener">' + label + '</a>';
        return label;
      })
      .replace(/^[•\-]\s+(.+)$/gm, '<li>$1</li>')
      .replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>');
    html = html.replace(/((?:<li>.*?<\/li>(?:<br>)?)+)/g, '<ul>$1</ul>');
    html = html.replace(/<br><\/ul>/g, '</ul>').replace(/<ul><br>/g, '<ul>');
    return '<p>' + html + '</p>';
  }

  // ─── Load/save/clear history ───
  function loadHistory() {
    try {
      var data = localStorage.getItem(CFG.storageKey);
      if (data) {
        var parsed = JSON.parse(data);
        messages = parsed.filter(function (m) {
          return m && (m.role === 'user' || m.role === 'assistant')
            && typeof m.content === 'string' && m.content.length > 0 && m.content.length <= 4000;
        });
      }
    } catch (e) {
      messages = [];
      localStorage.removeItem(CFG.storageKey);
    }
  }
  function saveHistory() {
    try {
      localStorage.setItem(CFG.storageKey, JSON.stringify(messages.slice(-20)));
    } catch (e) { /* ignore */ }
  }
  function clearHistory() {
    messages = [];
    localStorage.removeItem(CFG.storageKey);
    renderMessages();
  }

  // ─── DOM refs ───
  var panel, messagesEl, inputEl, sendBtn;

  // ─── Build UI ───
  function init() {
    currentPage = detectPage();
    loadHistory();

    // Check PRO status — contextual features only for PRO
    if (typeof exoPro !== 'undefined' && exoPro.check) {
      exoPro.check().then(function (pro) {
        isPro = pro;
        if (pro && messages.length === 0) renderMessages(); // Re-render with suggestions
      });
    }

    // Inject CSS if not already linked
    if (!document.querySelector('link[href*="chat.css"]')) {
      var link = document.createElement('link');
      link.rel = 'stylesheet';
      var isSubpage = location.pathname.split('/').filter(Boolean).length > 0
        && !location.pathname.endsWith('index.html')
        && !location.pathname.endsWith('/');
      link.href = (isSubpage ? '../' : '') + 'shared/chat.css';
      document.head.appendChild(link);
    }

    // FAB
    var fab = document.createElement('button');
    fab.className = 'exa-fab';
    fab.setAttribute('aria-label', 'Abrir asistente Exa');
    fab.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>';
    fab.onclick = togglePanel;

    // Panel
    panel = document.createElement('div');
    panel.className = 'exa-panel';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Chat con Exa');
    panel.innerHTML =
      '<div class="exa-header">' +
        '<div class="exa-avatar">E</div>' +
        '<div class="exa-header-info">' +
          '<h3>Exa</h3>' +
          '<span>Asistente contable IA</span>' +
        '</div>' +
        '<button class="exa-clear" aria-label="Nueva conversación" title="Nueva conversación">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>' +
        '</button>' +
        '<button class="exa-close" aria-label="Cerrar chat">&times;</button>' +
      '</div>' +
      '<div class="exa-messages"></div>' +
      '<div class="exa-input-area">' +
        '<textarea class="exa-input" placeholder="' + esc(currentPage.placeholder) + '" rows="1" maxlength="500"></textarea>' +
        '<button class="exa-send" aria-label="Enviar" disabled>' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>' +
        '</button>' +
      '</div>' +
      '<div class="exa-footer">Exa puede cometer errores · <a href="https://exogenadian.com" target="_blank" rel="noopener">exogenadian.com</a></div>';

    document.body.appendChild(fab);
    document.body.appendChild(panel);

    messagesEl = panel.querySelector('.exa-messages');
    inputEl = panel.querySelector('.exa-input');
    sendBtn = panel.querySelector('.exa-send');

    panel.querySelector('.exa-close').onclick = togglePanel;
    panel.querySelector('.exa-clear').onclick = clearHistory;
    sendBtn.onclick = sendMessage;
    inputEl.addEventListener('input', function () {
      sendBtn.disabled = !inputEl.value.trim() || isStreaming;
      autoResize();
    });
    inputEl.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && isOpen) togglePanel();
    });

    renderMessages();
  }

  function autoResize() {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 100) + 'px';
  }

  function togglePanel() {
    isOpen = !isOpen;
    panel.classList.toggle('open', isOpen);
    document.querySelector('.exa-fab').classList.toggle('open', isOpen);
    if (isOpen) { inputEl.focus(); scrollToBottom(); }
  }

  function scrollToBottom() {
    requestAnimationFrame(function () { messagesEl.scrollTop = messagesEl.scrollHeight; });
  }

  // ═══════════════════════════════════════════════════════════════
  //  SUGERENCIAS CONTEXTUALES — botones rápidos según la página
  // ═══════════════════════════════════════════════════════════════

  function renderSuggestions() {
    if (!currentPage.suggestions || !currentPage.suggestions.length) return;
    var wrap = document.createElement('div');
    wrap.className = 'exa-quick-wrap';
    var inner = document.createElement('div');
    inner.className = 'exa-quick';
    currentPage.suggestions.forEach(function (text) {
      var btn = document.createElement('button');
      btn.textContent = text;
      btn.onclick = function () {
        inputEl.value = text;
        sendMessage();
        // Quitar sugerencias después de usar una
        var allWraps = messagesEl.querySelectorAll('.exa-quick-wrap');
        allWraps.forEach(function (w) { w.remove(); });
      };
      inner.appendChild(btn);
    });
    wrap.appendChild(inner);
    messagesEl.appendChild(wrap);
  }

  var GENERIC_GREETING = 'Hola, soy **Exa** \u2014 tu asistente contable. Pregunta lo que necesites sobre normas tributarias, sanciones, vencimientos o herramientas del portal.';
  var GENERIC_PLACEHOLDER = 'Pregunta sobre impuestos, sanciones, ex\u00f3gena...';

  // ─── Render ───
  function renderMessages() {
    if (messages.length === 0) {
      messagesEl.innerHTML = '';
      var greet = document.createElement('div');
      greet.className = 'exa-msg assistant';
      // PRO: greeting contextual de la página. Free: greeting genérico.
      greet.innerHTML = md(isPro ? currentPage.greeting : GENERIC_GREETING);
      messagesEl.appendChild(greet);
      // Solo PRO ve sugerencias contextuales
      if (isPro) renderSuggestions();
      // Actualizar placeholder según PRO
      if (inputEl) inputEl.placeholder = isPro ? currentPage.placeholder : GENERIC_PLACEHOLDER;
      return;
    }

    messagesEl.innerHTML = '';
    messages.forEach(function (m) {
      var div = document.createElement('div');
      div.className = 'exa-msg ' + m.role;
      div.innerHTML = m.role === 'assistant' ? md(m.content) : esc(m.content);
      messagesEl.appendChild(div);
    });
    scrollToBottom();
  }

  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
  }

  function addBubble(role, content) {
    var div = document.createElement('div');
    div.className = 'exa-msg ' + role;
    div.innerHTML = role === 'assistant' ? md(content) : esc(content);
    var w = messagesEl.querySelector('.exa-welcome');
    if (w) w.remove();
    messagesEl.appendChild(div);
    scrollToBottom();
    return div;
  }

  function showTyping() {
    var d = document.createElement('div');
    d.className = 'exa-typing'; d.id = 'exa-typing';
    d.innerHTML = '<span></span><span></span><span></span>';
    messagesEl.appendChild(d); scrollToBottom();
  }
  function hideTyping() {
    var el = document.getElementById('exa-typing');
    if (el) el.remove();
  }

  function showError(msg) {
    hideTyping();
    var lastBubble = messagesEl.querySelector('.exa-msg.assistant:last-child');
    if (!lastBubble) lastBubble = addBubble('assistant', '');
    lastBubble.innerHTML = '<em style="color:#F87171">' + esc(msg || 'Error inesperado.') + '</em>';
  }

  // ─── Send message ───
  async function sendMessage() {
    var text = (inputEl.value || '').trim();
    if (!text || isStreaming) return;

    isStreaming = true;
    sendBtn.disabled = true;
    inputEl.value = '';
    inputEl.style.height = 'auto';

    // Quitar sugerencias al enviar primer mensaje
    var allWraps = messagesEl.querySelectorAll('.exa-quick-wrap');
    allWraps.forEach(function (w) { w.remove(); });

    messages.push({ role: 'user', content: text });
    addBubble('user', text);
    showTyping();

    var apiMessages = messages.slice(-CFG.maxHistory);

    var fullText = '';
    var isError = false;
    abortCtrl = new AbortController();

    try {
      var timeoutId = setTimeout(function () { if (abortCtrl) abortCtrl.abort(); }, 60000);
      var resp;
      try {
        resp = await fetch(CFG.apiUrl + '/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            messages: apiMessages,
            page: isPro ? currentPage.id : null,
            page_name: isPro ? currentPage.name : null,
          }),
          signal: abortCtrl.signal,
        });
      } catch (fetchErr) {
        clearTimeout(timeoutId);
        if (fetchErr && fetchErr.name === 'AbortError') {
          throw { _type: 'abort' };
        }
        throw { _type: 'network', message: 'No se pudo conectar al servidor. Verifica tu conexión a internet.' };
      }
      clearTimeout(timeoutId);

      var contentType = (resp.headers.get('content-type') || '').toLowerCase();

      if (!resp.ok) {
        var errData = {};
        try { errData = await resp.json(); } catch (e) { /* body no era JSON */ }
        var errMsg = errData.error || 'Error del servidor (' + resp.status + ')';
        if (errData.whatsapp) errMsg += ' Escribenos por [WhatsApp](' + errData.whatsapp + ').';
        throw { _type: 'server', message: errMsg };
      }

      if (contentType.indexOf('application/json') !== -1) {
        var jsonResp = {};
        try { jsonResp = await resp.json(); } catch (e) { /* body corrupto */ }
        if (jsonResp.error) {
          var msg = jsonResp.error;
          if (jsonResp.whatsapp) msg += ' Escribenos por [WhatsApp](' + jsonResp.whatsapp + ').';
          throw { _type: 'server', message: msg };
        }
        throw { _type: 'server', message: 'Respuesta inesperada del servidor.' };
      }

      if (!resp.body || typeof resp.body.getReader !== 'function') {
        throw { _type: 'server', message: 'Tu navegador no soporta streaming. Actualiza tu navegador.' };
      }

      hideTyping();
      var bubble = addBubble('assistant', '');
      var reader = resp.body.getReader();
      var decoder = new TextDecoder();
      var buffer = '';

      try {
        while (true) {
          var result = await reader.read();
          if (result.done) break;

          buffer += decoder.decode(result.value, { stream: true });
          var lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (var i = 0; i < lines.length; i++) {
            var line = lines[i];
            if (!line.startsWith('data: ')) continue;
            var data;
            try { data = JSON.parse(line.slice(6)); } catch (e) { continue; }

            if (data.type === 'text' && data.text) {
              fullText += data.text;
              bubble.innerHTML = md(fullText);
              scrollToBottom();
            } else if (data.type === 'error') {
              throw { _type: 'stream', message: data.error || 'Error del asistente.' };
            } else if (data.type === 'done') {
              break;
            }
          }
        }
      } finally {
        try { reader.cancel(); } catch (e) { /* ya cerrado */ }
      }

      if (!fullText) {
        throw { _type: 'stream', message: 'El asistente no generó respuesta. Intenta de nuevo.' };
      }

    } catch (err) {
      isError = true;
      var errorText;

      if (err && err._type === 'abort') {
        errorText = '(Mensaje cancelado)';
      } else if (err && err._type === 'network') {
        errorText = err.message;
      } else if (err && err._type === 'server') {
        errorText = err.message;
      } else if (err && err._type === 'stream') {
        errorText = err.message;
      } else if (err && err.name === 'AbortError') {
        errorText = 'Tiempo de espera agotado. Intenta con una pregunta más corta.';
      } else if (err && err.message) {
        errorText = err.message;
      } else {
        errorText = 'Error de conexión. Verifica tu internet e intenta de nuevo.';
      }

      if (!fullText) {
        showError(errorText);
      }
    }

    if (fullText && !isError) {
      messages.push({ role: 'assistant', content: fullText });
      saveHistory();
    } else if (isError) {
      messages.pop();
      saveHistory();
    }

    isStreaming = false;
    sendBtn.disabled = !inputEl.value.trim();
    abortCtrl = null;
  }

  // ─── Init ───
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
