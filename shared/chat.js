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

  // ─── Load/save history ───
  function loadHistory() {
    try {
      var data = localStorage.getItem(CFG.storageKey);
      if (data) messages = JSON.parse(data);
    } catch (e) { /* ignore */ }
  }
  function saveHistory() {
    try {
      localStorage.setItem(CFG.storageKey, JSON.stringify(messages.slice(-20)));
    } catch (e) { /* ignore */ }
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
        '<a class="exa-wa-btn" href="' + CFG.whatsapp + '" target="_blank" rel="noopener" aria-label="WhatsApp" title="Hablar con un humano">' +
          '<svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>' +
        '</a>' +
        '<button class="exa-close" aria-label="Cerrar chat">&times;</button>' +
      '</div>' +
      '<div class="exa-messages"></div>' +
      '<div class="exa-input-area">' +
        '<textarea class="exa-input" placeholder="Pregunta sobre impuestos, sanciones, exógena..." rows="1" maxlength="500"></textarea>' +
        '<button class="exa-send" aria-label="Enviar" disabled>' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>' +
        '</button>' +
      '</div>' +
      '<div class="exa-footer">Exa puede cometer errores · <a href="' + CFG.whatsapp + '" target="_blank" rel="noopener">Soporte humano por WhatsApp</a></div>';

    document.body.appendChild(fab);
    document.body.appendChild(panel);

    messagesEl = panel.querySelector('.exa-messages');
    inputEl = panel.querySelector('.exa-input');
    sendBtn = panel.querySelector('.exa-send');

    panel.querySelector('.exa-close').onclick = togglePanel;
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

  // ─── Render ───
  function renderMessages() {
    if (messages.length === 0) {
      messagesEl.innerHTML =
        '<div class="exa-welcome">' +
          '<div class="exa-welcome-icon">E</div>' +
          '<h4>Hola, soy Exa</h4>' +
          '<p>Tu asistente contable de ExógenaDIAN. Pregunta sobre normas tributarias, sanciones, vencimientos o cualquier herramienta del portal.</p>' +
          '<div class="exa-quick">' +
            '<button data-q="¿Cuándo vence la exógena 2025?">Vencimientos exógena</button>' +
            '<button data-q="¿Cómo calculo la sanción por extemporaneidad?">Sanciones</button>' +
            '<button data-q="¿Qué herramientas son gratis?">Gratis vs PRO</button>' +
            '<button data-q="¿Cuánto es el UVT 2026?">UVT 2026</button>' +
          '</div>' +
          '<div class="exa-wa-card">' +
            '<a href="' + CFG.whatsapp + '" target="_blank" rel="noopener">' +
              '<svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>' +
              ' Prefiero hablar con un humano' +
            '</a>' +
          '</div>' +
        '</div>';
      messagesEl.querySelectorAll('.exa-quick button').forEach(function (btn) {
        btn.onclick = function () {
          inputEl.value = btn.getAttribute('data-q');
          sendBtn.disabled = false;
          sendMessage();
        };
      });
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
    abortCtrl = new AbortController();

    try {
      var resp = await fetch(CFG.apiUrl + '/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: apiMessages }),
        signal: abortCtrl.signal,
      });

      if (!resp.ok) {
        var errData;
        try { errData = await resp.json(); } catch (e) { errData = {}; }
        // Si el rate limit incluye whatsapp, mostrar link
        if (errData.whatsapp) {
          throw new Error(errData.error + ' [WhatsApp](' + errData.whatsapp + ')');
        }
        throw new Error(errData.error || 'Error ' + resp.status);
      }

      var contentType = resp.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        var jsonResp = await resp.json();
        if (jsonResp.error) {
          var errMsg = jsonResp.error;
          if (jsonResp.whatsapp) errMsg += ' Escríbenos por [WhatsApp](' + jsonResp.whatsapp + ').';
          throw new Error(errMsg);
        }
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
      if (err.name === 'AbortError') {
        fullText = fullText || '(Mensaje cancelado)';
      } else {
        var errorText = err.message || 'Error de conexión. Intenta de nuevo.';
        if (!fullText) {
          fullText = errorText;
          var lastBubble = messagesEl.querySelector('.exa-msg.assistant:last-child');
          if (!lastBubble) lastBubble = addBubble('assistant', '');
          lastBubble.innerHTML = '<em style="color:#F87171">' + md(errorText) + '</em>';
        }
      }
    }

    if (fullText) {
      messages.push({ role: 'assistant', content: fullText });
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
