/* ═══ ExógenaDIAN — Exportaciones Liquidador Laboral (PDF + Excel) ═══ */

var _causasTxt = {sin_justa_causa:'Despido sin justa causa',justa_causa:'Despido con justa causa',renuncia:'Renuncia voluntaria',mutuo_acuerdo:'Mutuo acuerdo',vencimiento:'Vencimiento contrato fijo',fin_obra:'Terminación de obra'};
var _tiposTxt = {indefinido:'Término indefinido',fijo:'Término fijo',obra:'Obra o labor'};

/* ─── PDF con jsPDF + autoTable ─── */
function exportarPDF(r) {
  try {
    var jsPDFClass = (window.jspdf && window.jspdf.jsPDF) || window.jsPDF;
    if (!jsPDFClass) { alert('Error: librería jsPDF no cargó correctamente. Recarga la página e intenta de nuevo.'); return; }
    var doc = new jsPDFClass('p','mm','letter');
  } catch(e) {
    alert('Error al generar PDF: ' + e.message); return;
  }
  var W = 216, M = 18, cw = W - 2*M;
  var y = 18;

  // Header azul
  doc.setFillColor(27,58,92);
  doc.rect(0,0,W,44,'F');
  doc.setTextColor(255,255,255);
  doc.setFontSize(15);
  doc.setFont('helvetica','bold');
  doc.text('LIQUIDACIÓN DE CONTRATO DE TRABAJO', M, y);
  y += 8;
  doc.setFontSize(9);
  doc.setFont('helvetica','normal');
  var hoy = new Date();
  doc.text('Fecha de elaboración: ' + hoy.toLocaleDateString('es-CO'), M, y);
  y += 5;
  doc.text('exogenadian.com  |  Ley 2466/2025 — Normativa laboral vigente ' + r.anioLiq, M, y);
  // Badge
  doc.setFillColor(5,150,105);
  doc.roundedRect(W-M-42, 14, 42, 8, 2, 2, 'F');
  doc.setFontSize(7);
  doc.setFont('helvetica','bold');
  doc.text('Ley 2466/2025', W-M-40, 19.5);
  y += 18;
  doc.setTextColor(0,0,0);

  // ── Sección 1: Datos del contrato ──
  doc.setFillColor(240,242,245);
  doc.rect(M, y-4, cw, 8, 'F');
  doc.setFontSize(10);
  doc.setFont('helvetica','bold');
  doc.setTextColor(27,58,92);
  doc.text('1. DATOS DEL CONTRATO', M+3, y+1);
  doc.setTextColor(0,0,0);
  y += 8;

  var datos1 = [
    ['Empleador', (r.empleador||'—') + (r.nitEmpleador ? '  —  NIT: '+r.nitEmpleador : '')],
    ['Trabajador', r.empleado||'—'],
    ['Cargo', r.cargo||'—'],
    ['Tipo de contrato', _tiposTxt[r.tipoContrato]||r.tipoContrato],
    ['Causa de terminación', _causasTxt[r.causa]||r.causa],
    ['Fecha inicio', r.fechaInicio.toLocaleDateString('es-CO')],
    ['Fecha terminación', r.fechaFin.toLocaleDateString('es-CO')],
    ['Tiempo laborado', r.periodoTexto + '  (' + r.diasTotal + ' días base 360)']
  ];

  doc.autoTable({
    startY: y, margin:{left:M,right:M}, theme:'plain',
    body: datos1,
    columnStyles: {0:{fontStyle:'bold',cellWidth:48,textColor:[107,114,128]},1:{cellWidth:cw-48}},
    styles: {fontSize:8.5,cellPadding:{top:2,bottom:2,left:3,right:3},lineColor:[226,232,240],lineWidth:0.3},
    alternateRowStyles:{fillColor:[249,250,251]}
  });
  y = doc.lastAutoTable.finalY + 6;

  // ── Sección 2: Base salarial ──
  doc.setFillColor(240,242,245);
  doc.rect(M, y-4, cw, 8, 'F');
  doc.setFontSize(10);
  doc.setFont('helvetica','bold');
  doc.setTextColor(27,58,92);
  doc.text('2. BASE SALARIAL', M+3, y+1);
  doc.setTextColor(0,0,0);
  y += 8;

  var datos2 = [
    ['Salario básico mensual', fCOP(r.salario) + (r.esIntegral?' (integral — 70% = '+fCOP(Math.round(r.salario*0.7))+')':'')],
    ['Auxilio de transporte', r.auxTransporte>0 ? fCOP(r.auxTransporte)+'/mes' : 'No aplica (salario > 2 SMLMV)'],
    ['SBL Cesantías y Prima', fCOP(r.sblCesPrima)],
    ['SBL Vacaciones', fCOP(r.sblVac) + ' (solo salario básico, Art. 189 CST)']
  ];

  doc.autoTable({
    startY: y, margin:{left:M,right:M}, theme:'plain', body:datos2,
    columnStyles:{0:{fontStyle:'bold',cellWidth:48,textColor:[107,114,128]},1:{cellWidth:cw-48}},
    styles:{fontSize:8.5,cellPadding:{top:2,bottom:2,left:3,right:3},lineColor:[226,232,240],lineWidth:0.3},
    alternateRowStyles:{fillColor:[249,250,251]}
  });
  y = doc.lastAutoTable.finalY + 6;

  // ── Sección 3: Liquidación detallada ──
  doc.setFillColor(240,242,245);
  doc.rect(M, y-4, cw, 8, 'F');
  doc.setFontSize(10);
  doc.setFont('helvetica','bold');
  doc.setTextColor(27,58,92);
  doc.text('3. LIQUIDACIÓN DETALLADA', M+3, y+1);
  doc.setTextColor(0,0,0);
  y += 6;

  var filas = [
    ['Salario proporcional ('+r.diaDelMes+' días)', fCOP(Math.round(r.salDiario))+'/día', r.diaDelMes+'', fCOP(r.salProporcional)],
  ];
  if (r.auxProporcional>0) {
    filas.push(['Aux. transporte proporcional', fCOP(r.auxTransporte)+'/mes', r.diaDelMes+' días', fCOP(r.auxProporcional)]);
  }
  filas.push(
    ['Cesantías (Art. 249 CST)', fCOP(r.sblCesPrima), r.diasAnio+' días', fCOP(r.cesantias)],
    ['Intereses cesantías (Ley 52/75)', fCOP(r.cesantias), r.diasAnio+' d × 12%', fCOP(r.intereses)],
    ['Prima de servicios (Art. 306 CST)', fCOP(r.sblCesPrima), r.diasSemestre+' días sem.', fCOP(r.prima)],
    ['Vacaciones (Art. 186 CST)', fCOP(r.sblVac), r.vacaciones.diasPendientes.toFixed(1)+' días pend.', fCOP(r.vacaciones.valor)]
  );

  if (r.indemnizacion.aplica) {
    filas.push(['INDEMNIZACIÓN (Art. 64 CST)', fCOP(r.salario), r.indemnizacion.dias.toFixed(1)+' días', fCOP(r.indemnizacion.valor)]);
  }

  filas.push(['', '', 'SUBTOTAL DEVENGADO', fCOP(r.subtotal)]);
  if (r.anticipos>0) filas.push(['(-) Anticipos cesantías','','', '-'+fCOP(r.anticipos)]);
  if (r.prestamos>0) filas.push(['(-) Préstamos/libranzas','','', '-'+fCOP(r.prestamos)]);
  filas.push(['','','TOTAL A PAGAR', fCOP(r.total)]);

  doc.autoTable({
    startY: y, margin:{left:M,right:M}, theme:'grid',
    head: [['Concepto','Base','Días / Factor','Valor COP']],
    body: filas,
    headStyles:{fillColor:[27,58,92],fontSize:7.5,fontStyle:'bold',halign:'center',cellPadding:3},
    styles:{fontSize:8,cellPadding:3,lineColor:[226,232,240],lineWidth:0.3},
    columnStyles:{0:{cellWidth:58},1:{cellWidth:38,halign:'right'},2:{cellWidth:32,halign:'center'},3:{halign:'right',fontStyle:'bold'}},
    alternateRowStyles:{fillColor:[249,250,251]},
    didParseCell: function(data) {
      if (data.section==='body') {
        var txt = String(data.cell.raw||'');
        if (txt.indexOf('TOTAL A PAGAR')>=0) {
          data.cell.styles.fontStyle='bold';
          data.cell.styles.fillColor=[27,58,92];
          data.cell.styles.textColor=[255,255,255];
          data.cell.styles.fontSize=9;
        } else if (txt.indexOf('SUBTOTAL')>=0) {
          data.cell.styles.fontStyle='bold';
          data.cell.styles.fillColor=[209,250,229];
          data.cell.styles.textColor=[6,95,70];
        } else if (txt.indexOf('INDEMNIZACIÓN')>=0) {
          data.cell.styles.fillColor=[255,247,237];
          data.cell.styles.fontStyle='bold';
          data.cell.styles.textColor=[194,65,12];
        } else if (txt.indexOf('(-)')>=0) {
          data.cell.styles.textColor=[220,38,38];
        }
      }
    }
  });
  y = doc.lastAutoTable.finalY + 10;

  // ── Firmas ──
  if (y > 215) { doc.addPage(); y = 25; }
  doc.setDrawColor(200,200,200);
  doc.setFontSize(9);
  doc.setFont('helvetica','bold');
  doc.setTextColor(27,58,92);
  doc.text('4. FIRMAS', M, y); y += 10;
  doc.setFont('helvetica','normal');
  doc.setTextColor(0,0,0);
  doc.setFontSize(8);
  // Líneas de firma
  doc.setDrawColor(180,180,180);
  doc.line(M, y+12, M+72, y+12);
  doc.line(W-M-72, y+12, W-M, y+12);
  doc.text('EL EMPLEADOR', M, y+17);
  doc.text('EL TRABAJADOR', W-M-72, y+17);
  doc.setFontSize(7.5);
  doc.setTextColor(107,114,128);
  doc.text('Nombre: '+(r.empleador||''), M, y+22);
  doc.text('Nombre: '+(r.empleado||''), W-M-72, y+22);
  doc.text('C.C./NIT: '+(r.nitEmpleador||'______________'), M, y+27);
  doc.text('C.C.: ______________', W-M-72, y+27);
  y += 36;

  // ── Pie de página ──
  doc.setFillColor(249,250,251);
  doc.rect(0, 252, W, 28, 'F');
  doc.setDrawColor(226,232,240);
  doc.line(0, 252, W, 252);
  doc.setFontSize(6.5);
  doc.setTextColor(150,150,150);
  doc.text('Documento generado por exogenadian.com  |  Arts. 249, 306, 186-189, 64 CST  |  Ley 2466/2025  |  Valores vigentes '+r.anioLiq, M, 258);
  doc.text('Este documento es informativo y orientativo. Los valores exactos pueden variar según condiciones específicas del contrato.', M, 262);
  doc.text('Consulte con un abogado laboral para casos con complejidades adicionales.', M, 266);

  try {
    doc.save('Liquidacion_Laboral_' + (r.empleado||'trabajador').replace(/\s+/g,'_') + '.pdf');
  } catch(e) {
    alert('Error al guardar PDF: ' + e.message);
  }
}

/* ─── Excel con ExcelJS (con estilos) ─── */
function exportarExcel(r) {
  try {
    var wb = new ExcelJS.Workbook();
    wb.creator = 'exogenadian.com';
    wb.created = new Date();

    // ══ Hoja 1: Liquidación ══
    var ws = wb.addWorksheet('Liquidación', {properties:{defaultColWidth:18}});
    ws.columns = [
      {width:38},{width:20},{width:14},{width:30},{width:20}
    ];

    var hdrFill = {type:'pattern',pattern:'solid',fgColor:{argb:'FF1B3A5C'}};
    var hdrFont = {bold:true,color:{argb:'FFFFFFFF'},size:11};
    var greenFill = {type:'pattern',pattern:'solid',fgColor:{argb:'FFD1FAE5'}};
    var greenFont = {bold:true,color:{argb:'FF065F46'},size:11};
    var amberFill = {type:'pattern',pattern:'solid',fgColor:{argb:'FFFFF7ED'}};
    var grayFill = {type:'pattern',pattern:'solid',fgColor:{argb:'FFF9FAFB'}};
    var borderThin = {top:{style:'thin',color:{argb:'FFE2E8F0'}},bottom:{style:'thin',color:{argb:'FFE2E8F0'}},left:{style:'thin',color:{argb:'FFE2E8F0'}},right:{style:'thin',color:{argb:'FFE2E8F0'}}};
    var copFmt = '#,##0';

    // Título
    ws.mergeCells('A1:E1');
    var t1 = ws.getCell('A1');
    t1.value = 'LIQUIDACIÓN DE CONTRATO DE TRABAJO';
    t1.fill = hdrFill; t1.font = {bold:true,color:{argb:'FFFFFFFF'},size:14}; t1.alignment={horizontal:'center',vertical:'middle'};
    ws.getRow(1).height = 32;

    ws.mergeCells('A2:C2');
    ws.getCell('A2').value = 'Generado por exogenadian.com  |  Ley 2466/2025';
    ws.getCell('A2').font = {italic:true,color:{argb:'FF6B7280'},size:9};
    ws.getCell('D2').value = 'Fecha:';
    ws.getCell('D2').font = {bold:true,color:{argb:'FF6B7280'},size:9};
    ws.getCell('E2').value = new Date().toLocaleDateString('es-CO');
    ws.getCell('E2').font = {size:9};

    // Espacio
    ws.addRow([]);

    // Datos del contrato - header
    ws.mergeCells('A4:E4');
    var h4 = ws.getCell('A4');
    h4.value = 'DATOS DEL CONTRATO';
    h4.fill = {type:'pattern',pattern:'solid',fgColor:{argb:'FFF0F2F5'}};
    h4.font = {bold:true,color:{argb:'FF1B3A5C'},size:10};
    ws.getRow(4).height = 22;

    var infoRows = [
      ['Empleador:', r.empleador||'','','NIT:', r.nitEmpleador||''],
      ['Trabajador:', r.empleado||'','','Cargo:', r.cargo||''],
      ['Tipo contrato:', _tiposTxt[r.tipoContrato]||'','','Causa:', _causasTxt[r.causa]||''],
      ['Fecha inicio:', r.fechaInicio.toLocaleDateString('es-CO'),'','Fecha fin:', r.fechaFin.toLocaleDateString('es-CO')],
      ['Tiempo laborado:', r.periodoTexto,'','Días (base 360):', r.diasTotal]
    ];
    infoRows.forEach(function(row) {
      var rw = ws.addRow(row);
      rw.getCell(1).font = {bold:true,color:{argb:'FF6B7280'},size:9};
      rw.getCell(2).font = {size:9};
      rw.getCell(4).font = {bold:true,color:{argb:'FF6B7280'},size:9};
      rw.getCell(5).font = {size:9};
      rw.eachCell(function(c){c.border=borderThin;});
    });

    ws.addRow([]);

    // Tabla principal - encabezado
    var thRow = ws.addRow(['Concepto','Base (COP)','Días','Fórmula','Valor (COP)']);
    thRow.height = 24;
    thRow.eachCell(function(c){
      c.fill=hdrFill; c.font=hdrFont; c.alignment={horizontal:'center',vertical:'middle'};
      c.border={top:{style:'thin'},bottom:{style:'thin'},left:{style:'thin'},right:{style:'thin'}};
    });

    // Filas de datos
    function addConceptRow(concepto, base, dias, formula, valor, style) {
      var rw = ws.addRow([concepto, base, dias, formula, valor]);
      rw.getCell(1).font = {size:9,bold:style==='indem'||style==='total'||style==='subtotal'};
      rw.getCell(2).font = {size:9}; rw.getCell(2).numFmt = copFmt; rw.getCell(2).alignment={horizontal:'right'};
      rw.getCell(3).font = {size:9}; rw.getCell(3).alignment={horizontal:'center'};
      rw.getCell(4).font = {size:8,italic:true,color:{argb:'FF6B7280'}};
      rw.getCell(5).font = {bold:true,size:10}; rw.getCell(5).numFmt = copFmt; rw.getCell(5).alignment={horizontal:'right'};
      rw.eachCell(function(c){c.border=borderThin;});
      if (style==='indem') { rw.eachCell(function(c){c.fill=amberFill;}); rw.getCell(5).font={bold:true,size:10,color:{argb:'FFC2410C'}}; }
      if (style==='subtotal') { rw.eachCell(function(c){c.fill=greenFill;}); rw.getCell(5).font=greenFont; }
      if (style==='total') { rw.eachCell(function(c){c.fill=hdrFill;}); rw.getCell(1).font={bold:true,size:11,color:{argb:'FFFFFFFF'}}; rw.getCell(5).font={bold:true,size:12,color:{argb:'FFFFFFFF'}}; rw.height=28; }
      if (style==='deduccion') { rw.getCell(5).font={bold:true,size:10,color:{argb:'FFDC2626'}}; }
      return rw;
    }

    addConceptRow('Salario proporcional ('+r.diaDelMes+' días)', Math.round(r.salDiario), r.diaDelMes, 'Salario/30 × Días', r.salProporcional);
    if (r.auxProporcional>0) addConceptRow('Aux. transporte proporcional', r.auxTransporte, r.diaDelMes, 'Aux × Días / 30', r.auxProporcional);
    addConceptRow('Cesantías (Art. 249 CST)', r.sblCesPrima, r.diasAnio, 'SBL × Días / 360', r.cesantias);
    addConceptRow('Intereses cesantías (Ley 52/75)', r.cesantias, r.diasAnio, 'Ces × Días × 12% / 360', r.intereses);
    addConceptRow('Prima de servicios (Art. 306 CST)', r.sblCesPrima, r.diasSemestre, 'SBL × Días / 360', r.prima);
    addConceptRow('Vacaciones (Art. 186 CST)', r.sblVac, r.vacaciones.diasPendientes, 'Sal / 30 × Días pend.', r.vacaciones.valor);
    if (r.indemnizacion.aplica) {
      addConceptRow('INDEMNIZACIÓN (Art. 64 CST)', r.salario, r.indemnizacion.dias, r.indemnizacion.formula||'', r.indemnizacion.valor, 'indem');
    }
    ws.addRow([]);
    addConceptRow('','','','SUBTOTAL DEVENGADO', r.subtotal, 'subtotal');
    if (r.anticipos>0) addConceptRow('','','','(-) Anticipos cesantías', -r.anticipos, 'deduccion');
    if (r.prestamos>0) addConceptRow('','','','(-) Préstamos/libranzas', -r.prestamos, 'deduccion');
    addConceptRow('','','','TOTAL A PAGAR', r.total, 'total');

    // ══ Hoja 2: Parámetros ══
    var ws2 = wb.addWorksheet('Parámetros');
    ws2.columns = [{width:12},{width:18},{width:22}];
    ws2.mergeCells('A1:C1');
    var pt = ws2.getCell('A1');
    pt.value = 'PARÁMETROS LABORALES ' + r.anioLiq;
    pt.fill = hdrFill; pt.font = hdrFont; pt.alignment={horizontal:'center'};
    ws2.getRow(1).height = 28;
    ws2.addRow([]);
    var ph = ws2.addRow(['Año','SMLMV','Auxilio Transporte']);
    ph.eachCell(function(c){c.fill={type:'pattern',pattern:'solid',fgColor:{argb:'FFF0F2F5'}};c.font={bold:true,size:9};c.border=borderThin;c.alignment={horizontal:'center'};});
    for (var yy in PARAMS) {
      var pr = ws2.addRow([parseInt(yy), PARAMS[yy].SMLMV, PARAMS[yy].AUX]);
      pr.getCell(2).numFmt = copFmt; pr.getCell(3).numFmt = copFmt;
      pr.eachCell(function(c){c.border=borderThin;c.alignment={horizontal:'center'};c.font={size:9};});
      if (parseInt(yy)===r.anioLiq) pr.eachCell(function(c){c.fill=greenFill;c.font={bold:true,size:9,color:{argb:'FF065F46'}};});
    }

    // ══ Hoja 3: Verificación ══
    var ws3 = wb.addWorksheet('Verificación');
    ws3.columns = [{width:38},{width:48},{width:22}];
    ws3.mergeCells('A1:C1');
    var vt = ws3.getCell('A1');
    vt.value = 'HOJA DE VERIFICACIÓN'; vt.fill = hdrFill; vt.font = hdrFont; vt.alignment={horizontal:'center'};
    ws3.getRow(1).height = 28;
    ws3.addRow([]);
    var vh = ws3.addRow(['Check','Condición','Resultado']);
    vh.eachCell(function(c){c.fill={type:'pattern',pattern:'solid',fgColor:{argb:'FFF0F2F5'}};c.font={bold:true,size:9};c.border=borderThin;});

    var checks = [
      ['Cesantías = SBL × días / 360', r.sblCesPrima+' × '+r.diasAnio+' / 360 = '+fNum(Math.round(r.sblCesPrima*r.diasAnio/360)), r.cesantias===Math.round(r.sblCesPrima*r.diasAnio/360)?'CORRECTO':'REVISAR'],
      ['Intereses = Ces × días × 12% / 360', r.cesantias+' × '+r.diasAnio+' × 0.12 / 360 = '+fNum(Math.round(r.cesantias*r.diasAnio*0.12/360)), r.intereses===Math.round(r.cesantias*r.diasAnio*0.12/360)?'CORRECTO':'REVISAR'],
      ['Vacaciones sobre salario básico', 'Base: '+fCOP(r.sblVac)+' (NO incluye aux. transporte)', r.sblVac===(r.esIntegral?Math.round(r.salario*0.7):r.salario)?'CORRECTO':'REVISAR'],
      ['Auxilio transporte aplica', 'Salario '+fCOP(r.salario)+' vs 2 SMLMV = '+fCOP(r.params.SMLMV*2), r.salario<=r.params.SMLMV*2?(r.auxTransporte>0?'CORRECTO':'REVISAR'):(r.auxTransporte===0?'CORRECTO':'REVISAR')],
      ['Salario integral ≥ 13 SMLMV', r.esIntegral?'Salario '+fCOP(r.salario)+' vs 13 SMLMV = '+fCOP(r.params.SMLMV*13):'No es integral', r.esIntegral?(r.salario>=r.params.SMLMV*13?'CORRECTO':'ALERTA'):'N/A']
    ];
    checks.forEach(function(ck){
      var cr = ws3.addRow(ck);
      cr.getCell(1).font = {size:9};
      cr.getCell(2).font = {size:8,color:{argb:'FF6B7280'}};
      cr.getCell(3).font = {bold:true,size:9,color:{argb:ck[2]==='CORRECTO'?'FF059669':(ck[2]==='N/A'?'FF6B7280':'FFDC2626')}};
      if(ck[2]==='CORRECTO') cr.getCell(3).fill=greenFill;
      else if(ck[2]!=='N/A') cr.getCell(3).fill={type:'pattern',pattern:'solid',fgColor:{argb:'FFFEF2F2'}};
      cr.eachCell(function(c){c.border=borderThin;});
    });

    // Guardar
    wb.xlsx.writeBuffer().then(function(buf){
      var blob = new Blob([buf], {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = 'Liquidacion_Laboral_' + (r.empleado||'trabajador').replace(/\s+/g,'_') + '.xlsx';
      a.click();
      URL.revokeObjectURL(url);
    });
  } catch(e) {
    alert('Error al generar Excel: ' + e.message);
  }
}
