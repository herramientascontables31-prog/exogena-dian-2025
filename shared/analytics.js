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

/* Scroll depth 75% — mide engagement real */
window.addEventListener('scroll', function() {
  if (exoTrack.scroll75) return;
  var scrollPct = (window.scrollY + window.innerHeight) / document.body.scrollHeight;
  if (scrollPct > 0.75) {
    exoTrack.scroll75 = true;
    gtag('event', 'scroll_depth', { percent: 75, page: location.pathname });
  }
});
