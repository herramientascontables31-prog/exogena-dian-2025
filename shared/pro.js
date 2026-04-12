/* ═══ ExógenaDIAN — Shared PRO Validation Module ═══
   Uso:
     <script src="shared/pro.js"></script>
     <script>
       // Verificar si el usuario es PRO (con caché de 1h)
       exoPro.check().then(isPro => { ... });
       // Forzar re-validación (ignora caché)
       exoPro.revalidate().then(isPro => { ... });
       // Obtener email/clave guardada
       exoPro.getSaved(); // returns string or null
     </script>

   Claves localStorage unificadas:
     - exogenadian_pro_email   (email del suscriptor)
     - exogenadian_pro_key     (clave PRO alternativa)
     - exogenadian_device_id   (fingerprint de dispositivo)

   Caché:
     - sessionStorage: exogenadian_pro_valid (timestamp de última validación exitosa)
     - Duración: 1 hora
*/
(function(){
  'use strict';

  var APPS_SCRIPT_URL='https://script.google.com/macros/s/AKfycbwT5ofExiwOKKLnBlwH6Uqhs4cdDpaieSiLn2dYf5D-6yPIdJ_9XEWeIGYyq1ViNKiasQ/exec';
  var CACHE_KEY='exogenadian_pro_valid';
  var CACHE_DURATION=60*60*1000; // 1 hora

  // Claves estándar
  var KEY_EMAIL='exogenadian_pro_email';
  var KEY_PRO='exogenadian_pro_key';
  var KEY_DEVICE='exogenadian_device_id';
  var KEY_ACTIVATED='exogenadian_pro_activated_at';
  var KEY_PLAN='exogenadian_pro_plan';       // pro | pro+escuela | pro-anual
  var KEY_ESCUELA='exogenadian_pro_escuela'; // true | false
  var PRO_MAX_DAYS=395; // 365 días + 30 de gracia

  // --- Backward compatibility: migrate old keys ---
  function migrateOldKeys(){
    // nav.js usaba proKey/proName
    var oldKey=localStorage.getItem('proKey');
    if(oldKey && !localStorage.getItem(KEY_EMAIL) && !localStorage.getItem(KEY_PRO)){
      if(oldKey.includes('@')){
        localStorage.setItem(KEY_EMAIL, oldKey);
      } else {
        localStorage.setItem(KEY_PRO, oldKey);
      }
    }
    // Limpiar claves viejas
    localStorage.removeItem('proKey');
    localStorage.removeItem('proName');
  }

  function getDeviceFingerprint(){
    var uid=localStorage.getItem(KEY_DEVICE);
    if(!uid){
      uid='D-'+(crypto.randomUUID?crypto.randomUUID():([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g,function(c){return(c^(crypto.getRandomValues(new Uint8Array(1))[0]&(15>>c/4))).toString(16)})).split('-').slice(0,2).join('');
      localStorage.setItem(KEY_DEVICE, uid);
    }
    return uid;
  }

  function getSaved(){
    return localStorage.getItem(KEY_EMAIL) || localStorage.getItem(KEY_PRO) || null;
  }

  function clearPro(){
    localStorage.removeItem(KEY_EMAIL);
    localStorage.removeItem(KEY_PRO);
    localStorage.removeItem(KEY_ACTIVATED);
    localStorage.removeItem(KEY_PLAN);
    localStorage.removeItem(KEY_ESCUELA);
    sessionStorage.removeItem(CACHE_KEY);
  }

  function isLocallyExpired(){
    var activated=localStorage.getItem(KEY_ACTIVATED);
    if(!activated) return false; // Sin fecha, dejar que el server valide
    var days=(Date.now()-parseInt(activated,10))/(1000*60*60*24);
    return days>PRO_MAX_DAYS;
  }

  function isCacheValid(){
    var ts=sessionStorage.getItem(CACHE_KEY);
    if(!ts) return false;
    return (Date.now() - parseInt(ts,10)) < CACHE_DURATION;
  }

  function setCacheValid(){
    sessionStorage.setItem(CACHE_KEY, String(Date.now()));
  }

  function validateAgainstServer(valor){
    return new Promise(function(resolve){
      try{
        var fp=getDeviceFingerprint();
        var isEmail=valor.includes('@');
        var action=isEmail?'validateEmail':'validateKey';
        var param=isEmail?'email':'key';
        var url=APPS_SCRIPT_URL+'?action='+action+'&'+param+'='+encodeURIComponent(valor)+'&device='+encodeURIComponent(fp);
        fetch(url)
          .then(function(r){return r.json()})
          .then(function(data){
            if(data.valid){
              setCacheValid();
              // Guardar tipo de plan y acceso a escuela
              if(data.planType) localStorage.setItem(KEY_PLAN, data.planType);
              // Si el servidor no envía campo 'escuela' explícitamente, PRO incluye escuela por defecto
              var tieneEscuela = (typeof data.escuela !== 'undefined') ? data.escuela : true;
              localStorage.setItem(KEY_ESCUELA, tieneEscuela ? 'true' : 'false');
              resolve(true);
            } else {
              if(data.reason) console.warn('PRO rechazado:', data.reason);
              resolve(false);
            }
          })
          .catch(function(e){
            console.error('Error validando PRO:', e);
            // En caso de error de red, si hay caché previo, dar beneficio de la duda
            var ts=sessionStorage.getItem(CACHE_KEY);
            resolve(!!ts);
          });
      }catch(e){
        console.error('Error validando PRO:', e);
        resolve(false);
      }
    });
  }

  // Verifica PRO con caché de 1h
  function check(){
    migrateOldKeys();
    var saved=getSaved();
    if(!saved) return Promise.resolve(false);
    // Expiración local como capa extra de protección
    if(isLocallyExpired()){
      clearPro();
      return Promise.resolve(false);
    }
    if(isCacheValid()) return Promise.resolve(true);
    return validateAgainstServer(saved).then(function(valid){
      if(!valid) clearPro();
      return valid;
    });
  }

  // Fuerza re-validación ignorando caché
  function revalidate(){
    migrateOldKeys();
    sessionStorage.removeItem(CACHE_KEY);
    var saved=getSaved();
    if(!saved) return Promise.resolve(false);
    return validateAgainstServer(saved).then(function(valid){
      if(!valid) clearPro();
      return valid;
    });
  }

  // Activar PRO con email o clave
  function activate(valor){
    if(!valor) return Promise.resolve(false);
    valor=valor.trim().toLowerCase();
    // Limpiar estado previo para evitar conflictos con isLocallyExpired
    clearPro();
    return validateAgainstServer(valor).then(function(valid){
      if(valid){
        if(valor.includes('@')){
          localStorage.setItem(KEY_EMAIL, valor);
        } else {
          localStorage.setItem(KEY_PRO, valor);
        }
        localStorage.setItem(KEY_ACTIVATED, String(Date.now()));
      }
      return valid;
    });
  }

  // Obtener tipo de plan actual
  function getPlan(){
    return localStorage.getItem(KEY_PLAN) || 'pro';
  }

  // Verificar si tiene acceso a Escuela
  function hasEscuela(){
    return localStorage.getItem(KEY_ESCUELA) === 'true';
  }

  // Exportar API global
  window.exoPro={
    check: check,
    revalidate: revalidate,
    activate: activate,
    getSaved: getSaved,
    clearPro: clearPro,
    getDeviceFingerprint: getDeviceFingerprint,
    getPlan: getPlan,
    hasEscuela: hasEscuela,
    // Constantes para uso externo
    KEY_EMAIL: KEY_EMAIL,
    KEY_PRO: KEY_PRO,
    KEY_PLAN: KEY_PLAN,
    KEY_ESCUELA: KEY_ESCUELA,
    APPS_SCRIPT_URL: APPS_SCRIPT_URL
  };

  // Auto-migrar claves al cargar
  migrateOldKeys();
})();
