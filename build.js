/**
 * ExógenaDIAN — Build Script
 *
 * Copia archivos fuente a /docs (GitHub Pages), obfusca JavaScript inline,
 * minifica HTML y sincroniza assets compartidos.
 *
 * Uso:  node build.js
 */
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const DOCS = path.join(ROOT, 'docs');

// ─── Archivos HTML a procesar ───
const HTML_FILES = [
  'index.html',
  'exogena.html',
  'renta110.html',
  'consultanit.html',
  'conciliacion.html',
  'iva300.html',
  'retencion350.html',
  'estadosfinancieros.html',
  'dashboard.html',
  'intereses.html',
  'sanciones.html',
  'vencimientos.html',
  'blog.html',
  'gracias.html',
  'terminos.html',
  'liquidador.html',
  'sanciones-dian.html',
  'uvt.html',
  'costoreal.html',
  'politica-privacidad.html',
  'retencion-fuente.html',
  'credito.html',
  'formato220.html',
  'precios.html',
  'ia.html',
  'ia-analisis-balance.html',
  'ia-chat-et.html',
  'ia-inconsistencias.html',
  'ia-asistente.html',
  'ia-respuesta-requerimiento.html',
  'ia-resumen-declaracion.html',
];

// ─── Directorios/archivos estáticos a copiar tal cual ───
const STATIC_COPY = [
  'shared',
  'data',
  'og-image.png',
  'robots.txt',
  'sitemap.xml',
  'template_110.xlsx',
  'template_300.xlsx',
  'template_350.xlsx',
];

// ─── Configuración de ofuscación ───
let JavaScriptObfuscator;
try {
  JavaScriptObfuscator = require('javascript-obfuscator');
} catch {
  console.log('WARNING: javascript-obfuscator not installed. Skipping obfuscation.');
  console.log('  Run: npm install javascript-obfuscator');
}

const OBF_OPTIONS = {
  compact: true,
  controlFlowFlattening: false,
  deadCodeInjection: false,
  identifierNamesGenerator: 'hexadecimal',
  renameGlobals: false,
  selfDefending: false,
  stringArray: true,
  stringArrayThreshold: 0.5,
  stringArrayEncoding: ['base64'],
  splitStrings: true,
  splitStringsChunkLength: 10,
  transformObjectKeys: false,
  unicodeEscapeSequence: false,
};

// ─── Helpers ───
function copyRecursive(src, dest) {
  if (!fs.existsSync(src)) return;
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    fs.mkdirSync(dest, { recursive: true });
    for (const child of fs.readdirSync(src)) {
      copyRecursive(path.join(src, child), path.join(dest, child));
    }
  } else {
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(src, dest);
  }
}

function obfuscateHTML(html, filename) {
  if (!JavaScriptObfuscator) return { html, count: 0 };
  let count = 0;
  html = html.replace(/<script(?![^>]*\bsrc\b)([^>]*)>([\s\S]*?)<\/script>/gi, (match, attrs, jsCode) => {
    if (jsCode.trim().length < 50) return match;
    if (attrs.includes('data-render')) return match;
    if (attrs.includes('application/ld+json')) return match;
    try {
      const result = JavaScriptObfuscator.obfuscate(jsCode, OBF_OPTIONS);
      count++;
      // Sanitize: replace any </script> inside obfuscated strings to prevent breaking HTML
      let obfCode = result.getObfuscatedCode();
      obfCode = obfCode.replace(/<\/script>/gi, '<\\/script>');
      return `<script${attrs}>${obfCode}</script>`;
    } catch (e) {
      console.log(`  WARNING [${filename}]: ${e.message.substring(0, 80)}`);
      return match;
    }
  });
  return { html, count };
}

function minifyHTML(html) {
  return html
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\n\s*\n/g, '\n');
}

// ═══════════════════════════════════════════════
//  BUILD
// ═══════════════════════════════════════════════
console.log('ExógenaDIAN Build\n');

// 1. Copiar assets estáticos
console.log('1. Copying static assets...');
for (const item of STATIC_COPY) {
  const src = path.join(ROOT, item);
  const dest = path.join(DOCS, item);
  if (fs.existsSync(src)) {
    copyRecursive(src, dest);
    console.log(`   ${item}`);
  }
}

// 2. Copiar blog posts (si existen)
const blogSrc = path.join(ROOT, 'blog');
const blogDest = path.join(DOCS, 'blog');
if (fs.existsSync(blogSrc)) {
  copyRecursive(blogSrc, blogDest);
  console.log('   blog/');
}

// 3. Procesar HTML: copiar, obfuscar, minificar
console.log('\n2. Processing HTML files...');
let totalFiles = 0;
let totalScripts = 0;

for (const file of HTML_FILES) {
  const src = path.join(ROOT, file);
  const dest = path.join(DOCS, file);

  if (!fs.existsSync(src)) {
    console.log(`   SKIP: ${file} (not found)`);
    continue;
  }

  let html = fs.readFileSync(src, 'utf-8');
  const { html: obfuscated, count } = obfuscateHTML(html, file);
  html = minifyHTML(obfuscated);

  fs.writeFileSync(dest, html, 'utf-8');
  console.log(`   ${file} (${count} scripts obfuscated)`);
  totalFiles++;
  totalScripts += count;
}

// 4. Preservar CNAME si existe
const cname = path.join(DOCS, 'CNAME');
if (!fs.existsSync(cname)) {
  fs.writeFileSync(cname, 'exogenadian.com\n', 'utf-8');
  console.log('\n   Created CNAME');
}

console.log(`\nDone: ${totalFiles} HTML files, ${totalScripts} script blocks obfuscated.`);
console.log('Deploy: git add docs/ && git commit && git push');
