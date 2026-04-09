/* ═══ ExógenaDIAN — Exa Chat Widget ═══
   Uso:
     <link rel="stylesheet" href="shared/chat.css">
     <script src="shared/chat.js"></script>

   Config (opcional, antes del script):
     window.EXA_CONFIG = { apiUrl: 'https://tu-backend.com' };
*/
(function () {
  'use strict';

  var WA = 'https://wa.me/573054559574';

  // ─── Config ───
  var CFG = Object.assign({
    apiUrl: 'https://dian-proxy-337146111457.southamerica-east1.run.app',
    maxHistory: 10,       // mensajes enviados a la API (reducido para ahorrar tokens)
    storageKey: 'exa_chat_history',
    whatsapp: WA,
  }, window.EXA_CONFIG || {});

  // ─── State ───
  var isOpen = false;
  var isStreaming = false;
  var messages = [];   // {role, content}
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
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
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
        // Filtrar mensajes válidos
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
    loadHistory();

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
        '<textarea class="exa-input" placeholder="Pregunta sobre impuestos, sanciones, exógena..." rows="1" maxlength="500"></textarea>' +
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

  // ─── Greeting precargado (no gasta tokens) ───
  var GREETING = 'Hola, soy **Exa** — tu asistente contable. Pregunta lo que necesites sobre normas tributarias, sanciones, vencimientos o herramientas del portal.';

  // ─── Render ───
  function renderMessages() {
    if (messages.length === 0) {
      messagesEl.innerHTML = '';
      // Burbuja precargada de Exa (no se guarda en historial API)
      var greet = document.createElement('div');
      greet.className = 'exa-msg assistant';
      greet.innerHTML = md(GREETING);
      messagesEl.appendChild(greet);
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
    d.textContent = s;
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

  // ─── Send message ───
  async function sendMessage() {
    var text = inputEl.value.trim();
    if (!text || isStreaming) return;

    isStreaming = true;
    sendBtn.disabled = true;
    inputEl.value = '';
    inputEl.style.height = 'auto';

    messages.push({ role: 'user', content: text });
    addBubble('user', text);
    showTyping();

    // Solo últimos N mensajes para la API (ahorra tokens)
    var apiMessages = messages.slice(-CFG.maxHistory);

    var fullText = '';
    var isError = false;
    abortCtrl = new AbortController();

    try {
      var resp = await fetch(CFG.apiUrl + '/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: apiMessages }),
        signal: abortCtrl.signal,
      });

      // Leer contenido según content-type
      var contentType = resp.headers.get('content-type') || '';

      if (!resp.ok) {
        var errData;
        try { errData = await resp.json(); } catch (e) { errData = {}; }
        if (errData.whatsapp) {
          throw new Error((errData.error || 'Error') + ' [WhatsApp](' + errData.whatsapp + ')');
        }
        throw new Error(errData.error || 'Error del servidor (' + resp.status + ')');
      }

      // Backend puede devolver JSON directo (budget exceeded, error) con status 200
      if (contentType.includes('application/json')) {
        var jsonResp = await resp.json();
        if (jsonResp.error) {
          var errMsg = jsonResp.error;
          if (jsonResp.whatsapp) errMsg += ' Escríbenos por [WhatsApp](' + jsonResp.whatsapp + ').';
          throw new Error(errMsg);
        }
        // Si no es error pero es JSON, no hay stream que leer
        throw new Error('Respuesta inesperada del servidor. Intenta de nuevo.');
      }

      // Verificar que el body sea streameable antes de intentar leerlo
      if (!resp.body) {
        throw new Error('Error de conexión. El servidor no envió respuesta.');
      }

      hideTyping();
      var bubble = addBubble('assistant', '');

      var reader = resp.body.getReader();
      var decoder = new TextDecoder();
      var buffer = '';

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

          if (data.type === 'text') {
            fullText += data.text;
            bubble.innerHTML = md(fullText);
            scrollToBottom();
          } else if (data.type === 'error') {
            if (!fullText) {
              fullText = data.error;
              bubble.innerHTML = '<em style="color:#F87171">' + esc(data.error) + '</em>';
            }
          } else if (data.type === 'done') {
            break;
          }
        }
      }
    } catch (err) {
      hideTyping();
      isError = true;
      var errorText;
      if (err && err.name === 'AbortError') {
        errorText = '(Mensaje cancelado)';
      } else if (err && err.message) {
        errorText = err.message;
      } else {
        errorText = 'Error de conexión. Verifica tu internet e intenta de nuevo.';
      }
      if (!fullText) {
        var lastBubble = messagesEl.querySelector('.exa-msg.assistant:last-child');
        if (!lastBubble) lastBubble = addBubble('assistant', '');
        lastBubble.innerHTML = '<em style="color:#F87171">' + esc(errorText) + '</em>';
      }
    }

    // Solo guardar respuestas exitosas (no errores) para no contaminar historial
    if (fullText && !isError) {
      messages.push({ role: 'assistant', content: fullText });
      saveHistory();
    } else if (isError) {
      // Quitar también el mensaje del usuario que causó el error
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
