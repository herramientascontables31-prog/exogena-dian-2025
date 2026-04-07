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
  scroll75: false
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
  var msg = e.reason ? (e.reason.message || String(e.reason)) : 'Promise rejected';
  _reportError(msg, 'promise');
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
