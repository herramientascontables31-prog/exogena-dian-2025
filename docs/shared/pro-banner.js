/* ═══ ExógenaDIAN — Shared PRO Status Banner ═══
   Uso:
     <script src="shared/pro-banner.js"></script>
   Se auto-inyecta despues del nav o header de cada herramienta.
   Requiere: shared/pro.js cargado antes.
*/
(function(){
  'use strict';

  /* ─── Tool config: page → { free, pro, icon } ─── */
  var TOOLS = {
    'exogena.html':               { free:'3 formatos incluidos',        pro:'10 formatos completos',              icon:'📋' },
    'renta110.html':              { free:'Borrador en pantalla',         pro:'Excel con depuracion completa',      icon:'📄' },
    'iva300.html':                { free:'Formulario completo',          pro:'+ Cruce con facturacion electronica',icon:'🧾' },
    'retencion350.html':          { free:'Formulario completo',          pro:'+ Excel formulado descargable',      icon:'🧾' },
    'estadosfinancieros.html':    { free:'ESF + Estado de Resultados',   pro:'+ Notas, comparativo, flujo, patrimonio', icon:'📊' },
    'conciliacion.html':          { free:'Hasta 100 movimientos',        pro:'Sin limite de movimientos',          icon:'🏦' },
    'consultanit.html':           { free:'10 consultas por dia',         pro:'Consultas ilimitadas',               icon:'🔍' },
    'dashboard.html':             { free:'Vista basica',                 pro:'Dashboard completo con graficos',    icon:'📈' },
    'formato220.html':            { free:'Certificado basico',           pro:'Todas las modalidades',              icon:'📜' },
    'credito.html':               { free:'Simulacion basica',            pro:'Exportacion y comparativo',          icon:'💳' },
    'decreto240.html':            { free:'Consulta basica',              pro:'Busqueda avanzada y exportacion',    icon:'📑' },
    'ia-analisis-balance.html':   { free:'3 analisis por dia',           pro:'30 analisis por dia',                icon:'🤖', dark:true },
    'ia-chat-et.html':            { free:'3 consultas por dia',          pro:'50 consultas por dia',               icon:'⚖️', dark:true },
    'ia-asistente.html':          { free:'3 consultas por dia',          pro:'50 consultas por dia',               icon:'💬', dark:true },
    'ia-respuesta-requerimiento.html': { free:'3 consultas por dia',     pro:'50 consultas por dia',               icon:'📨', dark:true },
    'ia-resumen-declaracion.html':{ free:'3 consultas por dia',          pro:'50 consultas por dia',               icon:'📝', dark:true },
    'ia-inconsistencias.html':    { free:'3 consultas por dia',          pro:'50 consultas por dia',               icon:'🔎', dark:true }
  };

  /* ─── Skip pages that don't need a banner ─── */
  var SKIP = ['index.html','precios.html','blog.html','gracias.html','terminos.html','politica-privacidad.html','404.html','ia.html','sanciones-dian.html','estatutos.html'];

  var page = location.pathname.split('/').pop() || 'index.html';
  if (SKIP.indexOf(page) !== -1) return;

  var tool = TOOLS[page] || null;

  /* ─── Detect if tool is fully free (no config = free tool) ─── */
  var isFreeOnly = !tool;

  /* ─── Styles ─── */
  var style = document.createElement('style');
  style.textContent = `
    /* ===== PRO Status Banner ===== */
    .pro-status-banner {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      padding: 10px 20px;
      font-family: 'Outfit', 'DM Sans', system-ui, sans-serif;
      font-size: 0.84rem;
      line-height: 1.4;
      z-index: 90;
      flex-wrap: wrap;
    }

    /* Light theme (regular tools) */
    .pro-status-banner.light {
      background: linear-gradient(90deg, #ECFDF5 0%, #D1FAE5 50%, #ECFDF5 100%);
      border-bottom: 1px solid #A7F3D0;
      color: #065F46;
    }
    .pro-status-banner.light .psb-badge-free {
      background: #FEF3C7;
      color: #92400E;
      border: 1px solid #FDE68A;
    }
    .pro-status-banner.light .psb-badge-pro {
      background: #059669;
      color: #fff;
      border: 1px solid #047857;
    }
    .pro-status-banner.light .psb-limits {
      color: #374151;
    }
    .pro-status-banner.light .psb-cta {
      background: #059669;
      color: #fff;
    }
    .pro-status-banner.light .psb-cta:hover {
      background: #047857;
    }

    /* Dark theme (IA tools) */
    .pro-status-banner.dark {
      background: linear-gradient(90deg, rgba(5,150,105,0.08) 0%, rgba(5,150,105,0.15) 50%, rgba(5,150,105,0.08) 100%);
      border-bottom: 1px solid rgba(5,150,105,0.2);
      color: #A7F3D0;
    }
    .pro-status-banner.dark .psb-badge-free {
      background: rgba(254,243,199,0.15);
      color: #FDE68A;
      border: 1px solid rgba(253,230,138,0.3);
    }
    .pro-status-banner.dark .psb-badge-pro {
      background: rgba(5,150,105,0.3);
      color: #34D399;
      border: 1px solid rgba(5,150,105,0.5);
    }
    .pro-status-banner.dark .psb-limits {
      color: #D1D5DB;
    }
    .pro-status-banner.dark .psb-cta {
      background: #059669;
      color: #fff;
    }
    .pro-status-banner.dark .psb-cta:hover {
      background: #047857;
    }

    /* Badge pill */
    .psb-badge-free, .psb-badge-pro {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 3px 10px;
      border-radius: 20px;
      font-size: 0.76rem;
      font-weight: 700;
      letter-spacing: 0.02em;
      white-space: nowrap;
      flex-shrink: 0;
    }

    /* Limits text */
    .psb-limits {
      font-size: 0.82rem;
      font-weight: 500;
    }
    .psb-sep {
      opacity: 0.4;
      margin: 0 2px;
    }
    .psb-pro-feature {
      font-weight: 600;
      opacity: 0.75;
    }

    /* CTA button */
    .psb-cta {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 5px 14px;
      border-radius: 8px;
      font-size: 0.78rem;
      font-weight: 700;
      text-decoration: none;
      transition: all 0.2s;
      white-space: nowrap;
      flex-shrink: 0;
    }
    .psb-cta:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(5,150,105,0.3);
    }

    /* Free-only tools: subtle green badge */
    .pro-status-banner.free-tool {
      background: linear-gradient(90deg, #F0FDF4 0%, #ECFDF5 100%);
      border-bottom: 1px solid #D1FAE5;
      color: #065F46;
    }
    .psb-badge-gratis {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 3px 10px;
      border-radius: 20px;
      font-size: 0.76rem;
      font-weight: 700;
      background: #D1FAE5;
      color: #065F46;
      border: 1px solid #A7F3D0;
      white-space: nowrap;
    }

    /* Mobile */
    @media (max-width: 640px) {
      .pro-status-banner {
        padding: 8px 12px;
        gap: 8px;
        font-size: 0.78rem;
      }
      .psb-limits { font-size: 0.76rem; }
      .psb-cta { padding: 4px 10px; font-size: 0.74rem; }
    }
  `;
  document.head.appendChild(style);

  /* ─── Wait for DOM + exoPro ─── */
  function init() {
    if (typeof exoPro === 'undefined') {
      setTimeout(init, 50);
      return;
    }
    exoPro.check().then(function(isPro) {
      render(isPro);
    });
  }

  function render(isPro) {
    var banner = document.createElement('div');
    banner.className = 'pro-status-banner';
    banner.setAttribute('role', 'status');
    banner.setAttribute('aria-label', 'Estado de suscripcion');

    if (isFreeOnly) {
      /* ── Herramienta 100% gratuita ── */
      if (isPro) return; // PRO users don't need to see "free" badge
      banner.classList.add('free-tool');
      banner.innerHTML = '<span class="psb-badge-gratis">✓ Herramienta gratuita</span>' +
        '<span class="psb-limits">Sin limites ni suscripcion</span>';
    } else if (isPro) {
      /* ── PRO activo ── */
      var theme = tool.dark ? 'dark' : 'light';
      banner.classList.add(theme);
      banner.innerHTML = '<span class="psb-badge-pro">✅ PRO activo</span>' +
        '<span class="psb-limits">' + tool.icon + ' Acceso completo — ' + tool.pro + '</span>';
    } else {
      /* ── Free user en herramienta con limites ── */
      var theme = tool.dark ? 'dark' : 'light';
      banner.classList.add(theme);
      banner.innerHTML = '<span class="psb-badge-free">⚡ GRATIS</span>' +
        '<span class="psb-limits">' + tool.icon + ' ' + tool.free +
        ' <span class="psb-sep">·</span> <span class="psb-pro-feature">' + tool.pro + ' con PRO</span></span>' +
        '<a href="precios.html" class="psb-cta">Ver PRO →</a>';
    }

    /* ── Insertion point ── */
    var inserted = false;

    // IA tools: insert at top of .chat-container, after .chat-header
    var chatHeader = document.querySelector('.chat-header');
    if (chatHeader) {
      chatHeader.parentNode.insertBefore(banner, chatHeader.nextSibling);
      inserted = true;
    }

    // Regular tools: insert after nav#nav (rendered by nav.js)
    if (!inserted) {
      var nav = document.querySelector('nav#nav');
      if (nav) {
        nav.parentNode.insertBefore(banner, nav.nextSibling);
        // Add top margin to account for fixed nav
        banner.style.position = 'relative';
        banner.style.zIndex = '90';
        inserted = true;
      }
    }

    // Fallback: insert after nav-container
    if (!inserted) {
      var navContainer = document.getElementById('nav-container');
      if (navContainer) {
        navContainer.parentNode.insertBefore(banner, navContainer.nextSibling);
        inserted = true;
      }
    }

    // Last fallback: prepend to body
    if (!inserted) {
      document.body.insertBefore(banner, document.body.firstChild);
    }
  }

  /* ─── Start ─── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { setTimeout(init, 100); });
  } else {
    setTimeout(init, 100);
  }
})();
