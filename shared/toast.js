/* ═══ ExógenaDIAN — Toast Notification System ═══ */
(function(){
  'use strict';
  var COLORS={
    success:{bg:'#D1FAE5',border:'#059669',text:'#065F46',icon:'✓'},
    error:  {bg:'#FEE2E2',border:'#DC2626',text:'#991B1B',icon:'✕'},
    warning:{bg:'#FEF3C7',border:'#D97706',text:'#92400E',icon:'⚠'},
    info:   {bg:'#DBEAFE',border:'#2563EB',text:'#1E40AF',icon:'ℹ'}
  };
  var container;
  function getContainer(){
    if(container)return container;
    container=document.createElement('div');
    container.setAttribute('aria-live','polite');
    container.setAttribute('role','status');
    container.style.cssText='position:fixed;top:16px;right:16px;z-index:99999;display:flex;flex-direction:column;gap:8px;max-width:400px;width:calc(100% - 32px);pointer-events:none';
    document.body.appendChild(container);
    return container;
  }
  window.exoToast=function(msg,type){
    type=type||'info';
    var c=COLORS[type]||COLORS.info;
    var dur=(type==='error'||type==='warning')?8000:5000;
    var el=document.createElement('div');
    el.style.cssText='pointer-events:auto;display:flex;align-items:flex-start;gap:10px;padding:12px 16px;background:'+c.bg+';border-left:4px solid '+c.border+';border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,.1);font-family:Outfit,DM Sans,sans-serif;font-size:.88rem;color:'+c.text+';opacity:0;transform:translateX(20px);transition:all .3s ease;line-height:1.4;word-break:break-word';
    var icon=document.createElement('span');
    icon.style.cssText='font-weight:700;font-size:1rem;flex-shrink:0;line-height:1.2';
    icon.textContent=c.icon;
    var text=document.createElement('span');
    text.style.cssText='flex:1';
    text.textContent=msg;
    var close=document.createElement('button');
    close.style.cssText='background:none;border:none;color:'+c.text+';cursor:pointer;font-size:1.1rem;padding:0;line-height:1;flex-shrink:0;opacity:.6';
    close.textContent='×';
    close.setAttribute('aria-label','Cerrar');
    close.onclick=function(){dismiss()};
    el.appendChild(icon);el.appendChild(text);el.appendChild(close);
    getContainer().appendChild(el);
    requestAnimationFrame(function(){requestAnimationFrame(function(){el.style.opacity='1';el.style.transform='translateX(0)'})});
    var timer=setTimeout(dismiss,dur);
    function dismiss(){
      clearTimeout(timer);
      el.style.opacity='0';el.style.transform='translateX(20px)';
      setTimeout(function(){if(el.parentNode)el.parentNode.removeChild(el)},300);
    }
  };
})();
