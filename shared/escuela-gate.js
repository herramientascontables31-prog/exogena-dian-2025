/* ═══ ExógenaDIAN — Escuela Access Gate ═══
   Controla el acceso a cursos de la Escuela Contable.
   Cursos gratuitos: iva300.html (no incluir este script ahí).
   El resto requiere plan PRO+Escuela o PRO Anual.

   Uso: <script src="../shared/escuela-gate.js"></script>
   Requiere: ../shared/pro.js cargado antes (o se auto-carga).
*/
(function(){
  'use strict';

  // Cursos gratuitos que NO requieren Escuela
  var FREE_COURSES = ['iva300.html', 'ia-automatizacion.html'];
  var page = location.pathname.split('/').pop() || '';
  if (FREE_COURSES.indexOf(page) !== -1) return;

  function waitForExoPro(cb) {
    if (typeof exoPro !== 'undefined') return cb();
    // Auto-cargar pro.js si no está
    var existing = document.querySelector('script[src*="pro.js"]');
    if (!existing) {
      var s = document.createElement('script');
      s.src = '../shared/pro.js';
      document.head.appendChild(s);
    }
    var tries = 0;
    var iv = setInterval(function(){
      if (typeof exoPro !== 'undefined') { clearInterval(iv); cb(); }
      if (++tries > 100) clearInterval(iv); // 5s timeout
    }, 50);
  }

  function showGate() {
    // Crear overlay que bloquea el contenido
    var overlay = document.createElement('div');
    overlay.id = 'escuela-gate-overlay';
    overlay.style.cssText = 'position:fixed;inset:0;z-index:9999;background:rgba(255,255,255,0.97);display:flex;align-items:center;justify-content:center;padding:24px;';
    overlay.innerHTML =
      '<div style="max-width:480px;text-align:center;font-family:Outfit,sans-serif">' +
        '<div style="width:72px;height:72px;background:#FFF7ED;border:2px solid #FED7AA;border-radius:50%;display:grid;place-items:center;margin:0 auto 20px;font-size:1.8rem">🎓</div>' +
        '<h2 style="font-family:Fraunces,serif;font-size:1.6rem;color:#1F2937;margin-bottom:12px">Este curso requiere Escuela</h2>' +
        '<p style="color:#6B7280;font-size:.95rem;line-height:1.6;margin-bottom:8px">' +
          'Los cursos de la Escuela Contable IA están incluidos en:' +
        '</p>' +
        '<div style="display:flex;flex-direction:column;gap:8px;margin:20px 0;text-align:left">' +
          '<div style="background:#FFF7ED;border:1px solid #FED7AA;border-radius:10px;padding:12px 16px;font-size:.88rem">' +
            '<strong style="color:#EA580C">PRO + Escuela</strong> <span style="color:#9CA3AF">— $39.900/mes</span>' +
          '</div>' +
          '<div style="background:#ECFDF5;border:1px solid #A7F3D0;border-radius:10px;padding:12px 16px;font-size:.88rem">' +
            '<strong style="color:#059669">PRO Anual</strong> <span style="color:#9CA3AF">— $179.900/año (Escuela gratis)</span>' +
          '</div>' +
        '</div>' +
        '<p style="color:#9CA3AF;font-size:.82rem;margin-bottom:20px">El curso de IVA 300 está disponible gratis para todos.</p>' +
        '<div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap">' +
          '<a href="../precios.html" style="padding:12px 28px;background:#EA580C;color:#fff;border-radius:12px;font-weight:700;font-size:.95rem;text-decoration:none;box-shadow:0 4px 14px rgba(234,88,12,.25)">Ver planes →</a>' +
          '<a href="../escuela/iva300.html" style="padding:12px 28px;background:#F3F4F6;color:#374151;border-radius:12px;font-weight:600;font-size:.95rem;text-decoration:none">Curso IVA gratis →</a>' +
        '</div>' +
        '<a href="../escuela.html" style="display:inline-block;margin-top:16px;color:#9CA3AF;font-size:.82rem;text-decoration:none">← Volver a la Escuela</a>' +
      '</div>';
    document.body.appendChild(overlay);
  }

  function checkAccess() {
    waitForExoPro(function(){
      exoPro.check().then(function(isPro){
        if (!isPro) {
          showGate();
          return;
        }
        // Es PRO, verificar si tiene Escuela
        if (!exoPro.hasEscuela()) {
          showGate();
        }
        // Tiene acceso, no hacer nada
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkAccess);
  } else {
    checkAccess();
  }
})();
