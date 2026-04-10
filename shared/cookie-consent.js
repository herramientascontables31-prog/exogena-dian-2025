/* ═══ ExógenaDIAN — Cookie Consent Banner (Google Consent Mode v2) ═══
   Carga ANTES de gtag. Bloquea analytics hasta aceptar.
   Guarda preferencia en localStorage.
*/
(function(){
  'use strict';

  var STORAGE_KEY = 'exo_cookie_consent'; // 'granted' | 'denied'
  var saved = localStorage.getItem(STORAGE_KEY);

  /* ─── Set default consent state ─── */
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  window.gtag = gtag;

  gtag('consent', 'default', {
    analytics_storage: saved === 'granted' ? 'granted' : 'denied',
    ad_storage: 'denied',
    ad_user_data: 'denied',
    ad_personalization: 'denied',
    wait_for_update: 500
  });

  /* If already answered, don't show banner */
  if (saved) return;

  /* ─── Inject CSS ─── */
  var css = document.createElement('style');
  css.textContent =
    '.exo-cookie{position:fixed;bottom:0;left:0;right:0;z-index:9998;background:#0A0F1E;color:#CBD5E1;font-family:"Outfit",sans-serif;padding:14px 20px;display:flex;align-items:center;justify-content:center;gap:12px;font-size:.85rem;flex-wrap:wrap;border-top:1px solid #1E293B;box-shadow:0 -4px 20px rgba(0,0,0,.4)}' +
    '.exo-cookie a{color:#22C55E;text-decoration:underline}' +
    '.exo-cookie-btns{display:flex;gap:8px;flex-shrink:0}' +
    '.exo-cookie-btn{padding:7px 18px;border-radius:8px;font-weight:700;font-size:.82rem;cursor:pointer;border:none;font-family:inherit;transition:all .2s}' +
    '.exo-cookie-accept{background:#22C55E;color:#0A0F1E}' +
    '.exo-cookie-accept:hover{background:#16A34A;color:#fff}' +
    '.exo-cookie-deny{background:transparent;color:#94A3B8;border:1px solid #334155}' +
    '.exo-cookie-deny:hover{border-color:#64748B;color:#E2E8F0}' +
    '@media(max-width:600px){.exo-cookie{font-size:.78rem;padding:12px 14px;gap:8px;flex-direction:column;text-align:center}}';
  document.head.appendChild(css);

  /* ─── Create banner ─── */
  var banner = document.createElement('div');
  banner.className = 'exo-cookie';
  banner.setAttribute('role', 'dialog');
  banner.setAttribute('aria-label', 'Consentimiento de cookies');
  banner.innerHTML =
    '<span>Usamos cookies de Google Analytics para mejorar el servicio. No recopilamos datos personales. <a href="politica-privacidad.html">Pol\u00edtica de privacidad</a></span>' +
    '<div class="exo-cookie-btns">' +
    '  <button class="exo-cookie-btn exo-cookie-accept">Aceptar</button>' +
    '  <button class="exo-cookie-btn exo-cookie-deny">Rechazar</button>' +
    '</div>';

  /* ─── Wait for body ─── */
  function inject() {
    document.body.appendChild(banner);

    banner.querySelector('.exo-cookie-accept').addEventListener('click', function() {
      localStorage.setItem(STORAGE_KEY, 'granted');
      gtag('consent', 'update', { analytics_storage: 'granted' });
      banner.remove();
    });

    banner.querySelector('.exo-cookie-deny').addEventListener('click', function() {
      localStorage.setItem(STORAGE_KEY, 'denied');
      banner.remove();
    });
  }

  if (document.body) inject();
  else document.addEventListener('DOMContentLoaded', inject);
})();
