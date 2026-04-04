/* ═══ Exportaciones Liquidador Laboral (PDF + Excel + Word) ═══ */

var _causasTxt={sin_justa_causa:'Despido sin justa causa',justa_causa:'Despido con justa causa',renuncia:'Renuncia voluntaria',mutuo_acuerdo:'Mutuo acuerdo',vencimiento:'Vencimiento contrato fijo',fin_obra:'Terminación de obra'};
var _tiposTxt={indefinido:'Término indefinido',fijo:'Término fijo',obra:'Obra o labor'};

/* ═══ PDF ═══ */
function exportarPDF(r){
  try{
    var J=(window.jspdf&&window.jspdf.jsPDF)||window.jsPDF;
    if(!J){alert('Error: jsPDF no cargó. Recarga la página.');return;}
    var doc=new J('p','mm','letter');
  }catch(e){alert('Error PDF: '+e.message);return;}
  var W=216,M=18,cw=W-2*M,y=18;

  doc.setFillColor(27,58,92);doc.rect(0,0,W,40,'F');
  doc.setTextColor(255,255,255);doc.setFontSize(15);doc.setFont('helvetica','bold');
  doc.text('LIQUIDACIÓN DE CONTRATO DE TRABAJO',M,y);y+=8;
  doc.setFontSize(9);doc.setFont('helvetica','normal');
  doc.text('Fecha: '+new Date().toLocaleDateString('es-CO')+'  |  Ley 2466/2025 — Normativa vigente '+r.anioLiq,M,y);
  y+=17;doc.setTextColor(0);

  // Datos
  _pdfSection(doc,M,cw,y,'1. DATOS DEL CONTRATO');y+=8;
  doc.autoTable({startY:y,margin:{left:M,right:M},theme:'plain',
    body:[['Empleador',(r.empleador||'—')+(r.nitEmpleador?' — NIT: '+r.nitEmpleador:'')],['Trabajador',r.empleado||'—'],['Cargo',r.cargo||'—'],['Tipo contrato',_tiposTxt[r.tipoContrato]||''],['Causa terminación',_causasTxt[r.causa]||''],['Período',r.fechaInicio.toLocaleDateString('es-CO')+' al '+r.fechaFin.toLocaleDateString('es-CO')+' ('+r.periodoTexto+')']],
    columnStyles:{0:{fontStyle:'bold',cellWidth:48,textColor:[107,114,128]},1:{cellWidth:cw-48}},
    styles:{fontSize:8.5,cellPadding:2.5,lineColor:[226,232,240],lineWidth:0.2},alternateRowStyles:{fillColor:[249,250,251]}
  });y=doc.lastAutoTable.finalY+6;

  // Salario
  _pdfSection(doc,M,cw,y,'2. BASE SALARIAL');y+=8;
  doc.autoTable({startY:y,margin:{left:M,right:M},theme:'plain',
    body:[['Salario básico',fCOP(r.salario)+(r.esIntegral?' (integral — 70% = '+fCOP(Math.round(r.salario*0.7))+')':'')],['Aux. transporte',r.auxTransporte>0?fCOP(r.auxTransporte)+'/mes':'No aplica'],['SBL Cesantías/Prima',fCOP(r.sblCesPrima)],['SBL Vacaciones',fCOP(r.sblVac)]],
    columnStyles:{0:{fontStyle:'bold',cellWidth:48,textColor:[107,114,128]},1:{cellWidth:cw-48}},
    styles:{fontSize:8.5,cellPadding:2.5,lineColor:[226,232,240],lineWidth:0.2},alternateRowStyles:{fillColor:[249,250,251]}
  });y=doc.lastAutoTable.finalY+6;

  // Liquidación
  _pdfSection(doc,M,cw,y,'3. LIQUIDACIÓN DETALLADA');y+=6;
  var filas=[['Salario proporcional ('+r.diaDelMes+' d)',fCOP(Math.round(r.salDiario))+'/día',r.diaDelMes+'',fCOP(r.salProporcional)]];
  if(r.auxProporcional>0)filas.push(['Aux. transporte prop.',fCOP(r.auxTransporte)+'/mes',r.diaDelMes+' d',fCOP(r.auxProporcional)]);
  filas.push(['Cesantías (Art. 249)',fCOP(r.sblCesPrima),r.diasAnio+' d',fCOP(r.cesantias)],['Intereses cesantías (Ley 52/75)',fCOP(r.cesantias),r.diasAnio+' d × 12%',fCOP(r.intereses)],['Prima de servicios (Art. 306)',fCOP(r.sblCesPrima),r.diasSemestre+' d sem.',fCOP(r.prima)],['Vacaciones (Art. 186)',fCOP(r.sblVac),r.vacaciones.diasPendientes.toFixed(1)+' d pend.',fCOP(r.vacaciones.valor)]);
  if(r.indemnizacion.aplica)filas.push(['INDEMNIZACIÓN (Art. 64)',fCOP(r.salario),r.indemnizacion.dias.toFixed(1)+' d',fCOP(r.indemnizacion.valor)]);
  filas.push(['','','SUBTOTAL',fCOP(r.subtotal)]);
  if(r.anticipos>0)filas.push(['(-) Anticipos cesantías','','','-'+fCOP(r.anticipos)]);
  if(r.prestamos>0)filas.push(['(-) Préstamos','','','-'+fCOP(r.prestamos)]);
  filas.push(['','','TOTAL A PAGAR',fCOP(r.total)]);

  doc.autoTable({startY:y,margin:{left:M,right:M},theme:'grid',
    head:[['Concepto','Base','Días','Valor COP']],body:filas,
    headStyles:{fillColor:[27,58,92],fontSize:7.5,fontStyle:'bold',halign:'center',cellPadding:3},
    styles:{fontSize:8,cellPadding:3,lineColor:[226,232,240],lineWidth:0.2},
    columnStyles:{0:{cellWidth:56},1:{cellWidth:38,halign:'right'},2:{cellWidth:30,halign:'center'},3:{halign:'right',fontStyle:'bold'}},
    alternateRowStyles:{fillColor:[249,250,251]},
    didParseCell:function(d){if(d.section==='body'){var t=String(d.cell.raw||'');
      if(t.indexOf('TOTAL A PAGAR')>=0){d.cell.styles.fillColor=[27,58,92];d.cell.styles.textColor=[255,255,255];d.cell.styles.fontStyle='bold';d.cell.styles.fontSize=9;}
      else if(t.indexOf('SUBTOTAL')>=0){d.cell.styles.fillColor=[209,250,229];d.cell.styles.textColor=[6,95,70];d.cell.styles.fontStyle='bold';}
      else if(t.indexOf('INDEMNIZACIÓN')>=0){d.cell.styles.fillColor=[255,247,237];d.cell.styles.fontStyle='bold';d.cell.styles.textColor=[194,65,12];}
      else if(t.indexOf('(-)')>=0){d.cell.styles.textColor=[220,38,38];}}}
  });y=doc.lastAutoTable.finalY+10;

  // Firmas
  if(y>215){doc.addPage();y=25;}
  doc.setDrawColor(180);doc.setFontSize(8);doc.setTextColor(0);
  doc.line(M,y+10,M+72,y+10);doc.line(W-M-72,y+10,W-M,y+10);
  doc.text('EL EMPLEADOR',M,y+15);doc.text('EL TRABAJADOR',W-M-72,y+15);
  doc.setFontSize(7);doc.setTextColor(120);
  doc.text('Nombre: '+(r.empleador||''),M,y+20);doc.text('Nombre: '+(r.empleado||''),W-M-72,y+20);
  doc.text('C.C./NIT: '+(r.nitEmpleador||''),M,y+25);doc.text('C.C.:',W-M-72,y+25);

  // Pie
  doc.setFontSize(6.5);doc.setTextColor(160);
  doc.text('Arts. 249, 306, 186-189, 64 CST | Ley 2466/2025 | Valores vigentes '+r.anioLiq+' | Documento informativo',M,270);

  try{doc.save('Liquidacion_'+(r.empleado||'trabajador').replace(/\s+/g,'_')+'.pdf');}catch(e){alert('Error guardando PDF: '+e.message);}
}

function _pdfSection(doc,M,cw,y,title){
  doc.setFillColor(240,242,245);doc.rect(M,y-4,cw,8,'F');
  doc.setFontSize(10);doc.setFont('helvetica','bold');doc.setTextColor(27,58,92);
  doc.text(title,M+3,y+1);doc.setTextColor(0);doc.setFont('helvetica','normal');
}

/* ═══ Excel con ExcelJS ═══ */
function exportarExcel(r){
  try{
    var wb=new ExcelJS.Workbook();wb.created=new Date();
    var ws=wb.addWorksheet('Liquidación');
    ws.columns=[{width:38},{width:20},{width:14},{width:30},{width:20}];
    var hF={type:'pattern',pattern:'solid',fgColor:{argb:'FF1B3A5C'}};
    var wF={bold:true,color:{argb:'FFFFFFFF'},size:11};
    var gF={type:'pattern',pattern:'solid',fgColor:{argb:'FFD1FAE5'}};
    var aF={type:'pattern',pattern:'solid',fgColor:{argb:'FFFFF7ED'}};
    var bdr={top:{style:'thin',color:{argb:'FFE2E8F0'}},bottom:{style:'thin',color:{argb:'FFE2E8F0'}},left:{style:'thin',color:{argb:'FFE2E8F0'}},right:{style:'thin',color:{argb:'FFE2E8F0'}}};

    ws.mergeCells('A1:E1');var c1=ws.getCell('A1');
    c1.value='LIQUIDACIÓN DE CONTRATO DE TRABAJO';c1.fill=hF;c1.font={bold:true,color:{argb:'FFFFFFFF'},size:14};c1.alignment={horizontal:'center',vertical:'middle'};ws.getRow(1).height=32;
    ws.mergeCells('A2:C2');ws.getCell('A2').value='Ley 2466/2025 — Valores '+r.anioLiq;ws.getCell('A2').font={italic:true,color:{argb:'FF6B7280'},size:9};
    ws.getCell('D2').value='Fecha:';ws.getCell('D2').font={bold:true,size:9};ws.getCell('E2').value=new Date().toLocaleDateString('es-CO');
    ws.addRow([]);

    ws.mergeCells('A4:E4');var h4=ws.getCell('A4');h4.value='DATOS DEL CONTRATO';h4.fill={type:'pattern',pattern:'solid',fgColor:{argb:'FFF0F2F5'}};h4.font={bold:true,color:{argb:'FF1B3A5C'},size:10};

    var info=[['Empleador:',r.empleador||'','','NIT:',r.nitEmpleador||''],['Trabajador:',r.empleado||'','','Cargo:',r.cargo||''],['Contrato:',_tiposTxt[r.tipoContrato]||'','','Causa:',_causasTxt[r.causa]||''],['Inicio:',r.fechaInicio.toLocaleDateString('es-CO'),'','Fin:',r.fechaFin.toLocaleDateString('es-CO')],['Tiempo:',r.periodoTexto,'','Días:',r.diasTotal]];
    info.forEach(function(row){var rw=ws.addRow(row);rw.getCell(1).font={bold:true,color:{argb:'FF6B7280'},size:9};rw.getCell(4).font={bold:true,color:{argb:'FF6B7280'},size:9};rw.eachCell(function(c){c.border=bdr;});});
    ws.addRow([]);

    var th=ws.addRow(['Concepto','Base (COP)','Días','Fórmula','Valor (COP)']);th.height=24;
    th.eachCell(function(c){c.fill=hF;c.font=wF;c.alignment={horizontal:'center',vertical:'middle'};});

    function addR(a,b,c,d,e,st){
      var rw=ws.addRow([a,b,c,d,e]);
      rw.getCell(2).numFmt='#,##0';rw.getCell(2).alignment={horizontal:'right'};
      rw.getCell(5).numFmt='#,##0';rw.getCell(5).alignment={horizontal:'right'};rw.getCell(5).font={bold:true,size:10};
      rw.getCell(3).alignment={horizontal:'center'};rw.getCell(4).font={size:8,italic:true,color:{argb:'FF6B7280'}};
      rw.eachCell(function(c){c.border=bdr;});
      if(st==='indem')rw.eachCell(function(c){c.fill=aF;});
      if(st==='subtotal'){rw.eachCell(function(c){c.fill=gF;});rw.getCell(5).font={bold:true,size:11,color:{argb:'FF065F46'}};}
      if(st==='total'){rw.eachCell(function(c){c.fill=hF;});rw.getCell(5).font={bold:true,size:12,color:{argb:'FFFFFFFF'}};rw.getCell(4).font={bold:true,size:11,color:{argb:'FFFFFFFF'}};rw.height=28;}
      if(st==='ded')rw.getCell(5).font={bold:true,size:10,color:{argb:'FFDC2626'}};
    }
    addR('Salario proporcional ('+r.diaDelMes+' d)',Math.round(r.salDiario),r.diaDelMes,'Sal/30 × Días',r.salProporcional);
    if(r.auxProporcional>0)addR('Aux. transporte prop.',r.auxTransporte,r.diaDelMes,'Aux × Días / 30',r.auxProporcional);
    addR('Cesantías (Art. 249)',r.sblCesPrima,r.diasAnio,'SBL × Días / 360',r.cesantias);
    addR('Intereses cesantías (Ley 52/75)',r.cesantias,r.diasAnio,'Ces × Días × 12% / 360',r.intereses);
    addR('Prima de servicios (Art. 306)',r.sblCesPrima,r.diasSemestre,'SBL × Días / 360',r.prima);
    addR('Vacaciones (Art. 186)',r.sblVac,r.vacaciones.diasPendientes,'Sal / 30 × Días pend.',r.vacaciones.valor);
    if(r.indemnizacion.aplica)addR('INDEMNIZACIÓN (Art. 64)',r.salario,r.indemnizacion.dias,r.indemnizacion.formula||'',r.indemnizacion.valor,'indem');
    ws.addRow([]);
    addR('','','','SUBTOTAL DEVENGADO',r.subtotal,'subtotal');
    if(r.anticipos>0)addR('','','','(-) Anticipos cesantías',-r.anticipos,'ded');
    if(r.prestamos>0)addR('','','','(-) Préstamos',-r.prestamos,'ded');
    addR('','','','TOTAL A PAGAR',r.total,'total');

    // Hoja Parámetros
    var ws2=wb.addWorksheet('Parámetros');ws2.columns=[{width:12},{width:18},{width:22}];
    ws2.mergeCells('A1:C1');ws2.getCell('A1').value='PARÁMETROS LABORALES '+r.anioLiq;ws2.getCell('A1').fill=hF;ws2.getCell('A1').font=wF;ws2.getCell('A1').alignment={horizontal:'center'};
    ws2.addRow([]);var ph=ws2.addRow(['Año','SMLMV','Aux. Transporte']);ph.eachCell(function(c){c.fill={type:'pattern',pattern:'solid',fgColor:{argb:'FFF0F2F5'}};c.font={bold:true,size:9};c.border=bdr;});
    for(var yy in PARAMS){var pr=ws2.addRow([parseInt(yy),PARAMS[yy].SMLMV,PARAMS[yy].AUX]);pr.getCell(2).numFmt='#,##0';pr.getCell(3).numFmt='#,##0';pr.eachCell(function(c){c.border=bdr;c.alignment={horizontal:'center'};});if(parseInt(yy)===r.anioLiq)pr.eachCell(function(c){c.fill=gF;c.font={bold:true,size:9,color:{argb:'FF065F46'}};});}

    // Hoja Verificación
    var ws3=wb.addWorksheet('Verificación');ws3.columns=[{width:36},{width:46},{width:22}];
    ws3.mergeCells('A1:C1');ws3.getCell('A1').value='HOJA DE VERIFICACIÓN';ws3.getCell('A1').fill=hF;ws3.getCell('A1').font=wF;ws3.getCell('A1').alignment={horizontal:'center'};
    ws3.addRow([]);ws3.addRow(['Check','Condición','Resultado']).eachCell(function(c){c.fill={type:'pattern',pattern:'solid',fgColor:{argb:'FFF0F2F5'}};c.font={bold:true,size:9};c.border=bdr;});
    var cks=[
      ['Cesantías = SBL × días / 360',fCOP(r.sblCesPrima)+' × '+r.diasAnio+' / 360 = '+fNum(Math.round(r.sblCesPrima*r.diasAnio/360)),r.cesantias===Math.round(r.sblCesPrima*r.diasAnio/360)?'CORRECTO':'REVISAR'],
      ['Intereses = Ces × días × 12% / 360',fCOP(r.cesantias)+' × '+r.diasAnio+' × 0.12 / 360',r.intereses===Math.round(r.cesantias*r.diasAnio*0.12/360)?'CORRECTO':'REVISAR'],
      ['Vacaciones sobre salario básico','Base: '+fCOP(r.sblVac),r.sblVac===(r.esIntegral?Math.round(r.salario*0.7):r.salario)?'CORRECTO':'REVISAR'],
      ['Aux. transporte aplica','Sal '+fCOP(r.salario)+' vs 2 SMLMV',r.salario<=r.params.SMLMV*2?(r.auxTransporte>0?'CORRECTO':'REVISAR'):(r.auxTransporte===0?'CORRECTO':'REVISAR')]
    ];
    cks.forEach(function(ck){var cr=ws3.addRow(ck);cr.getCell(3).font={bold:true,size:9,color:{argb:ck[2]==='CORRECTO'?'FF059669':'FFDC2626'}};if(ck[2]==='CORRECTO')cr.getCell(3).fill=gF;cr.eachCell(function(c){c.border=bdr;});});

    wb.xlsx.writeBuffer().then(function(buf){
      var b=new Blob([buf],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
      var a=document.createElement('a');a.href=URL.createObjectURL(b);
      a.download='Liquidacion_'+(r.empleado||'trabajador').replace(/\s+/g,'_')+'.xlsx';a.click();
    });
  }catch(e){alert('Error Excel: '+e.message);}
}

/* ═══ Word editable con docx.js ═══ */
function exportarWord(r){
  try{
    var D=window.docx;if(!D){alert('Librería Word no cargó. Recarga la página.');return;}
    var causaTxt=_causasTxt[r.causa]||r.causa;
    var tipoTxt=_tiposTxt[r.tipoContrato]||r.tipoContrato;

    // Filas de la tabla principal
    var tRows=[];
    function addTR(concepto,base,dias,valor,bold){
      tRows.push(new D.TableRow({children:[
        new D.TableCell({children:[new D.Paragraph({children:[new D.TextRun({text:concepto,bold:!!bold,size:18})]})],width:{size:3600,type:D.WidthType.DXA}}),
        new D.TableCell({children:[new D.Paragraph({children:[new D.TextRun({text:base,size:18})],alignment:D.AlignmentType.RIGHT})],width:{size:2000,type:D.WidthType.DXA}}),
        new D.TableCell({children:[new D.Paragraph({children:[new D.TextRun({text:String(dias),size:18})],alignment:D.AlignmentType.CENTER})],width:{size:1400,type:D.WidthType.DXA}}),
        new D.TableCell({children:[new D.Paragraph({children:[new D.TextRun({text:valor,bold:true,size:18})],alignment:D.AlignmentType.RIGHT})],width:{size:2000,type:D.WidthType.DXA}})
      ]}));
    }
    // Header
    tRows.push(new D.TableRow({children:['Concepto','Base','Días','Valor COP'].map(function(h){
      return new D.TableCell({children:[new D.Paragraph({children:[new D.TextRun({text:h,bold:true,color:'FFFFFF',size:18})],alignment:D.AlignmentType.CENTER})],shading:{fill:'1B3A5C'},width:{size:2250,type:D.WidthType.DXA}});
    })}));
    addTR('Salario proporcional ('+r.diaDelMes+' días)',fCOP(Math.round(r.salDiario))+'/día',r.diaDelMes,fCOP(r.salProporcional));
    if(r.auxProporcional>0)addTR('Aux. transporte proporcional',fCOP(r.auxTransporte),r.diaDelMes+' d',fCOP(r.auxProporcional));
    addTR('Cesantías (Art. 249 CST)',fCOP(r.sblCesPrima),r.diasAnio,fCOP(r.cesantias));
    addTR('Intereses cesantías (Ley 52/75)',fCOP(r.cesantias),r.diasAnio+' × 12%',fCOP(r.intereses));
    addTR('Prima de servicios (Art. 306)',fCOP(r.sblCesPrima),r.diasSemestre+' sem.',fCOP(r.prima));
    addTR('Vacaciones (Art. 186 CST)',fCOP(r.sblVac),r.vacaciones.diasPendientes.toFixed(1)+' pend.',fCOP(r.vacaciones.valor));
    if(r.indemnizacion.aplica)addTR('INDEMNIZACIÓN (Art. 64 CST)',fCOP(r.salario),r.indemnizacion.dias+'',fCOP(r.indemnizacion.valor),true);
    addTR('','','SUBTOTAL',fCOP(r.subtotal),true);
    if(r.anticipos>0)addTR('','','(-) Anticipos','-'+fCOP(r.anticipos));
    if(r.prestamos>0)addTR('','','(-) Préstamos','-'+fCOP(r.prestamos));
    addTR('','','TOTAL A PAGAR',fCOP(r.total),true);

    var doc=new D.Document({
      sections:[{
        properties:{page:{margin:{top:1000,right:1000,bottom:1000,left:1000}}},
        children:[
          new D.Paragraph({children:[new D.TextRun({text:'LIQUIDACIÓN DE CONTRATO DE TRABAJO',bold:true,size:28,color:'1B3A5C'})],alignment:D.AlignmentType.CENTER,spacing:{after:100}}),
          new D.Paragraph({children:[new D.TextRun({text:'Fecha: '+new Date().toLocaleDateString('es-CO')+'  |  Ley 2466/2025',size:18,color:'6B7280',italics:true})],alignment:D.AlignmentType.CENTER,spacing:{after:300}}),

          new D.Paragraph({children:[new D.TextRun({text:'1. DATOS DEL CONTRATO',bold:true,size:22,color:'1B3A5C'})],spacing:{after:100},border:{bottom:{color:'E2E8F0',space:4,style:D.BorderStyle.SINGLE,size:6}}}),
          _wp('Empleador: '+(r.empleador||'—')+(r.nitEmpleador?'  —  NIT: '+r.nitEmpleador:'')),
          _wp('Trabajador: '+(r.empleado||'—')),
          _wp('Cargo: '+(r.cargo||'—')),
          _wp('Tipo de contrato: '+tipoTxt),
          _wp('Causa de terminación: '+causaTxt),
          _wp('Período: '+r.fechaInicio.toLocaleDateString('es-CO')+' al '+r.fechaFin.toLocaleDateString('es-CO')+' ('+r.periodoTexto+')'),
          new D.Paragraph({text:'',spacing:{after:200}}),

          new D.Paragraph({children:[new D.TextRun({text:'2. BASE SALARIAL',bold:true,size:22,color:'1B3A5C'})],spacing:{after:100},border:{bottom:{color:'E2E8F0',space:4,style:D.BorderStyle.SINGLE,size:6}}}),
          _wp('Salario básico: '+fCOP(r.salario)+(r.esIntegral?' (integral — 70% = '+fCOP(Math.round(r.salario*0.7))+')':'')),
          _wp('Auxilio de transporte: '+(r.auxTransporte>0?fCOP(r.auxTransporte)+'/mes':'No aplica')),
          _wp('SBL Cesantías/Prima: '+fCOP(r.sblCesPrima)),
          _wp('SBL Vacaciones: '+fCOP(r.sblVac)),
          new D.Paragraph({text:'',spacing:{after:200}}),

          new D.Paragraph({children:[new D.TextRun({text:'3. LIQUIDACIÓN DETALLADA',bold:true,size:22,color:'1B3A5C'})],spacing:{after:100},border:{bottom:{color:'E2E8F0',space:4,style:D.BorderStyle.SINGLE,size:6}}}),
          new D.Table({rows:tRows,width:{size:9000,type:D.WidthType.DXA}}),
          new D.Paragraph({text:'',spacing:{after:400}}),

          new D.Paragraph({children:[new D.TextRun({text:'4. FIRMAS',bold:true,size:22,color:'1B3A5C'})],spacing:{after:300},border:{bottom:{color:'E2E8F0',space:4,style:D.BorderStyle.SINGLE,size:6}}}),
          new D.Paragraph({text:'',spacing:{after:200}}),
          new D.Table({rows:[new D.TableRow({children:[
            new D.TableCell({children:[new D.Paragraph({text:''}),new D.Paragraph({text:'________________________',spacing:{before:400}}),new D.Paragraph({children:[new D.TextRun({text:'EL EMPLEADOR',bold:true,size:18})]}),new D.Paragraph({children:[new D.TextRun({text:r.empleador||'',size:16,color:'6B7280'})]}),new D.Paragraph({children:[new D.TextRun({text:'C.C./NIT: '+(r.nitEmpleador||''),size:16,color:'6B7280'})]})],borders:{top:{style:D.BorderStyle.NONE},bottom:{style:D.BorderStyle.NONE},left:{style:D.BorderStyle.NONE},right:{style:D.BorderStyle.NONE}},width:{size:4500,type:D.WidthType.DXA}}),
            new D.TableCell({children:[new D.Paragraph({text:''}),new D.Paragraph({text:'________________________',spacing:{before:400}}),new D.Paragraph({children:[new D.TextRun({text:'EL TRABAJADOR',bold:true,size:18})]}),new D.Paragraph({children:[new D.TextRun({text:r.empleado||'',size:16,color:'6B7280'})]}),new D.Paragraph({children:[new D.TextRun({text:'C.C.:',size:16,color:'6B7280'})]})],borders:{top:{style:D.BorderStyle.NONE},bottom:{style:D.BorderStyle.NONE},left:{style:D.BorderStyle.NONE},right:{style:D.BorderStyle.NONE}},width:{size:4500,type:D.WidthType.DXA}})
          ]})],width:{size:9000,type:D.WidthType.DXA}}),
          new D.Paragraph({text:'',spacing:{after:300}}),
          new D.Paragraph({children:[new D.TextRun({text:'Arts. 249, 306, 186-189, 64 CST | Ley 2466/2025 | Valores vigentes '+r.anioLiq+' | Documento informativo y editable.',size:14,color:'9CA3AF',italics:true})],alignment:D.AlignmentType.CENTER})
        ]
      }]
    });

    D.Packer.toBlob(doc).then(function(blob){
      var a=document.createElement('a');a.href=URL.createObjectURL(blob);
      a.download='Liquidacion_'+(r.empleado||'trabajador').replace(/\s+/g,'_')+'.docx';a.click();
    });
  }catch(e){alert('Error Word: '+e.message);}
}

function _wp(text){return new docx.Paragraph({children:[new docx.TextRun({text:text,size:20})],spacing:{after:60}});}
