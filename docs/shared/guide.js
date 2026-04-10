/* ═══ ExógenaDIAN — Guía Contextual Paso a Paso ═══
   Uso: <script src="shared/guide.js"></script>

   Sistema de tips inteligentes que aparecen según la herramienta
   y el paso en el que está el usuario. 100% frontend, $0 de costo.

   Detecta:
   1. En qué herramienta está el usuario (URL)
   2. En qué paso está (observa el DOM)
   3. Muestra tips relevantes con timing inteligente
*/
(function () {
  'use strict';

  // ═══════════════════════════════════════════════════════════════
  //  TIPS POR HERRAMIENTA Y PASO
  // ═══════════════════════════════════════════════════════════════

  var TIPS = {
    exogena: [
      {
        step: 1,
        trigger: '.drop-zone, [class*="drop"], [class*="upload"]',
        title: 'Tu balance debe tener auxiliar por tercero',
        body: 'Necesitas un balance de prueba con: <strong>c\u00f3digo PUC, nombre de cuenta, NIT del tercero, d\u00e9bitos y cr\u00e9ditos</strong>. No sirve un balance resumido sin terceros.',
        position: 'below'
      },
      {
        step: 2,
        trigger: '.step-pill.active:nth-child(2), [class*="mapper"], [class*="column"]',
        title: 'Verifica las columnas detectadas',
        body: 'La herramienta reconoce <strong>80+ nombres de columnas</strong> autom\u00e1ticamente. Si tu software usa nombres distintos, mapea manualmente aqu\u00ed.',
        position: 'below'
      },
      {
        step: 3,
        trigger: '.step-pill.active:nth-child(3), [class*="clasif"], [class*="review"]',
        title: 'Revisa la clasificaci\u00f3n autom\u00e1tica',
        body: 'Cada cuenta se clasifica por PUC al formato DIAN correcto. <strong>Revisa los conceptos</strong> — especialmente honorarios (1 o 2), arriendos y servicios que pueden variar.',
        position: 'above'
      }
    ],
    iva300: [
      {
        step: 1,
        trigger: '.drop-zone, [class*="drop"], [class*="upload"]',
        title: 'Usa el mismo balance de la ex\u00f3gena',
        body: 'Si ya procesaste ex\u00f3gena, <strong>usa el mismo archivo Excel</strong>. La herramienta detecta las cuentas del grupo 24 (IVA) autom\u00e1ticamente.',
        position: 'below'
      },
      {
        step: 2,
        trigger: '.step-pill.active:nth-child(2)',
        title: '\u00bfBimestral o cuatrimestral?',
        body: '<strong>Bimestral:</strong> ingresos \u2265 92.000 UVT ($4.818.408.000). <strong>Cuatrimestral:</strong> por debajo de ese tope. Art. 600 ET.',
        position: 'below'
      }
    ],
    retencion350: [
      {
        step: 1,
        trigger: '.drop-zone, [class*="drop"], [class*="upload"]',
        title: 'La herramienta lee la cuenta 2365',
        body: 'Busca las subcuentas del grupo <strong>2365 (Retenci\u00f3n en la fuente)</strong> y clasifica por concepto autom\u00e1ticamente: salarios, honorarios, servicios, etc.',
        position: 'below'
      }
    ],
    renta110: [
      {
        step: 1,
        trigger: '.drop-zone, [class*="drop"], [class*="upload"]',
        title: 'Balance completo del a\u00f1o gravable',
        body: 'Necesitas un balance de enero a diciembre con <strong>todas las cuentas</strong> (1xxx a 9xxx). La depuraci\u00f3n fiscal detecta autom\u00e1ticamente 63 tipos de gastos no deducibles.',
        position: 'below'
      }
    ],
    estadosfinancieros: [
      {
        step: 1,
        trigger: '.drop-zone, [class*="drop"], [class*="upload"]',
        title: 'Acepta cualquier balance PUC',
        body: 'Sube tu balance de prueba con saldos finales. La herramienta clasifica autom\u00e1ticamente en <strong>ESF (Activo/Pasivo/Patrimonio)</strong> y <strong>ERI (Ingresos/Costos/Gastos)</strong> seg\u00fan NIIF.',
        position: 'below'
      }
    ],
    conciliacion: [
      {
        step: 1,
        trigger: '.drop-zone, [class*="drop"], [class*="upload"]',
        title: 'Necesitas dos archivos',
        body: '<strong>1)</strong> Libro auxiliar de bancos (Excel contable). <strong>2)</strong> Extracto bancario (Excel del banco). La herramienta cruza ambos por valor y fecha.',
        position: 'below'
      }
    ]
  };

  // ═══════════════════════════════════════════════════════════════
  //  DETECTAR P\u00c1GINA Y ESTADO
  // ═══════════════════════════════════════════════════════════════

  function detectPage() {
    var path = location.pathname.replace(/^\/|\.html$/g, '').replace(/\/+$/, '').replace(/^docs\//, '');
    return path || 'index';
  }

  function getActiveStep() {
    // Intentar detectar el paso activo por varias convenciones
    var active = document.querySelector('.step-pill.active, .step.active, [data-step].active');
    if (active) {
      var num = active.querySelector('.num, .step-num');
      if (num) return parseInt(num.textContent) || 1;
      var idx = Array.from(active.parentElement.children).indexOf(active);
      return idx + 1;
    }
    return 1;
  }

  // ═══════════════════════════════════════════════════════════════
  //  RENDER TIP
  // ═══════════════════════════════════════════════════════════════

  var currentTip = null;
  var dismissed = {};

  function showTip(tip) {
    if (dismissed[tip.title]) return;
    if (currentTip) hideTip();

    var el = document.createElement('div');
    el.className = 'exa-guide-tip';
    el.innerHTML =
      '<div class="exa-guide-header">' +
        '<div class="exa-guide-icon">' +
          '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z"/><line x1="9" y1="21" x2="15" y2="21"/></svg>' +
        '</div>' +
        '<strong class="exa-guide-title">' + tip.title + '</strong>' +
        '<button class="exa-guide-close" aria-label="Cerrar tip">&times;</button>' +
      '</div>' +
      '<p class="exa-guide-body">' + tip.body + '</p>';

    el.querySelector('.exa-guide-close').onclick = function () {
      dismissed[tip.title] = true;
      hideTip();
    };

    document.body.appendChild(el);
    currentTip = el;

    // Animar entrada
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        el.classList.add('exa-guide-visible');
      });
    });

    // Auto-dismiss después de 15s
    setTimeout(function () {
      if (currentTip === el) hideTip();
    }, 15000);
  }

  function hideTip() {
    if (!currentTip) return;
    var el = currentTip;
    el.classList.remove('exa-guide-visible');
    currentTip = null;
    setTimeout(function () {
      if (el.parentElement) el.remove();
    }, 300);
  }

  // ═══════════════════════════════════════════════════════════════
  //  OBSERVADOR — detecta cambios de paso
  // ═══════════════════════════════════════════════════════════════

  function checkAndShowTip(pageTips) {
    var step = getActiveStep();
    var tip = pageTips.find(function (t) {
      // Buscar tip para este paso cuyo trigger exista en el DOM
      if (t.step !== step) return false;
      if (t.trigger) {
        try { return !!document.querySelector(t.trigger); } catch (e) { return false; }
      }
      return true;
    });
    if (tip && !dismissed[tip.title]) {
      showTip(tip);
    }
  }

  // ═══════════════════════════════════════════════════════════════
  //  CSS
  // ═══════════════════════════════════════════════════════════════

  function injectCSS() {
    if (document.getElementById('exa-guide-css')) return;
    var style = document.createElement('style');
    style.id = 'exa-guide-css';
    style.textContent = [
      '.exa-guide-tip{',
      '  position:fixed;bottom:100px;left:24px;z-index:9980;',
      '  max-width:340px;width:calc(100% - 48px);',
      '  background:#0A0F1E;border:1px solid rgba(34,197,94,.25);',
      '  border-radius:16px;padding:16px 18px;',
      '  box-shadow:0 12px 40px rgba(0,0,0,.4),0 0 20px rgba(34,197,94,.06);',
      '  font-family:"Outfit","DM Sans",sans-serif;',
      '  opacity:0;transform:translateY(12px);',
      '  transition:all .3s cubic-bezier(.4,0,.2,1);',
      '  pointer-events:auto;',
      '}',
      '.exa-guide-tip.exa-guide-visible{opacity:1;transform:translateY(0)}',
      '.exa-guide-header{display:flex;align-items:center;gap:8px;margin-bottom:8px}',
      '.exa-guide-icon{',
      '  width:28px;height:28px;border-radius:8px;',
      '  background:rgba(34,197,94,.12);color:#34D399;',
      '  display:grid;place-items:center;flex-shrink:0;',
      '}',
      '.exa-guide-title{font-size:.88rem;color:#F0FDF4;flex:1;line-height:1.3}',
      '.exa-guide-close{',
      '  background:none;border:none;color:rgba(255,255,255,.3);',
      '  font-size:1.1rem;cursor:pointer;padding:4px;',
      '  border-radius:6px;transition:all .2s;flex-shrink:0;',
      '}',
      '.exa-guide-close:hover{color:#fff;background:rgba(255,255,255,.08)}',
      '.exa-guide-body{',
      '  font-size:.82rem;color:#A2B8AE;line-height:1.55;margin:0;',
      '}',
      '.exa-guide-body strong{color:#6EE7B7;font-weight:600}',
      '@media(max-width:900px){',
      '  .exa-guide-tip{bottom:90px;left:16px;max-width:calc(100% - 32px)}',
      '}'
    ].join('\n');
    document.head.appendChild(style);
  }

  // ═══════════════════════════════════════════════════════════════
  //  INIT
  // ═══════════════════════════════════════════════════════════════

  function init() {
    var page = detectPage();
    var pageTips = TIPS[page];
    if (!pageTips || !pageTips.length) return;

    // ─── PRO GATE: tips solo para suscriptores ───
    if (typeof exoPro === 'undefined' || !exoPro.check) return;
    exoPro.check().then(function (isPro) {
      if (!isPro) return; // Free users no ven guías

      injectCSS();

      // Mostrar primer tip después de 2s
      setTimeout(function () {
        checkAndShowTip(pageTips);
      }, 2000);

      // Observar cambios de paso
      var observer = new MutationObserver(function () {
        setTimeout(function () {
          checkAndShowTip(pageTips);
        }, 500);
      });

      observer.observe(document.body, {
        subtree: true,
        attributes: true,
        attributeFilter: ['class'],
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
