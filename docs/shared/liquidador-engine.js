/* ═══ ExógenaDIAN — Motor de Cálculo Liquidación Laboral ═══
   Normativa: CST Arts. 249, 306, 186-189, 64 | Ley 52/75 | Ley 2466/2025
   Sentencia SL1659-2025 CSJ (salario variable)
*/
var PARAMS = {
  2026: { SMLMV: 1423500, AUX: 200000 },
  2025: { SMLMV: 1423500, AUX: 200000 },
  2024: { SMLMV: 1300000, AUX: 162000 },
  2023: { SMLMV: 1160000, AUX: 140606 },
  2022: { SMLMV: 1000000, AUX: 117172 },
  2021: { SMLMV: 908526,  AUX: 106454 },
  2020: { SMLMV: 877803,  AUX: 102854 }
};

function getParams(y) {
  return PARAMS[y] || PARAMS[2026];
}

/* ─── Días entre dos fechas (método laboral 360) ─── */
function dias360(d1, d2) {
  var y1=d1.getFullYear(), m1=d1.getMonth()+1, dd1=Math.min(d1.getDate(),30);
  var y2=d2.getFullYear(), m2=d2.getMonth()+1, dd2=Math.min(d2.getDate(),30);
  return (y2-y1)*360 + (m2-m1)*30 + (dd2-dd1);
}

/* Días reales entre fechas */
function diasReales(d1, d2) {
  return Math.round((d2-d1)/(1000*60*60*24));
}

/* ─── Período en texto ─── */
function periodoTexto(d1, d2) {
  var total = dias360(d1, d2);
  var a = Math.floor(total/360);
  var m = Math.floor((total%360)/30);
  var d = total%30;
  var t = '';
  if (a>0) t += a + (a===1?' año':' años');
  if (m>0) t += (t?', ':'') + m + (m===1?' mes':' meses');
  if (d>0) t += (t?' , ':'') + d + (d===1?' día':' días');
  return t || '0 días';
}

/* ─── Salario Base Liquidación ─── */
function calcularSBL(salario, auxTransporte, esIntegral, esVariable, promedioVariable) {
  if (esIntegral) return Math.round(salario * 0.7);
  var base = salario;
  if (esVariable) base = salario + (promedioVariable || 0);
  if (auxTransporte > 0) base += auxTransporte;
  return Math.round(base);
}

function sblVacaciones(salario, esIntegral) {
  if (esIntegral) return Math.round(salario * 0.7);
  return salario;
}

/* ─── Auxilio de transporte proporcional ─── */
function auxProporcional(aux, dias) {
  return Math.round(aux * dias / 360);
}

/* ─── Cesantías Art. 249 CST ─── */
function calcCesantias(sbl, dias) {
  return Math.round(sbl * dias / 360);
}

/* ─── Intereses sobre cesantías — Ley 52/75 ─── */
function calcIntereses(cesantias, dias) {
  return Math.round(cesantias * dias * 0.12 / 360);
}

/* ─── Prima de servicios Art. 306 CST ─── */
function calcPrima(sbl, diasSemestre) {
  return Math.round(sbl * diasSemestre / 360);
}

/* ─── Vacaciones Art. 186-189 CST ─── */
function calcVacaciones(salBasico, diasTrabajados, diasDisfrutados) {
  var diasDerecho = Math.round(diasTrabajados * 15 / 360 * 100) / 100;
  var diasPendientes = Math.max(0, diasDerecho - (diasDisfrutados || 0));
  var valor = Math.round(salBasico * diasPendientes / 30);
  return { diasDerecho: diasDerecho, diasDisfrutados: diasDisfrutados||0, diasPendientes: diasPendientes, valor: valor };
}

/* ─── Indemnización Art. 64 CST ─── */
function calcIndemnizacion(causa, tipoContrato, salario, diasTrabajados, esIntegral, fechaFin, fechaVencimiento) {
  var noAplica = ['renuncia','justa_causa','mutuo_acuerdo','vencimiento'];
  if (noAplica.indexOf(causa) >= 0) {
    var razones = {
      renuncia: 'Renuncia voluntaria — no genera indemnización',
      justa_causa: 'Despido con justa causa (Art. 62 CST) — no genera indemnización',
      mutuo_acuerdo: 'Terminación por mutuo acuerdo — no genera indemnización',
      vencimiento: 'Vencimiento del término pactado — no genera indemnización'
    };
    return { aplica: false, causa: razones[causa], dias: 0, valor: 0 };
  }

  var base = esIntegral ? Math.round(salario * 0.7) : salario;
  var diario = base / 30;
  var anios = Math.floor(diasTrabajados / 360);
  var fraccion = diasTrabajados % 360;

  // Contrato fijo u obra
  if (tipoContrato === 'fijo') {
    if (!fechaVencimiento || fechaFin >= fechaVencimiento) {
      return { aplica: false, causa: 'Contrato fijo ya vencido — no aplica indemnización', dias: 0, valor: 0 };
    }
    var diasRestantes = diasReales(fechaFin, fechaVencimiento);
    var valor = Math.max(diario * diasRestantes, diario * 15);
    return { aplica: true, causa: 'Despido sin justa causa — contrato fijo', dias: Math.max(diasRestantes, 15), valor: Math.round(valor),
      formula: 'Salarios restantes hasta vencimiento (mín. 15 días)' };
  }
  if (tipoContrato === 'obra') {
    var diasMin = 15;
    var valor2 = diario * Math.max(diasMin, 60); // estimado 60 días si no hay fecha
    return { aplica: true, causa: 'Despido sin justa causa — obra o labor', dias: Math.max(diasMin, 60), valor: Math.round(valor2),
      formula: 'Salarios hasta fin estimado de obra (mín. 15 días)' };
  }

  // Contrato indefinido
  var p = getParams(fechaFin ? fechaFin.getFullYear() : 2026);
  var umbral10 = p.SMLMV * 10;
  var diasIndem, formula;

  if (base < umbral10) {
    // Caso A: < 10 SMLMV
    if (anios < 1) {
      diasIndem = 30;
      formula = '30 días (primer año o fracción < 1 año)';
    } else {
      var adicionales = anios - 1;
      var fracDias = fraccion > 0 ? (20 * fraccion / 360) : 0;
      diasIndem = 30 + (20 * adicionales) + fracDias;
      formula = '30 + (20 × ' + adicionales + ' años)' + (fraccion > 0 ? ' + (20 × ' + fraccion + '/360)' : '');
    }
  } else {
    // Caso B: >= 10 SMLMV
    if (anios < 1) {
      diasIndem = 20;
      formula = '20 días (primer año o fracción — salario ≥ 10 SMLMV)';
    } else {
      var adic = anios - 1;
      var fracD = fraccion > 0 ? (15 * fraccion / 360) : 0;
      diasIndem = 20 + (15 * adic) + fracD;
      formula = '20 + (15 × ' + adic + ' años)' + (fraccion > 0 ? ' + (15 × ' + fraccion + '/360)' : '');
    }
  }

  return { aplica: true, causa: 'Despido sin justa causa — contrato indefinido', dias: Math.round(diasIndem*100)/100,
    valor: Math.round(diario * diasIndem), formula: formula };
}

/* ─── Días del semestre en curso ─── */
function diasSemestreActual(fechaFin) {
  var m = fechaFin.getMonth(); // 0-11
  var inicioSem;
  if (m < 6) {
    inicioSem = new Date(fechaFin.getFullYear(), 0, 1);
  } else {
    inicioSem = new Date(fechaFin.getFullYear(), 6, 1);
  }
  return dias360(inicioSem, fechaFin);
}

/* ─── Días del año en curso ─── */
function diasAnioActual(fechaInicio, fechaFin) {
  var inicioAnio = new Date(fechaFin.getFullYear(), 0, 1);
  var desde = fechaInicio > inicioAnio ? fechaInicio : inicioAnio;
  return dias360(desde, fechaFin);
}

/* ─── LIQUIDACIÓN COMPLETA ─── */
function liquidar(d) {
  var fi = new Date(d.fechaInicio);
  var ff = new Date(d.fechaFin);
  var anioFin = ff.getFullYear();
  var p = getParams(anioFin);

  var salario = d.salario;
  var esIntegral = d.tipoSalario === 'integral';
  var esVariable = d.esVariable && d.promedioVariable > 0;

  // Auxilio de transporte
  var auxTrans = 0;
  if (!esIntegral && salario <= p.SMLMV * 2) {
    auxTrans = p.AUX;
  }

  // Días
  var diasTotal = dias360(fi, ff);
  var diasAnio = diasAnioActual(fi, ff);
  var diasSem = diasSemestreActual(ff);
  // Ajustar si el contrato empezó después del inicio del semestre
  var inicioSem = ff.getMonth() < 6 ? new Date(anioFin,0,1) : new Date(anioFin,6,1);
  if (fi > inicioSem) diasSem = dias360(fi, ff);
  // Ajustar si empezó después del inicio del año
  var inicioAnio = new Date(anioFin,0,1);
  if (fi > inicioAnio) diasAnio = diasTotal;

  // SBL
  var sblCesPrima = calcularSBL(salario, auxTrans, esIntegral, esVariable, d.promedioVariable);
  var sblVac = sblVacaciones(salario, esIntegral);

  // Prestaciones
  var cesantias = calcCesantias(sblCesPrima, diasAnio);
  var intereses = calcIntereses(cesantias, diasAnio);
  var prima = calcPrima(sblCesPrima, diasSem);
  var vac = calcVacaciones(sblVac, diasTotal, d.diasVacDisfrutados || 0);

  // Salario proporcional último mes
  var diaDelMes = ff.getDate();
  var salDiario = (esIntegral ? Math.round(salario*0.7) : salario) / 30;
  var salProporcional = Math.round(salDiario * diaDelMes);

  // Aux transporte proporcional
  var auxProp = auxTrans > 0 ? Math.round(auxTrans * diaDelMes / 30) : 0;

  // Indemnización
  var fv = d.fechaVencimiento ? new Date(d.fechaVencimiento) : null;
  var indem = calcIndemnizacion(d.causa, d.tipoContrato, salario, diasTotal, esIntegral, ff, fv);

  // Deducciones
  var anticipos = d.anticiposCesantias || 0;
  var prestamos = d.prestamos || 0;

  // Totales
  var subtotal = cesantias + intereses + prima + vac.valor + salProporcional + auxProp;
  if (indem.aplica) subtotal += indem.valor;
  var deducciones = anticipos + prestamos;
  var total = subtotal - deducciones;

  return {
    empleado: d.empleado || '',
    empleador: d.empleador || '',
    nitEmpleador: d.nitEmpleador || '',
    cargo: d.cargo || '',
    tipoContrato: d.tipoContrato,
    causa: d.causa,
    fechaInicio: fi,
    fechaFin: ff,
    diasTotal: diasTotal,
    diasAnio: diasAnio,
    diasSemestre: diasSem,
    periodoTexto: periodoTexto(fi, ff),
    salario: salario,
    esIntegral: esIntegral,
    auxTransporte: auxTrans,
    auxProporcional: auxProp,
    sblCesPrima: sblCesPrima,
    sblVac: sblVac,
    cesantias: cesantias,
    intereses: intereses,
    prima: prima,
    vacaciones: vac,
    salProporcional: salProporcional,
    salDiario: salDiario,
    diaDelMes: diaDelMes,
    indemnizacion: indem,
    anticipos: anticipos,
    prestamos: prestamos,
    subtotal: subtotal,
    deducciones: deducciones,
    total: total,
    anioLiq: anioFin,
    params: p,
    normativa: getNormativa(indem.aplica, esIntegral, esVariable)
  };
}

function getNormativa(hayIndem, integral, variable) {
  var n = ['Art. 249 CST — Cesantías','Ley 52/1975 — Intereses sobre cesantías',
    'Art. 306 CST — Prima de servicios','Arts. 186-189 CST — Vacaciones'];
  if (hayIndem) n.push('Art. 64 CST — Indemnización por despido sin justa causa');
  if (integral) n.push('Art. 132 CST — Salario integral');
  if (variable) n.push('Sentencia SL1659-2025 CSJ — Salario variable');
  n.push('Ley 2466 de 2025 — Reforma laboral vigente');
  return n;
}

/* ─── Formato COP ─── */
function fCOP(n) {
  if (n == null || isNaN(n)) return '$0';
  return '$' + Math.round(n).toLocaleString('es-CO');
}

function fNum(n) {
  return Math.round(n).toLocaleString('es-CO');
}
