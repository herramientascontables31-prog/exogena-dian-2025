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
      uid='D-'+crypto.randomUUID().split('-').slice(0,2).join('');
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
    sessionStorage.removeItem(CACHE_KEY);
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
    return validateAgainstServer(valor).then(function(valid){
      if(valid){
        if(valor.includes('@')){
          localStorage.setItem(KEY_EMAIL, valor);
        } else {
          localStorage.setItem(KEY_PRO, valor);
        }
      }
      return valid;
    });
  }

  // Exportar API global
  window.exoPro={
    check: check,
    revalidate: revalidate,
    activate: activate,
    getSaved: getSaved,
    clearPro: clearPro,
    getDeviceFingerprint: getDeviceFingerprint,
    // Constantes para uso externo
    KEY_EMAIL: KEY_EMAIL,
    KEY_PRO: KEY_PRO,
    APPS_SCRIPT_URL: APPS_SCRIPT_URL
  };

  // Auto-migrar claves al cargar
  migrateOldKeys();
})();
