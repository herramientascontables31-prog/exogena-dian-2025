/* ═══ ExógenaDIAN — Certificate Generation System ═══
   Uso:
     <script src="shared/certificado.js"></script>
     — o desde escuela/:
     <script src="../shared/certificado.js"></script>

     generateCertificate('ia-automatizacion', 'Juan Hoyos', { modulosCompletados: 10 });
*/
(function(){
  'use strict';

  var COURSES = {
    'ia-automatizacion': {
      name: 'IA y Automatizaci\u00f3n para Contadores',
      desc: 'uso de inteligencia artificial aplicada a la pr\u00e1ctica contable colombiana: revisi\u00f3n de balances, generaci\u00f3n de ex\u00f3gena, declaraciones de renta, IVA, retenci\u00f3n, consulta normativa y dashboards',
      short: 'IA'
    },
    'iva300': {
      name: 'Formulario 300 \u2014 IVA',
      desc: 'declaraci\u00f3n del IVA bimestral, IVA generado vs descontable, proporcionalidad, importaciones y pr\u00e1ctica con balance real',
      short: 'IVA'
    },
    'renta110': {
      name: 'Declaraci\u00f3n de Renta F110',
      desc: 'depuraci\u00f3n de renta para personas jur\u00eddicas, patrimonio, ingresos, costos, gastos no deducibles, tasa m\u00ednima de tributaci\u00f3n',
      short: 'F110'
    },
    'retencion350': {
      name: 'Retenci\u00f3n en la Fuente 350',
      desc: 'retenci\u00f3n por renta, IVA, autorretenci\u00f3n, bases m\u00ednimas, tarifas en UVT y pr\u00e1ctica con auxiliar contable',
      short: 'RF'
    },
    'exogena': {
      name: 'Medios Magn\u00e9ticos \u2014 Ex\u00f3gena DIAN',
      desc: '10 formatos de informaci\u00f3n ex\u00f3gena, clasificaci\u00f3n de conceptos, Art. 631 ET y prevalidaci\u00f3n MUISCA',
      short: 'EXG'
    },
    'sanciones': {
      name: 'Sanciones DIAN',
      desc: 'gradualidad, extemporaneidad, correcci\u00f3n voluntaria, sanciones por ex\u00f3gena',
      short: 'SAN'
    },
    'nomina': {
      name: 'N\u00f3mina y Seguridad Social',
      desc: 'liquidaci\u00f3n de n\u00f3mina, prestaciones sociales, seguridad social, parafiscales',
      short: 'NOM'
    },
    'procedimiento': {
      name: 'Procedimiento Tributario',
      desc: 'fiscalizaci\u00f3n DIAN, requerimientos, liquidaci\u00f3n oficial, recursos',
      short: 'PT'
    },
    'ica': {
      name: 'ICA \u2014 Industria y Comercio',
      desc: 'hecho generador, territorialidad, tarifas CIIU, ReteICA, descuento en renta',
      short: 'ICA'
    },
    'niif': {
      name: 'NIIF para Contadores',
      desc: 'marco conceptual, reconocimiento, medici\u00f3n, presentaci\u00f3n de estados financieros bajo NIIF',
      short: 'NIIF'
    },
    'regimen-simple': {
      name: 'R\u00e9gimen Simple de Tributaci\u00f3n',
      desc: 'inscripci\u00f3n, 4 grupos de actividad, tarifas Art. 908 ET, anticipo bimestral F2593, declaraci\u00f3n anual F260',
      short: 'RST'
    }
  };

  var STORAGE_KEY = 'exo_certificates';

  function getStoredCertificates() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    } catch(e) { return []; }
  }

  function saveCertificate(cert) {
    var certs = getStoredCertificates();
    certs.push(cert);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(certs));
    } catch(e) {}
  }

  function findCertificate(code) {
    var certs = getStoredCertificates();
    for (var i = 0; i < certs.length; i++) {
      if (certs[i].codigo === code) return certs[i];
    }
    return null;
  }

  function generateCode(cursoId) {
    var course = COURSES[cursoId];
    var short = course ? course.short : 'GEN';
    var year = new Date().getFullYear();
    var hex = Math.random().toString(16).substring(2, 6).toUpperCase();
    return 'EXO-' + short + '-' + year + '-' + hex;
  }

  function generateCertificate(cursoId, studentName, options) {
    options = options || {};
    var course = COURSES[cursoId];
    if (!course) {
      console.error('Curso no encontrado: ' + cursoId);
      return null;
    }

    var code = generateCode(cursoId);
    var now = new Date();
    var fecha = now.getFullYear() + '-' +
      String(now.getMonth() + 1).padStart(2, '0') + '-' +
      String(now.getDate()).padStart(2, '0');

    var cert = {
      codigo: code,
      nombre: studentName.trim(),
      cursoId: cursoId,
      cursoNombre: course.name,
      cursoDesc: course.desc,
      fecha: fecha,
      modulosCompletados: options.modulosCompletados || 'todos',
      timestamp: now.getTime()
    };

    saveCertificate(cert);

    // Redirect to certificate page
    var basePath = '';
    if (window.location.pathname.indexOf('/escuela/') !== -1) {
      basePath = '../';
    }
    var hash = '#nombre=' + encodeURIComponent(cert.nombre) +
      '&curso=' + encodeURIComponent(cursoId) +
      '&codigo=' + encodeURIComponent(code) +
      '&fecha=' + encodeURIComponent(fecha);

    window.location.href = basePath + 'certificado.html' + hash;
    return cert;
  }

  // Expose globally
  window.exoCertificado = {
    COURSES: COURSES,
    generate: generateCertificate,
    find: findCertificate,
    getAll: getStoredCertificates,
    generateCode: generateCode
  };
})();
