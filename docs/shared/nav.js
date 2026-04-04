/* ═══ ExógenaDIAN — Shared Navigation Component ═══
   Uso:
     Paginas principales (index, blog):
       <div id="nav-container" data-variant="full"></div>
       <script src="shared/nav.js"></script>

     Paginas de herramientas:
       <div id="nav-container"></div>
       <script src="shared/nav.js"></script>
*/
(function(){
  'use strict';

  /* ─── Security: inject CSP meta tag if not present ─── */
  if(!document.querySelector('meta[http-equiv="Content-Security-Policy"]')){
    var csp=document.createElement('meta');
    csp.httpEquiv='Content-Security-Policy';
    csp.content="frame-ancestors 'none'; object-src 'none'; base-uri 'self'";
    document.head.appendChild(csp);
  }

  var APPS_SCRIPT_URL='https://script.google.com/macros/s/AKfycbwT5ofExiwOKKLnBlwH6Uqhs4cdDpaieSiLn2dYf5D-6yPIdJ_9XEWeIGYyq1ViNKiasQ/exec';
  var container=document.getElementById('nav-container');
  var variant=(container&&container.getAttribute('data-variant'))||'tool';
  var page=location.pathname.split('/').pop()||'index.html';

  /* ─── Tool nav (compact bar for exogena, renta, iva, etc.) ─── */
  var toolNav=
  '<nav class="ed-nav" style="display:flex;align-items:center;justify-content:space-between;padding:10px 20px;background:#fff;border-bottom:1px solid #e2e8f0;font-family:\'Outfit\',\'DM Sans\',sans-serif">'+
  '  <a href="index.html" style="display:flex;align-items:center;gap:8px;text-decoration:none;color:#1a1a2e;font-weight:800;font-size:.95rem">'+
  '    <div style="width:28px;height:28px;background:linear-gradient(135deg,#059669,#34D399);border-radius:7px;display:grid;place-items:center;color:#fff;font-size:.7rem;font-weight:900">E</div>'+
  '    ExógenaDIAN'+
  '  </a>'+
  '  <div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap" id="navLinks">'+
  '    <a href="exogena.html" style="font-size:.82rem;color:#6b7280;text-decoration:none">Exógena</a>'+
  '    <a href="renta110.html" style="font-size:.82rem;color:#6b7280;text-decoration:none">Renta</a>'+
  '    <a href="consultanit.html" style="font-size:.82rem;color:#6b7280;text-decoration:none">Consulta NIT</a>'+
  '    <a href="conciliacion.html" style="font-size:.82rem;color:#6b7280;text-decoration:none">Conciliaciones</a>'+
  '    <a href="iva300.html" style="font-size:.82rem;color:#6b7280;text-decoration:none">IVA 300</a>'+
  '    <a href="retencion350.html" style="font-size:.82rem;color:#6b7280;text-decoration:none">Ret 350</a>'+
  '    <a href="estadosfinancieros.html" style="font-size:.82rem;color:#6b7280;text-decoration:none">EEFF</a>'+
  '    <a href="dashboard.html" style="font-size:.82rem;color:#6b7280;text-decoration:none">Dashboard</a>'+
  '    <a href="intereses.html" style="font-size:.82rem;color:#6b7280;text-decoration:none">Intereses</a>'+
  '    <a href="sanciones.html" style="font-size:.82rem;color:#6b7280;text-decoration:none">Sanciones</a>'+
  '    <a href="index.html" style="font-size:.82rem;color:#6b7280;text-decoration:none">&larr; Inicio</a>'+
  '  </div>'+
  '</nav>';

  /* ─── Full nav (index.html, blog.html — with dropdown, PRO, hamburger) ─── */
  var fullNav=
  '<nav id="nav">'+
  '  <a href="index.html" class="logo">'+
  '    <div class="logo-mark">E</div>'+
  '    <div>ExógenaDIAN<small>Portal Contable</small></div>'+
  '  </a>'+
  '  <div class="nav-links" id="navLinks">'+
  '    <a href="exogena.html">Exógena</a>'+
  '    <a href="renta110.html">Renta</a>'+
  '    <a href="consultanit.html">Consulta NIT</a>'+
  '    <a href="conciliacion.html">Conciliaciones</a>'+
  '    <div class="nav-dropdown" id="navDropdown">'+
  '      <button class="nav-dropdown-toggle" onclick="document.getElementById(\'navDropdown\').classList.toggle(\'open\')">'+
  '        Herramientas <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd"/></svg>'+
  '      </button>'+
  '      <div class="nav-dropdown-menu">'+
  '        <a href="iva300.html"><div class="dd-icon" style="background:var(--amber-50)">📋</div> IVA 300</a>'+
  '        <a href="retencion350.html"><div class="dd-icon" style="background:var(--blue-50)">🧮</div> Retención 350</a>'+
  '        <a href="estadosfinancieros.html"><div class="dd-icon" style="background:var(--green-50)">📄</div> Estados Financieros</a>'+
  '        <a href="vencimientos.html"><div class="dd-icon" style="background:var(--purple-50)">📅</div> Vencimientos</a>'+
  '        <a href="dashboard.html"><div class="dd-icon" style="background:#1E293B">📊</div> Dashboard</a>'+
  '        <a href="intereses.html"><div class="dd-icon" style="background:var(--rose-50)">%</div> Intereses Mora</a>'+
  '        <a href="sanciones.html"><div class="dd-icon" style="background:var(--amber-50)">⚖️</div> Sanciones</a>'+
  '        <a href="blog.html"><div class="dd-icon" style="background:var(--blue-50)">📝</div> Blog</a>'+
  '      </div>'+
  '    </div>'+
  '    <div id="proNavLogin" style="display:flex;align-items:center;gap:6px">'+
  '      <input type="email" id="proNavKey" placeholder="Email PRO" style="padding:5px 10px;border:1px solid var(--gray-200);border-radius:8px;font-size:.78rem;font-family:inherit;width:170px;text-align:center">'+
  '      <button onclick="activarProNav()" style="padding:5px 10px;background:var(--green-600);color:#fff;border:none;border-radius:8px;font-size:.75rem;font-weight:600;cursor:pointer">Activar</button>'+
  '    </div>'+
  '    <div id="proNavActive" style="display:none;align-items:center;gap:8px">'+
  '      <span style="background:var(--green-100);color:var(--green-700);padding:4px 12px;border-radius:20px;font-size:.78rem;font-weight:700">PRO</span>'+
  '      <a href="#" onclick="cerrarProNav();return false" style="font-size:.7rem;color:var(--gray-400);text-decoration:none">salir</a>'+
  '    </div>'+
  '    <a href="#planes" id="proNavSubscribe" class="btn btn-green btn-sm" style="display:none">PRO &rarr;</a>'+
  '  </div>'+
  '  <button class="hamburger" id="hamburger" onclick="document.getElementById(\'navLinks\').classList.toggle(\'open\')">☰</button>'+
  '</nav>';

  /* ─── Inject ─── */
  var html=(variant==='full')?fullNav:toolNav;
  if(container){
    container.outerHTML=html;
  }else{
    document.body.insertAdjacentHTML('afterbegin',html);
  }

  /* ─── Highlight current page ─── */
  var links=document.querySelectorAll('#navLinks a[href]');
  links.forEach(function(a){
    var href=a.getAttribute('href');
    if(href===page||(page===''&&href==='index.html')){
      a.style.color='#059669';
      a.style.fontWeight='700';
    }
  });
  // Also highlight in dropdown menu
  var ddLinks=document.querySelectorAll('.nav-dropdown-menu a[href]');
  ddLinks.forEach(function(a){
    if(a.getAttribute('href')===page){
      a.style.color='#059669';
      a.style.fontWeight='700';
    }
  });

  /* ─── Event listeners (full nav only) ─── */
  if(variant==='full'){
    // Close dropdown on outside click
    document.addEventListener('click',function(e){
      var dd=document.getElementById('navDropdown');
      if(dd&&!dd.contains(e.target)){dd.classList.remove('open')}
    });
    // Close mobile menu on link click
    document.querySelectorAll('#navLinks a').forEach(function(a){
      a.addEventListener('click',function(){
        document.getElementById('navLinks').classList.remove('open');
      });
    });
    // Scroll effect
    window.addEventListener('scroll',function(){
      var nav=document.getElementById('nav');
      if(nav){nav.classList.toggle('scrolled',window.scrollY>20)}
    });
  }

  /* ─── PRO Nav Functions ─── */
  window.activarProNav=function(){
    var el=document.getElementById('proNavKey');
    if(!el)return;
    var key=el.value.trim();
    if(!key)return;
    var url=APPS_SCRIPT_URL+'?action=validateEmail&email='+encodeURIComponent(key);
    fetch(url).then(function(r){return r.json()}).then(function(d){
      if(d.valid){
        localStorage.setItem('proKey',key);
        localStorage.setItem('proName',d.name||'PRO');
        showProActive();
      }else{
        alert(d.message||'Clave PRO no válida o expirada');
      }
    }).catch(function(){alert('Error al verificar. Intenta de nuevo.')});
  };

  window.cerrarProNav=function(){
    localStorage.removeItem('proKey');
    localStorage.removeItem('proName');
    var login=document.getElementById('proNavLogin');
    var active=document.getElementById('proNavActive');
    var sub=document.getElementById('proNavSubscribe');
    if(login)login.style.display='flex';
    if(active)active.style.display='none';
    if(sub)sub.style.display='none';
    if(typeof window.onProStatusChange==='function')window.onProStatusChange(false);
  };

  function showProActive(){
    var login=document.getElementById('proNavLogin');
    var active=document.getElementById('proNavActive');
    if(login)login.style.display='none';
    if(active)active.style.display='flex';
    if(typeof window.onProStatusChange==='function')window.onProStatusChange(true);
  }

  // Auto-restore PRO from localStorage
  if(localStorage.getItem('proKey')){
    showProActive();
  }
})();
