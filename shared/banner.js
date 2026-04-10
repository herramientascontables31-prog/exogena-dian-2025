/* ═══ ExógenaDIAN — Standalone Announcement Banner ═══
   For pages that don't load nav.js (blog posts).
   nav.js has this same banner built in.
*/
(function(){
  'use strict';
  if(localStorage.getItem('exo_banner_dismissed_2026')) return;
  var css=document.createElement('style');
  css.textContent='.exo-announce{position:fixed;top:0;left:0;right:0;z-index:9999;background:#0A0F1E;color:#E2E8F0;font-family:"Outfit",sans-serif;padding:10px 20px;display:flex;align-items:center;justify-content:center;gap:12px;font-size:.88rem;flex-wrap:wrap;border-bottom:2px solid #22C55E;box-shadow:0 2px 12px rgba(0,0,0,.4)}.exo-announce-text{display:flex;align-items:center;gap:8px;flex-wrap:wrap;justify-content:center;text-align:center}.exo-announce-cta{display:inline-flex;align-items:center;gap:5px;background:#22C55E;color:#0A0F1E;padding:6px 16px;border-radius:8px;font-weight:700;font-size:.82rem;text-decoration:none;transition:all .2s;white-space:nowrap}.exo-announce-cta:hover{background:#16A34A;color:#fff;transform:translateY(-1px)}.exo-announce-x{background:none;border:none;color:#64748B;font-size:1.2rem;cursor:pointer;padding:4px 8px;margin-left:8px;transition:color .2s;flex-shrink:0}.exo-announce-x:hover{color:#fff}@media(max-width:600px){.exo-announce{font-size:.8rem;padding:8px 12px;gap:8px}.exo-announce-cta{padding:5px 12px;font-size:.78rem}}';
  document.head.appendChild(css);
  var b=document.createElement('div');
  b.className='exo-announce';
  b.setAttribute('role','alert');
  b.innerHTML='<span class="exo-announce-text">\u26A0\uFE0F Vencimientos Informaci\u00F3n Ex\u00F3gena DIAN: <strong>28 de abril</strong> \u2014 Activa tu cuenta antes de la fecha l\u00EDmite</span><a href="https://exogenadian.com/precios.html" class="exo-announce-cta">Activar ahora \u2192</a><button class="exo-announce-x" aria-label="Cerrar anuncio" onclick="this.parentElement.remove();localStorage.setItem(\'exo_banner_dismissed_2026\',\'1\')">&times;</button>';
  document.body.insertAdjacentElement('afterbegin',b);
  requestAnimationFrame(function(){
    var h=b.offsetHeight;
    // Push sticky nav down
    var nav=document.querySelector('nav');
    if(nav&&(getComputedStyle(nav).position==='sticky'||getComputedStyle(nav).position==='fixed')){
      nav.style.top=h+'px';
    }
    document.body.style.paddingTop=(parseInt(document.body.style.paddingTop||'0')+h)+'px';
  });
})();
