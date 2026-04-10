/* ═══ ExógenaDIAN — Google Analytics (compartido) ═══ */
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', 'G-S7SM6ST4CC');

/* ═══ Event Tracking — Conversiones ═══ */
var exoTrack = {
  tool: function(name) {
    gtag('event', 'click_herramienta', { tool_name: name, page: location.pathname });
  },
  generate: function(name, format) {
    gtag('event', 'archivo_generado', { tool_name: name, format: format || 'excel', page: location.pathname });
  },
  clickPro: function(plan) {
    gtag('event', 'click_pro', { plan: plan || 'mensual', page: location.pathname });
  },
  proActivated: function(method) {
    gtag('event', 'pro_activado', { method: method || 'email', page: location.pathname });
  },
  blogRead: function(slug) {
    gtag('event', 'blog_read', { article: slug, page: location.pathname });
  },
  newsletter: function() {
    gtag('event', 'newsletter_signup', { page: location.pathname });
  },
  scroll75: false,

  /* ═══ Conversion Events ═══ */
  ctaClick: function(toolName, destination) {
    gtag('event', 'cta_click', {
      page_location: location.href,
      tool_name: toolName || 'unknown',
      destination: destination || ''
    });
  },
  toolUsed: function(toolName) {
    gtag('event', 'tool_used', {
      page_location: location.href,
      tool_name: toolName || location.pathname.replace(/\.html$/, '').split('/').pop()
    });
  },
  pdfDownloaded: function(toolName) {
    gtag('event', 'pdf_downloaded', {
      page_location: location.href,
      tool_name: toolName || location.pathname.replace(/\.html$/, '').split('/').pop()
    });
  },
  nitConsulted: function(nit) {
    gtag('event', 'nit_consulted', {
      page_location: location.href,
      tool_name: 'consultanit',
      nit_prefix: nit ? String(nit).substring(0, 3) + '***' : ''
    });
  },
  emailCaptured: function(source) {
    gtag('event', 'email_captured', {
      page_location: location.href,
      tool_name: source || 'unknown'
    });
  }
};

/* ═══ Error Tracking — GA4 + alerta email vía Apps Script ═══ */
var _errHook = 'https://script.google.com/macros/s/AKfycbyxVQmTgAoJGoWgmuDZHZQbT44nbn7i6fCg_faSAv4DZDfRhO-gNYzRlpCn7hOpoOAS/exec';
var _errSent = {};
function _reportError(msg, source) {
  var key = msg + source;
  if (_errSent[key]) return;
  _errSent[key] = true;
  gtag('event', 'js_error', {
    error_message: msg.substring(0, 150),
    error_source: source,
    page: location.pathname
  });
  try {
    navigator.sendBeacon(_errHook, JSON.stringify({
      message: msg.substring(0, 300),
      source: source,
      page: location.pathname,
      ua: navigator.userAgent.substring(0, 150)
    }));
  } catch(x) {}
}
window.addEventListener('error', function(e) {
  var msg = e.message || 'Unknown error';
  var source = ((e.filename || '').split('/').pop() || 'unknown') + ':' + (e.lineno || 0);
  _reportError(msg, source);
});
window.addEventListener('unhandledrejection', function(e) {
  var reason = e.reason;
  var msg;
  if (reason && reason.message) {
    msg = reason.message;
  } else if (reason && typeof reason === 'string') {
    msg = reason;
  } else if (reason) {
    try { msg = JSON.stringify(reason).substring(0, 200); } catch(x) { msg = 'Promise rejected (unserializable)'; }
  } else {
    msg = 'Promise rejected (sin detalle)';
  }
  var source = (reason && reason.stack) ? reason.stack.split('\n')[1] || 'promise' : 'promise';
  _reportError(msg, source.trim().substring(0, 100));
});

/* ═══ Auto-track CTA clicks (links to /registro, /pricing, /precios, /planes) ═══ */
document.addEventListener('click', function(e) {
  var link = e.target.closest('a[href]');
  if (!link) return;
  var href = link.getAttribute('href') || '';
  if (/registro|pricing|precios|planes/.test(href)) {
    exoTrack.ctaClick(
      link.textContent.trim().substring(0, 40),
      href.replace(/\.html$/, '').split('/').pop()
    );
  }
});

/* Scroll depth 75% — mide engagement real */
window.addEventListener('scroll', function() {
  if (exoTrack.scroll75) return;
  var scrollPct = (window.scrollY + window.innerHeight) / document.body.scrollHeight;
  if (scrollPct > 0.75) {
    exoTrack.scroll75 = true;
    gtag('event', 'scroll_depth', { percent: 75, page: location.pathname });
  }
});
