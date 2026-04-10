/* ═══ ExógenaDIAN — Blog In-Content CTA + Floating Side CTA ═══
   Uso: <script src="../shared/blog-cta.js"></script> al final del <body>
   Inyecta:
   1. Tarjeta CTA después del 3er párrafo del artículo
   2. CTA flotante lateral en desktop después de 30% scroll
*/
(function(){
  'use strict';

  /* ─── Inject CSS ─── */
  var css=document.createElement('style');
  css.textContent=`
    /* ===== IN-CONTENT CTA CARD ===== */
    .exo-blog-cta{
      background:#0A0F1E;border:2px solid #22C55E;border-radius:14px;
      padding:1.5rem 1.75rem;margin:2rem 0;
      display:flex;align-items:center;gap:16px;flex-wrap:wrap;
      font-family:'Outfit',sans-serif;
      box-shadow:0 4px 20px rgba(34,197,94,.12);
      transition:border-color .3s,box-shadow .3s
    }
    .exo-blog-cta:hover{border-color:#16A34A;box-shadow:0 6px 28px rgba(34,197,94,.2)}
    .exo-blog-cta-icon{font-size:2rem;flex-shrink:0}
    .exo-blog-cta-body{flex:1;min-width:200px}
    .exo-blog-cta-title{color:#fff;font-weight:700;font-size:1.05rem;margin-bottom:4px}
    .exo-blog-cta-sub{color:#94A3B8;font-size:.9rem}
    .exo-blog-cta-btn{
      display:inline-flex;align-items:center;gap:6px;
      background:#22C55E;color:#0A0F1E;
      padding:10px 22px;border-radius:10px;
      font-weight:700;font-size:.92rem;text-decoration:none;
      transition:all .2s;white-space:nowrap;flex-shrink:0
    }
    .exo-blog-cta-btn:hover{background:#16A34A;color:#fff;transform:translateY(-1px)}

    /* ===== FLOATING SIDE CTA ===== */
    .exo-float-cta{
      position:fixed;right:20px;top:50%;transform:translateY(-50%);
      z-index:90;
      background:#0A0F1E;border:2px solid #22C55E;border-radius:14px;
      padding:16px 18px;width:180px;
      text-align:center;font-family:'Outfit',sans-serif;
      box-shadow:0 8px 32px rgba(0,0,0,.3);
      opacity:0;pointer-events:none;
      transition:opacity .4s,transform .4s
    }
    .exo-float-cta.visible{opacity:1;pointer-events:auto}
    .exo-float-cta-title{color:#fff;font-weight:700;font-size:.9rem;margin-bottom:8px}
    .exo-float-cta-link{
      display:inline-flex;align-items:center;gap:4px;
      color:#22C55E;font-weight:700;font-size:.85rem;text-decoration:none;
      transition:color .2s
    }
    .exo-float-cta-link:hover{color:#4ADE80}
    .exo-float-cta-close{
      position:absolute;top:6px;right:8px;
      background:none;border:none;color:#64748B;font-size:.9rem;
      cursor:pointer;padding:2px 4px;transition:color .2s
    }
    .exo-float-cta-close:hover{color:#fff}
    @media(max-width:1200px){.exo-float-cta{display:none}}
    @media(max-width:600px){.exo-blog-cta{padding:1.25rem;gap:12px}.exo-blog-cta-title{font-size:.95rem}.exo-blog-cta-btn{padding:8px 16px;font-size:.85rem}}
  `;
  document.head.appendChild(css);

  /* ─── 1. In-content CTA after 3rd paragraph ─── */
  var article=document.querySelector('.article-wrap')||document.querySelector('article');
  if(article){
    var paragraphs=article.querySelectorAll(':scope > p');
    if(paragraphs.length>=3){
      var cta=document.createElement('div');
      cta.className='exo-blog-cta';
      cta.innerHTML=
        '<div class="exo-blog-cta-icon">\uD83D\uDCCA</div>'+
        '<div class="exo-blog-cta-body">'+
        '  <div class="exo-blog-cta-title">\u00BFNecesitas calcular tu Informaci\u00F3n Ex\u00F3gena?</div>'+
        '  <div class="exo-blog-cta-sub">Usa nuestras herramientas gratuitas</div>'+
        '</div>'+
        '<a href="https://exogenadian.com/exogena.html" class="exo-blog-cta-btn" onclick="if(typeof exoTrack!==\'undefined\'&&exoTrack.ctaClick)exoTrack.ctaClick(\'blog_inline_cta\',\'exogena\')">Probar gratis \u2192</a>';
      // Insert after 3rd paragraph
      var target=paragraphs[2];
      target.parentNode.insertBefore(cta,target.nextSibling);
    }
  }

  /* ─── 2. Floating side CTA (desktop only, after 30% scroll) ─── */
  var floatEl=document.createElement('div');
  floatEl.className='exo-float-cta';
  floatEl.innerHTML=
    '<button class="exo-float-cta-close" aria-label="Cerrar" onclick="this.parentElement.remove()">&times;</button>'+
    '<div class="exo-float-cta-title">Herramientas DIAN gratis</div>'+
    '<a href="https://exogenadian.com/index.html" class="exo-float-cta-link" onclick="if(typeof exoTrack!==\'undefined\'&&exoTrack.ctaClick)exoTrack.ctaClick(\'blog_float_cta\',\'herramientas\')">Ver herramientas \u2192</a>';
  document.body.appendChild(floatEl);

  var floatShown=false;
  window.addEventListener('scroll',function(){
    if(floatShown) return;
    var scrollPct=(window.scrollY+window.innerHeight)/document.body.scrollHeight;
    if(scrollPct>0.30){
      floatShown=true;
      floatEl.classList.add('visible');
    }
  });

})();
