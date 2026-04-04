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

  /* ─── Mega-menu CSS (injected once) ─── */
  var megaCSS=document.createElement('style');
  megaCSS.textContent=`
    /* ===== MEGA MENU ===== */
    .mega-menu{display:none;position:absolute;top:calc(100% + 12px);right:-60px;background:var(--white,#fff);border:1.5px solid var(--gray-200,#E5E7EB);border-radius:16px;padding:20px 24px;min-width:620px;box-shadow:0 16px 48px rgba(0,0,0,.12);z-index:200}
    .nav-dropdown.open .mega-menu{display:grid;grid-template-columns:repeat(4,1fr);gap:20px}
    .mega-col h6{font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.1em;color:var(--gray-400,#9CA3AF);margin-bottom:10px;padding:0 10px}
    .mega-col a{display:flex;align-items:center;gap:9px;padding:8px 10px;border-radius:8px;text-decoration:none;color:var(--gray-600,#4B5563);font-size:.84rem;font-weight:500;transition:all .15s;white-space:nowrap}
    .mega-col a:hover{background:var(--green-50,#ECFDF5);color:var(--green-700,#047857)}
    .mega-col a .dd-icon{width:28px;height:28px;border-radius:7px;display:grid;place-items:center;font-size:.8rem;flex-shrink:0}
    .mega-col .mega-divider{height:1px;background:var(--gray-100,#F3F4F6);margin:6px 10px}

    /* ===== TOOL NAV DROPDOWN CATEGORIES ===== */
    .tn-cat{position:relative}
    .tn-cat-btn{display:inline-flex;align-items:center;gap:4px;padding:6px 14px;border:1px solid #e2e8f0;border-radius:8px;background:#fff;font-size:.82rem;font-weight:600;color:#374151;cursor:pointer;font-family:inherit;transition:all .15s;white-space:nowrap}
    .tn-cat-btn:hover,.tn-cat.open .tn-cat-btn{background:#ECFDF5;border-color:#059669;color:#047857}
    .tn-cat-btn svg{width:12px;height:12px;transition:transform .2s}
    .tn-cat.open .tn-cat-btn svg{transform:rotate(180deg)}
    .tn-dd{display:none;position:absolute;top:calc(100% + 6px);left:0;background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:6px;min-width:180px;box-shadow:0 8px 24px rgba(0,0,0,.1);z-index:200}
    .tn-cat:last-child .tn-dd{left:auto;right:0}
    .tn-cat.open .tn-dd{display:block}
    .tn-dd a{display:block;padding:7px 12px;border-radius:6px;text-decoration:none;color:#4B5563;font-size:.82rem;font-weight:500;transition:all .12s;white-space:nowrap}
    .tn-dd a:hover{background:#ECFDF5;color:#047857}
    .tn-hamburger{display:none;background:none;border:none;font-size:1.3rem;cursor:pointer;padding:6px;color:#374151;flex-shrink:0}

    /* ===== TOOL NAV MOBILE ===== */
    @media(max-width:768px){
      .tn-hamburger{display:block}
      .ed-nav #navLinks{display:none;width:100%;padding-top:8px;border-top:1px solid #e2e8f0;margin-top:8px}
      .ed-nav #navLinks.open{display:flex;flex-wrap:wrap;gap:6px}
      .tn-dd{position:static;box-shadow:none;border:none;padding:2px 0 2px 8px;min-width:auto}
      .tn-cat.open .tn-dd{display:block}
    }

    /* ===== MOBILE MEGA ===== */
    @media(max-width:900px){
      .mega-menu{position:static;transform:none;min-width:auto;box-shadow:none;border:none;padding:8px 0 8px 8px;margin-top:4px}
      .nav-dropdown.open .mega-menu{display:flex;flex-direction:column;gap:12px}
      .mega-col{border-bottom:1px solid var(--gray-100,#F3F4F6);padding-bottom:8px}
      .mega-col:last-child{border-bottom:none}
    }

    /* ===== SKIP LINK ===== */
    .skip-link{position:absolute;top:-100%;left:16px;background:#059669;color:#fff;padding:8px 16px;border-radius:0 0 8px 8px;font-size:.85rem;font-weight:600;z-index:9999;text-decoration:none;transition:top .2s}
    .skip-link:focus{top:0}

    /* ===== FOCUS VISIBLE ===== */
    *:focus-visible{outline:2px solid #10B981;outline-offset:2px;border-radius:4px}

    /* ===== LOADING OVERLAY ===== */
    .exo-loading{position:fixed;inset:0;background:rgba(255,255,255,.85);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:9998;opacity:0;pointer-events:none;transition:opacity .2s}
    .exo-loading.active{opacity:1;pointer-events:auto}
    .exo-loading .spinner{width:40px;height:40px;border:4px solid #E5E7EB;border-top-color:#059669;border-radius:50%;animation:exoSpin .8s linear infinite}
    .exo-loading .spinner-text{margin-top:12px;font-size:.9rem;color:#374151;font-weight:500}
    @keyframes exoSpin{to{transform:rotate(360deg)}}
  `;
  document.head.appendChild(megaCSS);

  /* ─── Skip link (accessibility) ─── */
  var skipLink='<a href="#main" class="skip-link">Ir al contenido</a>';

  /* ─── Tool nav (compact bar for tool pages) ─── */
  var chevron='<svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd"/></svg>';
  var toolNav=skipLink+
  '<nav class="ed-nav" role="navigation" aria-label="Navegación de herramientas" style="display:flex;align-items:center;justify-content:space-between;padding:8px 20px;background:#fff;border-bottom:1px solid #e2e8f0;font-family:Outfit,DM Sans,sans-serif;flex-wrap:wrap">'+
  '  <a href="index.html" style="display:flex;align-items:center;gap:8px;text-decoration:none;color:#1a1a2e;font-weight:800;font-size:.95rem;flex-shrink:0">'+
  '    <div style="width:28px;height:28px;background:linear-gradient(135deg,#059669,#34D399);border-radius:7px;display:grid;place-items:center;color:#fff;font-size:.7rem;font-weight:900">E</div>'+
  '    ExógenaDIAN'+
  '  </a>'+
  '  <button class="tn-hamburger" aria-expanded="false" aria-label="Abrir menú" onclick="var nl=document.getElementById(\'navLinks\');nl.classList.toggle(\'open\');this.setAttribute(\'aria-expanded\',nl.classList.contains(\'open\'))">☰</button>'+
  '  <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap" id="navLinks">'+
       /* Tributarias */
  '    <div class="tn-cat"><button class="tn-cat-btn" onclick="toggleTnCat(this)">Tributarias '+chevron+'</button>'+
  '      <div class="tn-dd">'+
  '        <a href="exogena.html">📊 Exógena DIAN</a>'+
  '        <a href="renta110.html">📑 Renta F110</a>'+
  '        <a href="iva300.html">📋 IVA 300</a>'+
  '        <a href="retencion350.html">🧮 Retención 350</a>'+
  '      </div>'+
  '    </div>'+
       /* Financieras */
  '    <div class="tn-cat"><button class="tn-cat-btn" onclick="toggleTnCat(this)">Financieras '+chevron+'</button>'+
  '      <div class="tn-dd">'+
  '        <a href="estadosfinancieros.html">📄 Estados Financieros</a>'+
  '        <a href="dashboard.html">📊 Dashboard</a>'+
  '        <a href="conciliacion.html">🏦 Conciliación</a>'+
  '      </div>'+
  '    </div>'+
       /* Sanciones */
  '    <div class="tn-cat"><button class="tn-cat-btn" onclick="toggleTnCat(this)">Sanciones '+chevron+'</button>'+
  '      <div class="tn-dd">'+
  '        <a href="sanciones.html">⚖️ Sanciones Exógena</a>'+
  '        <a href="sanciones-dian.html">⚖️ Sanciones DIAN</a>'+
  '        <a href="intereses.html">% Intereses de Mora</a>'+
  '        <a href="retencion-fuente.html">💰 Retención Fuente</a>'+
  '      </div>'+
  '    </div>'+
       /* Laboral + Consultas */
  '    <div class="tn-cat"><button class="tn-cat-btn" onclick="toggleTnCat(this)">Más '+chevron+'</button>'+
  '      <div class="tn-dd">'+
  '        <a href="liquidador.html">👷 Liquidador Laboral</a>'+
  '        <a href="costoreal.html">💰 Costo Empleado</a>'+
  '        <a href="consultanit.html">🔍 Consulta NIT</a>'+
  '        <a href="vencimientos.html">📅 Vencimientos</a>'+
  '        <a href="uvt.html">🔢 Conversor UVT</a>'+
  '      </div>'+
  '    </div>'+
  '  </div>'+
  '  <div style="display:flex;align-items:center;gap:6px;padding:5px 12px;background:#ECFDF5;border:1px solid #A7F3D0;border-radius:8px;font-size:.75rem;font-weight:600;color:#047857;flex-shrink:0;white-space:nowrap" title="Tu archivo se procesa 100% en tu navegador. Nunca se env\u00eda a ning\u00fan servidor.">'+
  '    <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor" style="flex-shrink:0"><path fill-rule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clip-rule="evenodd"/></svg>'+
  '    100% en tu equipo'+
  '  </div>'+
  '</nav>';

  /* ─── Full nav (index.html, blog.html — mega-menu + PRO + hamburger) ─── */
  var fullNav=skipLink+
  '<nav id="nav" role="navigation" aria-label="Navegación principal">'+
  '  <a href="index.html" class="logo">'+
  '    <div class="logo-mark">E</div>'+
  '    <div>ExógenaDIAN<small>Portal Contable</small></div>'+
  '  </a>'+
  '  <div class="nav-links" id="navLinks">'+
       /* Links directos de alto tráfico */
  '    <a href="exogena.html">Exógena</a>'+
  '    <a href="renta110.html">Renta F110</a>'+
       /* Mega-menu dropdown */
  '    <div class="nav-dropdown" id="navDropdown">'+
  '      <button class="nav-dropdown-toggle" aria-expanded="false" aria-haspopup="true" aria-label="Abrir menú de herramientas" onclick="var dd=document.getElementById(\'navDropdown\');dd.classList.toggle(\'open\');this.setAttribute(\'aria-expanded\',dd.classList.contains(\'open\'))">'+
  '        Herramientas <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd"/></svg>'+
  '      </button>'+
  '      <div class="mega-menu">'+
           /* ── Col 1: Tributarias ── */
  '        <div class="mega-col">'+
  '          <h6>Tributarias</h6>'+
  '          <a href="exogena.html"><div class="dd-icon" style="background:#ECFDF5">📊</div> Exógena DIAN</a>'+
  '          <a href="renta110.html"><div class="dd-icon" style="background:#F5F3FF">📑</div> Renta F110</a>'+
  '          <a href="iva300.html"><div class="dd-icon" style="background:#FFFBEB">📋</div> IVA 300</a>'+
  '          <a href="retencion350.html"><div class="dd-icon" style="background:#EFF6FF">🧮</div> Retención 350</a>'+
  '        </div>'+
           /* ── Col 2: Financieras ── */
  '        <div class="mega-col">'+
  '          <h6>Financieras</h6>'+
  '          <a href="estadosfinancieros.html"><div class="dd-icon" style="background:#ECFDF5">📄</div> Estados Financieros</a>'+
  '          <a href="dashboard.html"><div class="dd-icon" style="background:#1E293B">📊</div> Dashboard</a>'+
  '          <a href="conciliacion.html"><div class="dd-icon" style="background:#ECFEFF">🏦</div> Conciliación Bancaria</a>'+
  '        </div>'+
           /* ── Col 3: Sanciones y Mora ── */
  '        <div class="mega-col">'+
  '          <h6>Sanciones y Mora</h6>'+
  '          <a href="sanciones.html"><div class="dd-icon" style="background:#FFFBEB">⚖️</div> Sanciones Exógena</a>'+
  '          <a href="sanciones-dian.html"><div class="dd-icon" style="background:#EFF6FF">⚖️</div> Sanciones DIAN</a>'+
  '          <a href="intereses.html"><div class="dd-icon" style="background:#FFF1F2">%</div> Intereses de Mora</a>'+
  '          <a href="retencion-fuente.html"><div class="dd-icon" style="background:#EFF6FF">💰</div> Retención Fuente</a>'+
  '        </div>'+
           /* ── Col 4: Laboral + Consultas ── */
  '        <div class="mega-col">'+
  '          <h6>Laboral</h6>'+
  '          <a href="liquidador.html"><div class="dd-icon" style="background:#ECFDF5">👷</div> Liquidador Laboral</a>'+
  '          <a href="costoreal.html"><div class="dd-icon" style="background:#DBEAFE">💰</div> Costo Empleado</a>'+
  '          <div class="mega-divider"></div>'+
  '          <h6>Consultas</h6>'+
  '          <a href="consultanit.html"><div class="dd-icon" style="background:#F5F3FF">🔍</div> Consulta NIT</a>'+
  '          <a href="vencimientos.html"><div class="dd-icon" style="background:#FFF1F2">📅</div> Vencimientos</a>'+
  '        </div>'+
  '      </div>'+
  '    </div>'+
       /* Blog y PRO */
  '    <a href="blog.html">Blog</a>'+
       /* PRO Login */
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
  '  <button class="hamburger" id="hamburger" aria-expanded="false" aria-label="Abrir menú" onclick="var nl=document.getElementById(\'navLinks\');nl.classList.toggle(\'open\');this.setAttribute(\'aria-expanded\',nl.classList.contains(\'open\'))">☰</button>'+
  '</nav>';

  /* ─── Inject ─── */
  var html=(variant==='full')?fullNav:toolNav;
  if(container){
    container.outerHTML=html;
  }else{
    document.body.insertAdjacentHTML('afterbegin',html);
  }

  /* ─── Tool nav dropdown toggle ─── */
  window.toggleTnCat=function(btn){
    var cat=btn.parentElement;
    var wasOpen=cat.classList.contains('open');
    // Close all other dropdowns
    document.querySelectorAll('.tn-cat.open').forEach(function(c){c.classList.remove('open')});
    if(!wasOpen)cat.classList.add('open');
  };
  // Close tool nav dropdowns on outside click
  document.addEventListener('click',function(e){
    if(!e.target.closest('.tn-cat')){
      document.querySelectorAll('.tn-cat.open').forEach(function(c){c.classList.remove('open')});
    }
  });
  // Close on Escape
  document.addEventListener('keydown',function(e){
    if(e.key==='Escape'){
      document.querySelectorAll('.tn-cat.open').forEach(function(c){c.classList.remove('open')});
    }
  });

  /* ─── Highlight current page ─── */
  var links=document.querySelectorAll('#navLinks a[href]');
  links.forEach(function(a){
    var href=a.getAttribute('href');
    if(href===page||(page===''&&href==='index.html')){
      a.style.color='#059669';
      a.style.fontWeight='700';
    }
  });
  // Also highlight in mega-menu and tool nav dropdowns
  var ddLinks=document.querySelectorAll('.mega-col a[href], .tn-dd a[href]');
  ddLinks.forEach(function(a){
    if(a.getAttribute('href')===page){
      a.style.color='#059669';
      a.style.fontWeight='700';
      a.style.background='#ECFDF5';
      // Also highlight parent category button
      var cat=a.closest('.tn-cat');
      if(cat){var btn=cat.querySelector('.tn-cat-btn');if(btn){btn.style.borderColor='#059669';btn.style.color='#047857'}}
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
    // Close on Escape key
    document.addEventListener('keydown',function(e){
      if(e.key==='Escape'){
        var dd=document.getElementById('navDropdown');
        if(dd){dd.classList.remove('open');var btn=dd.querySelector('.nav-dropdown-toggle');if(btn){btn.setAttribute('aria-expanded','false');btn.focus()}}
        var nl=document.getElementById('navLinks');
        var hb=document.getElementById('hamburger');
        if(nl&&nl.classList.contains('open')){nl.classList.remove('open');if(hb){hb.setAttribute('aria-expanded','false');hb.focus()}}
      }
    });
    // Scroll effect
    window.addEventListener('scroll',function(){
      var nav=document.getElementById('nav');
      if(nav){nav.classList.toggle('scrolled',window.scrollY>20)}
    });
  }

  /* ─── PRO Nav Functions (uses shared/pro.js if available, standalone fallback) ─── */
  function showProActive(){
    var login=document.getElementById('proNavLogin');
    var active=document.getElementById('proNavActive');
    if(login)login.style.display='none';
    if(active)active.style.display='flex';
    if(typeof window.onProStatusChange==='function')window.onProStatusChange(true);
  }

  function showProLogin(){
    var login=document.getElementById('proNavLogin');
    var active=document.getElementById('proNavActive');
    var sub=document.getElementById('proNavSubscribe');
    if(login)login.style.display='flex';
    if(active)active.style.display='none';
    if(sub)sub.style.display='none';
    if(typeof window.onProStatusChange==='function')window.onProStatusChange(false);
  }

  window.activarProNav=function(){
    var el=document.getElementById('proNavKey');
    if(!el)return;
    var key=el.value.trim().toLowerCase();
    if(!key)return;
    // Use shared module if available
    if(window.exoPro){
      window.exoPro.activate(key).then(function(valid){
        if(valid){showProActive()}
        else{exoToast('Clave PRO no válida o expirada','warning')}
      });
      return;
    }
    // Standalone fallback
    var url=APPS_SCRIPT_URL+'?action=validateEmail&email='+encodeURIComponent(key);
    fetch(url).then(function(r){return r.json()}).then(function(d){
      if(d.valid){
        localStorage.setItem('exogenadian_pro_email',key);
        showProActive();
      }else{
        exoToast(d.message||'Clave PRO no válida o expirada','warning');
      }
    }).catch(function(){exoToast('Error al verificar. Intenta de nuevo.','error')});
  };

  window.cerrarProNav=function(){
    if(window.exoPro){
      window.exoPro.clearPro();
    } else {
      localStorage.removeItem('exogenadian_pro_email');
      localStorage.removeItem('exogenadian_pro_key');
    }
    showProLogin();
  };

  // Auto-restore PRO from localStorage (with server validation if pro.js loaded)
  var savedPro=localStorage.getItem('exogenadian_pro_email')||localStorage.getItem('exogenadian_pro_key');
  // Also check old keys for backward compat
  if(!savedPro){
    var oldKey=localStorage.getItem('proKey');
    if(oldKey){
      savedPro=oldKey;
      // Migrate
      if(oldKey.includes('@')){localStorage.setItem('exogenadian_pro_email',oldKey)}
      else{localStorage.setItem('exogenadian_pro_key',oldKey)}
      localStorage.removeItem('proKey');
      localStorage.removeItem('proName');
    }
  }
  if(savedPro){
    if(window.exoPro){
      window.exoPro.check().then(function(valid){
        if(valid){showProActive()}else{showProLogin()}
      });
    } else {
      showProActive();
    }
  }

})();
