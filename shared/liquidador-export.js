/* ═══ ExógenaDIAN — Exportaciones Liquidador Laboral (PDF + Excel) ═══ */

/* ─── PDF con jsPDF + autoTable ─── */
function exportarPDF(r) {
  var doc = new jspdf.jsPDF('p','mm','letter');
  var W = 216, M = 18, cw = W - 2*M;
  var y = 18;

  // Header
  doc.setFillColor(27,58,92);
  doc.rect(0,0,W,42,'F');
  doc.setTextColor(255);
  doc.setFontSize(16);
  doc.setFont('helvetica','bold');
  doc.text('LIQUIDACIÓN DE CONTRATO DE TRABAJO', M, y);
  y += 7;
  doc.setFontSize(9);
  doc.setFont('helvetica','normal');
  var hoy = new Date();
  doc.text('Fecha: ' + hoy.toLocaleDateString('es-CO') + '  |  exogenadian.com', M, y);
  y += 6;
  doc.text('Ley 2466/2025 — Normativa laboral vigente ' + r.anioLiq, M, y);
  y += 16;
  doc.setTextColor(0);

  // Sección 1: Partes
  doc.setFontSize(10);
  doc.setFont('helvetica','bold');
  doc.text('1. DATOS DEL CONTRATO', M, y); y += 6;
  doc.setFont('helvetica','normal');
  doc.setFontSize(9);

  var causasTxt = {sin_justa_causa:'Despido sin justa causa',justa_causa:'Despido con justa causa',renuncia:'Renuncia voluntaria',mutuo_acuerdo:'Mutuo acuerdo',vencimiento:'Vencimiento contrato fijo',fin_obra:'Terminación de obra'};
  var tiposTxt = {indefinido:'Término indefinido',fijo:'Término fijo',obra:'Obra o labor'};

  var datos1 = [
    ['Empleador', (r.empleador||'—') + (r.nitEmpleador ? ' — NIT: '+r.nitEmpleador : '')],
    ['Trabajador', r.empleado||'—'],
    ['Cargo', r.cargo||'—'],
    ['Tipo de contrato', tiposTxt[r.tipoContrato]||r.tipoContrato],
    ['Causa de terminación', causasTxt[r.causa]||r.causa],
    ['Fecha inicio', r.fechaInicio.toLocaleDateString('es-CO')],
    ['Fecha terminación', r.fechaFin.toLocaleDateString('es-CO')],
    ['Tiempo laborado', r.periodoTexto + ' (' + r.diasTotal + ' días)']
  ];

  doc.autoTable({
    startY: y, margin: {left:M,right:M}, theme:'plain',
    body: datos1,
    columnStyles: {0:{fontStyle:'bold',cellWidth:50},1:{cellWidth:cw-50}},
    styles: {fontSize:8.5,cellPadding:2.5}
  });
  y = doc.lastAutoTable.finalY + 8;

  // Sección 2: Salario
  doc.setFontSize(10);
  doc.setFont('helvetica','bold');
  doc.text('2. BASE SALARIAL', M, y); y += 6;

  var datos2 = [
    ['Salario básico mensual', fCOP(r.salario) + (r.esIntegral?' (integral)':'')],
    ['Auxilio de transporte', r.auxTransporte>0 ? fCOP(r.auxTransporte)+'/mes' : 'No aplica'],
    ['SBL Cesantías y Prima', fCOP(r.sblCesPrima)],
    ['SBL Vacaciones', fCOP(r.sblVac)]
  ];

  doc.autoTable({
    startY: y, margin:{left:M,right:M}, theme:'plain', body:datos2,
    columnStyles:{0:{fontStyle:'bold',cellWidth:50},1:{cellWidth:cw-50}},
    styles:{fontSize:8.5,cellPadding:2.5}
  });
  y = doc.lastAutoTable.finalY + 8;

  // Sección 3: Liquidación detallada
  doc.setFontSize(10);
  doc.setFont('helvetica','bold');
  doc.text('3. LIQUIDACIÓN DETALLADA', M, y); y += 2;

  var filas = [
    ['Salario proporcional ('+r.diaDelMes+' días)', fCOP(r.salDiario)+'/día', r.diaDelMes+'', fCOP(r.salProporcional)],
  ];
  if (r.auxProporcional>0) {
    filas.push(['Auxilio transporte proporcional', fCOP(r.auxTransporte)+'/mes', r.diaDelMes+' días', fCOP(r.auxProporcional)]);
  }
  filas.push(
    ['Cesantías (Art. 249 CST)', fCOP(r.sblCesPrima), r.diasAnio+' días', fCOP(r.cesantias)],
    ['Intereses cesantías (Ley 52/75)', fCOP(r.cesantias), r.diasAnio+' días × 12%', fCOP(r.intereses)],
    ['Prima de servicios (Art. 306 CST)', fCOP(r.sblCesPrima), r.diasSemestre+' días sem.', fCOP(r.prima)],
    ['Vacaciones (Art. 186 CST)', fCOP(r.sblVac), r.vacaciones.diasPendientes.toFixed(1)+' días pend.', fCOP(r.vacaciones.valor)]
  );

  if (r.indemnizacion.aplica) {
    filas.push(['INDEMNIZACIÓN (Art. 64 CST)', fCOP(r.salario), r.indemnizacion.dias+' días', fCOP(r.indemnizacion.valor)]);
  }

  filas.push(['', '', 'SUBTOTAL DEVENGADO', fCOP(r.subtotal)]);

  if (r.anticipos>0) filas.push(['(-) Anticipos cesantías','','', '-'+fCOP(r.anticipos)]);
  if (r.prestamos>0) filas.push(['(-) Préstamos/libranzas','','', '-'+fCOP(r.prestamos)]);

  filas.push(['','','TOTAL A PAGAR', fCOP(r.total)]);

  doc.autoTable({
    startY: y, margin:{left:M,right:M}, theme:'grid',
    head: [['Concepto','Base','Días/Factor','Valor COP']],
    body: filas,
    headStyles:{fillColor:[27,58,92],fontSize:8,fontStyle:'bold',halign:'center'},
    styles:{fontSize:8,cellPadding:3},
    columnStyles:{0:{cellWidth:60},3:{halign:'right',fontStyle:'bold'}},
    didParseCell: function(data) {
      if (data.section==='body') {
        var txt = data.cell.raw||'';
        if (txt.indexOf('TOTAL A PAGAR')>=0 || txt.indexOf('SUBTOTAL')>=0) {
          data.cell.styles.fontStyle='bold';
          data.cell.styles.fillColor=[236,253,245];
        }
        if (txt.indexOf('INDEMNIZACIÓN')>=0) {
          data.cell.styles.fillColor=[255,247,237];
          data.cell.styles.fontStyle='bold';
        }
      }
    }
  });
  y = doc.lastAutoTable.finalY + 10;

  // Firmas
  if (y > 220) { doc.addPage(); y = 25; }
  doc.setFontSize(10);
  doc.setFont('helvetica','bold');
  doc.text('4. FIRMAS', M, y); y += 12;
  doc.setFont('helvetica','normal');
  doc.setFontSize(8);
  doc.line(M, y, M+70, y);
  doc.line(W-M-70, y, W-M, y);
  y += 5;
  doc.text('El Empleador', M, y);
  doc.text('El Trabajador', W-M-70, y);
  y += 4;
  doc.text(r.empleador||'________________________', M, y);
  doc.text(r.empleado||'________________________', W-M-70, y);

  // Pie
  y += 14;
  doc.setFontSize(6.5);
  doc.setTextColor(120);
  doc.text('Documento generado por exogenadian.com | Arts. 249, 306, 186, 64 CST | Ley 2466/2025 | Valores vigentes '+r.anioLiq, M, y);
  y += 3.5;
  doc.text('Este documento es informativo y orientativo. Consulte con un abogado laboral para casos con complejidades adicionales.', M, y);

  doc.save('Liquidacion_Laboral_' + (r.empleado||'').replace(/\s/g,'_') + '.pdf');
}

/* ─── Excel con SheetJS ─── */
function exportarExcel(r) {
  var wb = XLSX.utils.book_new();
  var causasTxt = {sin_justa_causa:'Despido sin justa causa',justa_causa:'Despido con justa causa',renuncia:'Renuncia voluntaria',mutuo_acuerdo:'Mutuo acuerdo',vencimiento:'Vencimiento contrato fijo',fin_obra:'Terminación de obra'};
  var tiposTxt = {indefinido:'Término indefinido',fijo:'Término fijo',obra:'Obra o labor'};

  // Hoja 1: Liquidación
  var data = [
    ['LIQUIDACIÓN DE CONTRATO DE TRABAJO','','','',''],
    ['Generado por exogenadian.com','','','Fecha:', new Date().toLocaleDateString('es-CO')],
    [],
    ['DATOS DEL CONTRATO'],
    ['Empleador:', r.empleador||'','','NIT:', r.nitEmpleador||''],
    ['Trabajador:', r.empleado||'','','Cargo:', r.cargo||''],
    ['Tipo contrato:', tiposTxt[r.tipoContrato]||'','','Causa:', causasTxt[r.causa]||''],
    ['Fecha inicio:', r.fechaInicio.toLocaleDateString('es-CO'),'','Fecha fin:', r.fechaFin.toLocaleDateString('es-CO')],
    ['Tiempo laborado:', r.periodoTexto,'','Días (base 360):', r.diasTotal],
    [],
    ['Concepto','Base (COP)','Días','Fórmula','Valor (COP)'],
    ['Salario proporcional', Math.round(r.salDiario), r.diaDelMes, 'Base × Días', r.salProporcional],
  ];
  if (r.auxProporcional>0) {
    data.push(['Auxilio transporte proporcional', r.auxTransporte, r.diaDelMes, 'Aux × Días / 30', r.auxProporcional]);
  }
  data.push(
    ['Cesantías (Art. 249 CST)', r.sblCesPrima, r.diasAnio, 'SBL × Días / 360', r.cesantias],
    ['Intereses cesantías (Ley 52/75)', r.cesantias, r.diasAnio, 'Ces × Días × 12% / 360', r.intereses],
    ['Prima de servicios (Art. 306 CST)', r.sblCesPrima, r.diasSemestre, 'SBL × Días / 360', r.prima],
    ['Vacaciones (Art. 186 CST)', r.sblVac, r.vacaciones.diasPendientes, 'Sal / 30 × Días pend.', r.vacaciones.valor]
  );
  if (r.indemnizacion.aplica) {
    data.push(['INDEMNIZACIÓN (Art. 64 CST)', r.salario, r.indemnizacion.dias, r.indemnizacion.formula||'', r.indemnizacion.valor]);
  }
  data.push(
    [],
    ['','','','SUBTOTAL DEVENGADO', r.subtotal]
  );
  if (r.anticipos>0) data.push(['','','','(-) Anticipos cesantías', -r.anticipos]);
  if (r.prestamos>0) data.push(['','','','(-) Préstamos/libranzas', -r.prestamos]);
  data.push(['','','','TOTAL A PAGAR', r.total]);

  var ws = XLSX.utils.aoa_to_sheet(data);
  ws['!cols'] = [{wch:35},{wch:18},{wch:12},{wch:28},{wch:18}];
  XLSX.utils.book_append_sheet(wb, ws, 'Liquidación');

  // Hoja 2: Parámetros
  var pData = [
    ['PARÁMETROS LABORALES ' + r.anioLiq],
    [],['Año','SMLMV','Auxilio Transporte']
  ];
  for (var y in PARAMS) {
    pData.push([parseInt(y), PARAMS[y].SMLMV, PARAMS[y].AUX]);
  }
  var ws2 = XLSX.utils.aoa_to_sheet(pData);
  ws2['!cols'] = [{wch:10},{wch:15},{wch:20}];
  XLSX.utils.book_append_sheet(wb, ws2, 'Parámetros');

  // Hoja 3: Verificación
  var vData = [
    ['HOJA DE VERIFICACIÓN'],
    [],
    ['Check','Condición','Resultado'],
    ['Cesantías = SBL × días / 360', r.sblCesPrima+'×'+r.diasAnio+'/360 = '+Math.round(r.sblCesPrima*r.diasAnio/360), r.cesantias === Math.round(r.sblCesPrima*r.diasAnio/360) ? 'CORRECTO':'REVISAR'],
    ['Intereses = Ces × días × 12% / 360', r.cesantias+'×'+r.diasAnio+'×0.12/360 = '+Math.round(r.cesantias*r.diasAnio*0.12/360), r.intereses === Math.round(r.cesantias*r.diasAnio*0.12/360) ? 'CORRECTO':'REVISAR'],
    ['Vacaciones sobre salario básico', 'Base usada: '+r.sblVac+' (NO incluye aux. transporte)', r.sblVac === (r.esIntegral?Math.round(r.salario*0.7):r.salario) ? 'CORRECTO':'REVISAR'],
    ['Auxilio transporte aplica', 'Salario '+r.salario+' vs 2 SMLMV = '+(r.params.SMLMV*2), r.salario <= r.params.SMLMV*2 ? (r.auxTransporte>0?'CORRECTO: Sí aplica':'REVISAR') : (r.auxTransporte===0?'CORRECTO: No aplica':'REVISAR')],
    ['Salario integral ≥ 13 SMLMV', r.esIntegral ? 'Salario '+r.salario+' vs 13 SMLMV = '+(r.params.SMLMV*13) : 'No es integral', r.esIntegral ? (r.salario >= r.params.SMLMV*13 ? 'CORRECTO':'ALERTA: Salario < 13 SMLMV') : 'N/A']
  ];
  var ws3 = XLSX.utils.aoa_to_sheet(vData);
  ws3['!cols'] = [{wch:35},{wch:45},{wch:25}];
  XLSX.utils.book_append_sheet(wb, ws3, 'Verificación');

  XLSX.writeFile(wb, 'Liquidacion_Laboral_' + (r.empleado||'').replace(/\s/g,'_') + '.xlsx');
}
