/**
 * Generador: Calculadora de Retención en la Fuente — ExógenaDIAN
 * Excel 100% formulado (no valores fijos). El usuario solo llena celdas amarillas.
 * Hojas: Asalariado P1, Asalariado P2, Independiente, Tabla Art.383
 */
const ExcelJS = require('exceljs');
const path = require('path');

async function generarExcel() {
  const wb = new ExcelJS.Workbook();
  wb.creator = 'ExógenaDIAN';
  wb.created = new Date();

  // ═══════════════════════════════════════════════
  // COLORES
  // ═══════════════════════════════════════════════
  const C = {
    dark: '0A0F1E',
    dark2: '111827',
    dark3: '1F2937',
    green: '22C55E',
    greenDark: '166534',
    greenLight: 'DCFCE7',
    yellow: 'FEF3C7',
    yellowBorder: 'F59E0B',
    white: 'FFFFFF',
    gray: '9CA3AF',
    grayLight: '6B7280',
    red: 'EF4444',
    blue: '3B82F6',
    orange: 'F97316',
  };

  const fontWhite = { color: { argb: C.white } };
  const fontGreen = { color: { argb: C.green }, bold: true };
  const fontGray = { color: { argb: C.gray } };
  const fontRed = { color: { argb: C.red } };
  const fontOrange = { color: { argb: C.orange } };
  const fontBlue = { color: { argb: C.blue } };

  const fillDark = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.dark } };
  const fillDark2 = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.dark2 } };
  const fillDark3 = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.dark3 } };
  const fillGreen = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.greenDark } };
  const fillYellow = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.yellow } };
  const fillInput = { type: 'pattern', pattern: 'solid', fgColor: { argb: '1a2332' } };

  const borderThin = {
    top: { style: 'thin', color: { argb: C.dark3 } },
    bottom: { style: 'thin', color: { argb: C.dark3 } },
    left: { style: 'thin', color: { argb: C.dark3 } },
    right: { style: 'thin', color: { argb: C.dark3 } },
  };

  const numFmt = '#,##0';
  const pctFmt = '0.00%';
  const uvtFmt = '#,##0.00';

  // ═══════════════════════════════════════════════
  // HOJA: Tabla Art. 383
  // ═══════════════════════════════════════════════
  const wsT = wb.addWorksheet('Tabla Art.383', { properties: { tabColor: { argb: C.green } } });
  wsT.properties.defaultColWidth = 16;

  // Parámetros generales
  applyDarkBg(wsT, 30, 10);

  wsT.getCell('B2').value = 'PARÁMETROS GENERALES';
  styleTitle(wsT.getCell('B2'), C);
  wsT.mergeCells('B2:E2');

  const params = [
    ['Año gravable', 2026, 'B4', 'C4'],
    ['UVT 2026', 52374, 'B5', 'C5'],
    ['UVT 2025', 49799, 'B6', 'C6'],
    ['UVT aplicable', null, 'B7', 'C7'], // fórmula
    ['SMLMV 2026', 1750905, 'B8', 'C8'],
    ['SMLMV 2025', 1423500, 'B9', 'C9'],
  ];
  params.forEach(([label, val, lc, vc]) => {
    const lCell = wsT.getCell(lc);
    const vCell = wsT.getCell(vc);
    lCell.value = label;
    lCell.font = { ...fontWhite, size: 10 };
    lCell.fill = fillDark;
    if (val !== null) {
      vCell.value = val;
      if (label === 'Año gravable') {
        vCell.fill = fillInput;
        vCell.font = { ...fontGreen, size: 12 };
        vCell.border = { bottom: { style: 'medium', color: { argb: C.yellowBorder } } };
        // Validación: solo 2025 o 2026
        vCell.dataValidation = {
          type: 'list',
          allowBlank: false,
          formulae: ['"2025,2026"'],
        };
      } else {
        vCell.font = { ...fontWhite, size: 10 };
        vCell.numFmt = numFmt;
      }
    }
    vCell.fill = val === null ? fillDark : (label === 'Año gravable' ? fillInput : fillDark);
  });
  // UVT aplicable = SI(C4=2026, C5, C6)
  const uvtCell = wsT.getCell('C7');
  uvtCell.value = { formula: 'IF(C4=2026,C5,C6)' };
  uvtCell.font = { ...fontGreen, size: 12 };
  uvtCell.fill = fillDark;
  uvtCell.numFmt = numFmt;

  // Tabla Art. 383
  wsT.getCell('B11').value = 'TABLA ART. 383 ET — RETENCIÓN EN LA FUENTE';
  styleTitle(wsT.getCell('B11'), C);
  wsT.mergeCells('B11:G11');

  const headers383 = ['Desde (UVT)', 'Hasta (UVT)', 'Tarifa marginal', 'Impuesto base (UVT)', 'Fórmula'];
  const headerRow = 13;
  headers383.forEach((h, i) => {
    const cell = wsT.getCell(headerRow, 2 + i);
    cell.value = h;
    cell.font = { color: { argb: C.dark }, bold: true, size: 9 };
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.green } };
    cell.alignment = { horizontal: 'center' };
    cell.border = borderThin;
  });

  const rangos = [
    [0, 95, '0%', 0, 'Exento'],
    [95, 150, '19%', 0, '(Base UVT - 95) × 19%'],
    [150, 360, '28%', 10.56, '(Base UVT - 150) × 28% + 10.56'],
    [360, 640, '33%', 69.36, '(Base UVT - 360) × 33% + 69.36'],
    [640, 945, '35%', 162, '(Base UVT - 640) × 35% + 162'],
    [945, 2300, '37%', 268.75, '(Base UVT - 945) × 37% + 268.75'],
    [2300, '∞', '39%', 770.35, '(Base UVT - 2300) × 39% + 770.35'],
  ];
  rangos.forEach((r, i) => {
    const row = headerRow + 1 + i;
    [r[0], r[1], r[2], r[3], r[4]].forEach((v, j) => {
      const cell = wsT.getCell(row, 2 + j);
      cell.value = v;
      cell.font = { ...fontWhite, size: 10 };
      cell.fill = i % 2 === 0 ? fillDark : fillDark2;
      cell.border = borderThin;
      cell.alignment = { horizontal: 'center' };
    });
  });

  // Cuantías mínimas
  wsT.getCell('B22').value = 'CUANTÍAS MÍNIMAS DE RETENCIÓN';
  styleTitle(wsT.getCell('B22'), C);
  wsT.mergeCells('B22:F22');

  const cuantias = [
    ['Servicios', '2 UVT', { formula: 'C7*2' }, 'Aplica'],
    ['Honorarios', 'Sin mínima', 0, 'Siempre se retiene'],
    ['Compras', '27 UVT', { formula: 'C7*27' }, 'Aplica'],
    ['Arrendamientos', '27 UVT', { formula: 'C7*27' }, 'Aplica'],
  ];
  const cRow = 24;
  ['Concepto', 'Base mínima', 'Valor $', 'Nota'].forEach((h, i) => {
    const cell = wsT.getCell(cRow, 2 + i);
    cell.value = h;
    cell.font = { color: { argb: C.dark }, bold: true, size: 9 };
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.green } };
    cell.alignment = { horizontal: 'center' };
  });
  cuantias.forEach((r, i) => {
    r.forEach((v, j) => {
      const cell = wsT.getCell(cRow + 1 + i, 2 + j);
      cell.value = v;
      cell.font = { ...fontWhite, size: 10 };
      cell.fill = i % 2 === 0 ? fillDark : fillDark2;
      cell.border = borderThin;
      if (j === 2) cell.numFmt = numFmt;
    });
  });

  // ═══════════════════════════════════════════════
  // HOJA: Asalariado P1
  // ═══════════════════════════════════════════════
  const wsP1 = wb.addWorksheet('Asalariado P1', { properties: { tabColor: { argb: C.blue } } });
  buildAsalariadoSheet(wsP1, 'PROCEDIMIENTO 1', false, wb, C, fillDark, fillDark2, fillDark3, fillInput, fillGreen, fontWhite, fontGreen, fontGray, fontRed, fontOrange, fontBlue, borderThin, numFmt, pctFmt, uvtFmt);

  // ═══════════════════════════════════════════════
  // HOJA: Asalariado P2
  // ═══════════════════════════════════════════════
  const wsP2 = wb.addWorksheet('Asalariado P2', { properties: { tabColor: { argb: C.orange } } });
  buildAsalariadoSheet(wsP2, 'PROCEDIMIENTO 2', true, wb, C, fillDark, fillDark2, fillDark3, fillInput, fillGreen, fontWhite, fontGreen, fontGray, fontRed, fontOrange, fontBlue, borderThin, numFmt, pctFmt, uvtFmt);

  // ═══════════════════════════════════════════════
  // HOJA: Independiente
  // ═══════════════════════════════════════════════
  const wsInd = wb.addWorksheet('Independiente', { properties: { tabColor: { argb: C.orange } } });
  buildIndependienteSheet(wsInd, wb, C, fillDark, fillDark2, fillDark3, fillInput, fillGreen, fontWhite, fontGreen, fontGray, fontRed, fontOrange, fontBlue, borderThin, numFmt, pctFmt, uvtFmt);

  // ═══════════════════════════════════════════════
  // GUARDAR
  // ═══════════════════════════════════════════════
  const outPath = path.join(__dirname, 'Calculadora_Retencion_Fuente_ExogenaDIAN.xlsx');
  await wb.xlsx.writeFile(outPath);
  console.log('✅ Excel generado:', outPath);
}

// ═══════════════════════════════════════════════════════════
// BUILDER: Hoja Asalariado (P1 o P2)
// ═══════════════════════════════════════════════════════════
function buildAsalariadoSheet(ws, titulo, isP2, wb, C, fillDark, fillDark2, fillDark3, fillInput, fillGreen, fontWhite, fontGreen, fontGray, fontRed, fontOrange, fontBlue, borderThin, numFmt, pctFmt, uvtFmt) {
  ws.properties.defaultColWidth = 14;
  ws.getColumn(2).width = 42;
  ws.getColumn(3).width = 20;
  ws.getColumn(4).width = 18;
  ws.getColumn(5).width = 18;
  ws.getColumn(6).width = 22;
  ws.getColumn(7).width = 22;
  applyDarkBg(ws, 75, 8);

  const UVT = "'Tabla Art.383'!C7";

  // ── Título ──
  ws.getCell('B2').value = `RETENCIÓN EN LA FUENTE — ASALARIADOS ${titulo}`;
  styleTitle(ws.getCell('B2'), C);
  ws.mergeCells('B2:F2');

  ws.getCell('B3').value = isP2
    ? 'Arts. 386 y 383 ET — Porcentaje fijo semestral sobre promedio 12 meses'
    : 'Art. 383 ET — Depuración mensual del ingreso laboral';
  ws.getCell('B3').font = { ...fontGray, size: 9, italic: true };
  ws.getCell('B3').fill = fillDark;

  // ── INGRESOS (celdas de entrada) ──
  let row = 5;
  ws.getCell(`B${row}`).value = '▼ INGRESOS DEL MES';
  styleSection(ws.getCell(`B${row}`), C);
  ws.mergeCells(`B${row}:C${row}`);
  row++;

  const inputStyle = (cell, isInput) => {
    cell.fill = isInput ? fillInput : fillDark;
    cell.font = isInput ? { ...fontGreen, size: 11 } : { ...fontWhite, size: 10 };
    cell.numFmt = numFmt;
    cell.border = isInput ? { bottom: { style: 'medium', color: { argb: C.yellowBorder } } } : borderThin;
  };

  const inputRows = [
    ['Salario básico mensual', 'C6', true],
    ['Horas extras y recargos', 'C7', true],
    ['Bonificación salarial', 'C8', true],
    ['Bonificación NO salarial', 'C9', true],
    ['Otros ingresos laborales', 'C10', true],
    ['TOTAL INGRESOS BRUTOS', 'C11', false],
  ];
  inputRows.forEach(([label, ref, isInput], i) => {
    const r = 6 + i;
    const lCell = ws.getCell(`B${r}`);
    const vCell = ws.getCell(`C${r}`);
    lCell.value = label;
    lCell.font = isInput ? { ...fontWhite, size: 10 } : { ...fontGreen, size: 10, bold: true };
    lCell.fill = fillDark;
    if (isInput) {
      vCell.value = 0;
      inputStyle(vCell, true);
    } else {
      vCell.value = { formula: 'SUM(C6:C10)' };
      inputStyle(vCell, false);
      vCell.font = { ...fontGreen, size: 11, bold: true };
    }
  });

  // ── P2: Promedio 12 meses ──
  let depStart = 13;
  if (isP2) {
    row = 13;
    ws.getCell(`B${row}`).value = '▼ PROMEDIO INGRESOS 12 MESES (Procedimiento 2)';
    styleSection(ws.getCell(`B${row}`), C);
    ws.mergeCells(`B${row}:D${row}`);
    row++;

    const meses = ['Mes 1','Mes 2','Mes 3','Mes 4','Mes 5','Mes 6','Mes 7','Mes 8','Mes 9','Mes 10','Mes 11','Mes 12'];
    meses.forEach((m, i) => {
      const r = row + i;
      ws.getCell(`B${r}`).value = m;
      ws.getCell(`B${r}`).font = { ...fontWhite, size: 9 };
      ws.getCell(`B${r}`).fill = fillDark;
      ws.getCell(`C${r}`).value = 0;
      inputStyle(ws.getCell(`C${r}`), true);
    });
    const promRow = row + 12;
    ws.getCell(`B${promRow}`).value = 'PROMEDIO 12 MESES';
    ws.getCell(`B${promRow}`).font = { ...fontGreen, size: 10, bold: true };
    ws.getCell(`B${promRow}`).fill = fillDark;
    ws.getCell(`C${promRow}`).value = { formula: `AVERAGE(C${row}:C${row + 11})` };
    ws.getCell(`C${promRow}`).font = { ...fontGreen, size: 11, bold: true };
    ws.getCell(`C${promRow}`).fill = fillDark;
    ws.getCell(`C${promRow}`).numFmt = numFmt;

    ws.getCell(`B${promRow + 1}`).value = '💡 En P2 la retención se calcula sobre este promedio, no sobre el ingreso del mes';
    ws.getCell(`B${promRow + 1}`).font = { ...fontOrange, size: 8, italic: true };
    ws.getCell(`B${promRow + 1}`).fill = fillDark;
    ws.mergeCells(`B${promRow + 1}:E${promRow + 1}`);

    depStart = promRow + 3;
  }

  // ── DEPURACIÓN ──
  row = depStart;
  ws.getCell(`B${row}`).value = '▼ DEPURACIÓN DE LA BASE GRAVABLE';
  styleSection(ws.getCell(`B${row}`), C);
  ws.mergeCells(`B${row}:D${row}`);
  row++;

  // Headers depuración
  ['Concepto', 'Valor $', 'En UVT', 'Norma'].forEach((h, i) => {
    const cell = ws.getCell(row, 2 + i);
    cell.value = h;
    cell.font = { color: { argb: C.dark }, bold: true, size: 9 };
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.green } };
    cell.alignment = { horizontal: 'center' };
    cell.border = borderThin;
  });
  row++;

  const ingresoRef = isP2 ? `C${depStart - 3}` : 'C11'; // promedio o total

  // Ingreso base
  const depLines = [];
  const addDep = (label, formula, uvtFormula, norma, isNeg, isBold) => {
    depLines.push({ label, formula, uvtFormula, norma, isNeg, isBold, row });
    const lCell = ws.getCell(`B${row}`);
    const vCell = ws.getCell(`C${row}`);
    const uCell = ws.getCell(`D${row}`);
    const nCell = ws.getCell(`E${row}`);
    lCell.value = (isNeg ? '(−) ' : '') + label;
    lCell.font = { ...fontWhite, size: 10, bold: !!isBold };
    if (isNeg) lCell.font = { ...fontRed, size: 10 };
    if (isBold) lCell.font = { ...fontGreen, size: 10, bold: true };
    lCell.fill = fillDark;
    vCell.value = { formula };
    vCell.font = isBold ? { ...fontGreen, size: 11, bold: true } : (isNeg ? { ...fontRed, size: 10 } : { ...fontWhite, size: 10 });
    vCell.fill = fillDark;
    vCell.numFmt = numFmt;
    vCell.border = borderThin;
    uCell.value = { formula: uvtFormula };
    uCell.font = { ...fontGray, size: 9 };
    uCell.fill = fillDark;
    uCell.numFmt = uvtFmt;
    uCell.border = borderThin;
    nCell.value = norma;
    nCell.font = { ...fontGray, size: 8 };
    nCell.fill = fillDark;
    nCell.border = borderThin;
    row++;
  };

  const r0 = row; // fila del ingreso base
  addDep('Ingreso bruto laboral', `+${ingresoRef}`, `C${row}/${UVT}`, '', false, false);

  const rSalud = row;
  addDep('Aporte obligatorio salud (4%)', `ROUND(${ingresoRef}*0.04,0)`, `C${row}/${UVT}`, 'Art. 56 ET', true, false);

  const rPension = row;
  addDep('Aporte obligatorio pensión (4%)', `ROUND(${ingresoRef}*0.04,0)`, `C${row}/${UVT}`, 'Art. 55 ET', true, false);

  const rFSP = row;
  // FSP: si salario > 4 SMLMV = 1% adicional. Simplificado.
  addDep('Fondo Solidaridad Pensional', `IF(${ingresoRef}>('Tabla Art.383'!C8*4),ROUND(${ingresoRef}*0.01,0),0)`, `C${row}/${UVT}`, 'Art. 27 L.100/93', true, false);

  const rSub1 = row;
  addDep('Subtotal 1 (después de aportes)', `C${r0}-C${rSalud}-C${rPension}-C${rFSP}`, `C${row}/${UVT}`, '', false, true);

  // ── DEDUCCIONES OPCIONALES ──
  row++;
  ws.getCell(`B${row}`).value = '▼ DEDUCCIONES Y RENTAS EXENTAS (ingrese valores)';
  styleSection(ws.getCell(`B${row}`), C);
  ws.mergeCells(`B${row}:E${row}`);
  row++;

  const dedStart = row;

  // Dependientes
  const rDep = row;
  ws.getCell(`B${row}`).value = '(−) Dependientes (10% ingreso, máx 32 UVT/mes)';
  ws.getCell(`B${row}`).font = { ...fontRed, size: 9 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = 0; // # dependientes (0, 1 o 2)
  ws.getCell(`C${row}`).fill = fillInput;
  ws.getCell(`C${row}`).font = { ...fontGreen, size: 10 };
  ws.getCell(`C${row}`).border = { bottom: { style: 'medium', color: { argb: C.yellowBorder } } };
  ws.getCell(`C${row}`).dataValidation = { type: 'list', allowBlank: false, formulae: ['"0,1,2"'] };
  ws.getCell(`D${row}`).value = { formula: `IF(C${row}>0,MIN(ROUND(${ingresoRef}*0.1,0),ROUND(32*${UVT},0))*MIN(C${row},2),0)` };
  ws.getCell(`D${row}`).font = { ...fontRed, size: 10 };
  ws.getCell(`D${row}`).fill = fillDark;
  ws.getCell(`D${row}`).numFmt = numFmt;
  ws.getCell(`E${row}`).value = 'Art. 387 ET';
  ws.getCell(`E${row}`).font = { ...fontGray, size: 8 };
  ws.getCell(`E${row}`).fill = fillDark;
  row++;

  // Intereses vivienda
  const rViv = row;
  ws.getCell(`B${row}`).value = '(−) Intereses crédito vivienda (máx 100 UVT/mes)';
  ws.getCell(`B${row}`).font = { ...fontRed, size: 9 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = 0;
  inputStyle(ws.getCell(`C${row}`), true);
  ws.getCell(`D${row}`).value = { formula: `MIN(C${row},ROUND(100*${UVT},0))` };
  ws.getCell(`D${row}`).font = { ...fontRed, size: 10 };
  ws.getCell(`D${row}`).fill = fillDark;
  ws.getCell(`D${row}`).numFmt = numFmt;
  ws.getCell(`E${row}`).value = 'Art. 119 ET';
  ws.getCell(`E${row}`).font = { ...fontGray, size: 8 };
  ws.getCell(`E${row}`).fill = fillDark;
  row++;

  // Medicina prepagada
  const rMed = row;
  ws.getCell(`B${row}`).value = '(−) Medicina prepagada (máx 16 UVT/mes)';
  ws.getCell(`B${row}`).font = { ...fontRed, size: 9 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = 0;
  inputStyle(ws.getCell(`C${row}`), true);
  ws.getCell(`D${row}`).value = { formula: `MIN(C${row},ROUND(16*${UVT},0))` };
  ws.getCell(`D${row}`).font = { ...fontRed, size: 10 };
  ws.getCell(`D${row}`).fill = fillDark;
  ws.getCell(`D${row}`).numFmt = numFmt;
  ws.getCell(`E${row}`).value = 'Art. 387 ET';
  ws.getCell(`E${row}`).font = { ...fontGray, size: 8 };
  ws.getCell(`E${row}`).fill = fillDark;
  row++;

  // Aportes voluntarios pensión
  const rVolPen = row;
  ws.getCell(`B${row}`).value = '(−) Aportes voluntarios pensión AFP (máx 25% ingreso)';
  ws.getCell(`B${row}`).font = { ...fontRed, size: 9 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = 0;
  inputStyle(ws.getCell(`C${row}`), true);
  ws.getCell(`D${row}`).value = { formula: `MIN(C${row},ROUND(${ingresoRef}*0.25,0),ROUND(3800*${UVT}/12,0))` };
  ws.getCell(`D${row}`).font = { ...fontRed, size: 10 };
  ws.getCell(`D${row}`).fill = fillDark;
  ws.getCell(`D${row}`).numFmt = numFmt;
  ws.getCell(`E${row}`).value = 'Art. 126-1 ET';
  ws.getCell(`E${row}`).font = { ...fontGray, size: 8 };
  ws.getCell(`E${row}`).fill = fillDark;
  row++;

  // AFC
  const rAFC = row;
  ws.getCell(`B${row}`).value = '(−) Aportes AFC / ahorro vivienda';
  ws.getCell(`B${row}`).font = { ...fontRed, size: 9 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = 0;
  inputStyle(ws.getCell(`C${row}`), true);
  // Límite conjunto con vol. pensión: 30% ingreso bruto, máx 3800 UVT/año
  ws.getCell(`D${row}`).value = { formula: `MIN(C${row},MAX(ROUND(${ingresoRef}*0.3,0)-D${rVolPen},0),ROUND(3800*${UVT}/12,0)-D${rVolPen})` };
  ws.getCell(`D${row}`).font = { ...fontRed, size: 10 };
  ws.getCell(`D${row}`).fill = fillDark;
  ws.getCell(`D${row}`).numFmt = numFmt;
  ws.getCell(`E${row}`).value = 'Art. 126-4 ET';
  ws.getCell(`E${row}`).font = { ...fontGray, size: 8 };
  ws.getCell(`E${row}`).fill = fillDark;
  row++;

  // Total deducciones
  const rTotDed = row;
  ws.getCell(`B${row}`).value = 'Total deducciones';
  ws.getCell(`B${row}`).font = { ...fontRed, size: 10, bold: true };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`D${row}`).value = { formula: `D${rDep}+D${rViv}+D${rMed}+D${rVolPen}+D${rAFC}` };
  ws.getCell(`D${row}`).font = { ...fontRed, size: 10, bold: true };
  ws.getCell(`D${row}`).fill = fillDark;
  ws.getCell(`D${row}`).numFmt = numFmt;
  row++;

  // Subtotal 2
  const rSub2 = row;
  ws.getCell(`B${row}`).value = 'Subtotal 2 (después de deducciones)';
  ws.getCell(`B${row}`).font = { ...fontGreen, size: 10, bold: true };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = { formula: `MAX(C${rSub1}-D${rTotDed},0)` };
  ws.getCell(`C${row}`).font = { ...fontGreen, size: 11, bold: true };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.getCell(`C${row}`).numFmt = numFmt;
  row++;

  // Renta exenta 25%
  const rExenta = row;
  ws.getCell(`B${row}`).value = '(−) Renta exenta 25% (máx 240 UVT/mes)';
  ws.getCell(`B${row}`).font = { ...fontRed, size: 10 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = { formula: `MIN(ROUND(C${rSub2}*0.25,0),ROUND(240*${UVT},0))` };
  ws.getCell(`C${row}`).font = { ...fontRed, size: 10 };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.getCell(`C${row}`).numFmt = numFmt;
  ws.getCell(`E${row}`).value = 'Art. 206 num.10 ET';
  ws.getCell(`E${row}`).font = { ...fontGray, size: 8 };
  ws.getCell(`E${row}`).fill = fillDark;
  row++;

  // ── BASE GRAVABLE ──
  row++;
  const rBase = row;
  ws.getCell(`B${row}`).value = '★ BASE GRAVABLE';
  ws.getCell(`B${row}`).font = { color: { argb: C.dark }, bold: true, size: 11 };
  ws.getCell(`B${row}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.green } };
  ws.getCell(`C${row}`).value = { formula: `MAX(C${rSub2}-C${rExenta},0)` };
  ws.getCell(`C${row}`).font = { color: { argb: C.dark }, bold: true, size: 12 };
  ws.getCell(`C${row}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.green } };
  ws.getCell(`C${row}`).numFmt = numFmt;
  ws.getCell(`D${row}`).value = { formula: `ROUND(C${row}/${UVT},2)` };
  ws.getCell(`D${row}`).font = { color: { argb: C.dark }, bold: true, size: 10 };
  ws.getCell(`D${row}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.green } };
  ws.getCell(`D${row}`).numFmt = uvtFmt;
  ws.getCell(`E${row}`).value = 'UVT';
  ws.getCell(`E${row}`).font = { color: { argb: C.dark }, bold: true, size: 10 };
  ws.getCell(`E${row}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.green } };
  row += 2;

  // ── CÁLCULO RETENCIÓN (fórmula Art. 383) ──
  const rRet = row;
  ws.getCell(`B${row}`).value = '▼ CÁLCULO DE LA RETENCIÓN';
  styleSection(ws.getCell(`B${row}`), C);
  ws.mergeCells(`B${row}:D${row}`);
  row++;

  const baseUVT = `D${rBase}`;

  ws.getCell(`B${row}`).value = 'Retención en UVT';
  ws.getCell(`B${row}`).font = { ...fontWhite, size: 10 };
  ws.getCell(`B${row}`).fill = fillDark;
  // Nested IF for Art. 383 table
  const retFormula = `IF(${baseUVT}<=95,0,IF(${baseUVT}<=150,(${baseUVT}-95)*0.19,IF(${baseUVT}<=360,(${baseUVT}-150)*0.28+10.56,IF(${baseUVT}<=640,(${baseUVT}-360)*0.33+69.36,IF(${baseUVT}<=945,(${baseUVT}-640)*0.35+162,IF(${baseUVT}<=2300,(${baseUVT}-945)*0.37+268.75,(${baseUVT}-2300)*0.39+770.35))))))`;
  ws.getCell(`C${row}`).value = { formula: retFormula };
  ws.getCell(`C${row}`).font = { ...fontWhite, size: 10 };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.getCell(`C${row}`).numFmt = uvtFmt;
  ws.getCell(`D${row}`).value = 'UVT';
  ws.getCell(`D${row}`).font = { ...fontGray, size: 9 };
  ws.getCell(`D${row}`).fill = fillDark;
  const rRetUVT = row;
  row++;

  ws.getCell(`B${row}`).value = '★ RETENCIÓN DEL MES';
  ws.getCell(`B${row}`).font = { color: { argb: C.dark }, bold: true, size: 11 };
  ws.getCell(`B${row}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.green } };
  ws.getCell(`C${row}`).value = { formula: `ROUND(C${rRetUVT}*${UVT},0)` };
  ws.getCell(`C${row}`).font = { color: { argb: C.dark }, bold: true, size: 13 };
  ws.getCell(`C${row}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.green } };
  ws.getCell(`C${row}`).numFmt = numFmt;
  const rRetCOP = row;
  row++;

  // Tasa efectiva
  ws.getCell(`B${row}`).value = 'Tasa efectiva de retención';
  ws.getCell(`B${row}`).font = { ...fontWhite, size: 10 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = { formula: `IF(${ingresoRef}=0,0,C${rRetCOP}/${ingresoRef})` };
  ws.getCell(`C${row}`).font = { ...fontBlue, size: 11, bold: true };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.getCell(`C${row}`).numFmt = pctFmt;
  row += 2;

  // ── SUGERENCIAS DE OPTIMIZACIÓN ──
  buildSugerencias(ws, row, rRetCOP, ingresoRef, rDep, rViv, rMed, rVolPen, rAFC, UVT, C, fillDark, fillDark2, fillDark3, fontWhite, fontGreen, fontGray, fontOrange, fontBlue, borderThin, numFmt, retFormula, baseUVT, rBase, rSub2, rExenta, rTotDed, rSub1);
}

// ═══════════════════════════════════════════════════════════
// BUILDER: Hoja Independiente
// ═══════════════════════════════════════════════════════════
function buildIndependienteSheet(ws, wb, C, fillDark, fillDark2, fillDark3, fillInput, fillGreen, fontWhite, fontGreen, fontGray, fontRed, fontOrange, fontBlue, borderThin, numFmt, pctFmt, uvtFmt) {
  ws.properties.defaultColWidth = 14;
  ws.getColumn(2).width = 44;
  ws.getColumn(3).width = 20;
  ws.getColumn(4).width = 18;
  ws.getColumn(5).width = 18;
  ws.getColumn(6).width = 22;
  applyDarkBg(ws, 60, 8);

  const UVT = "'Tabla Art.383'!C7";

  ws.getCell('B2').value = 'RETENCIÓN EN LA FUENTE — INDEPENDIENTE / CONTRATISTA';
  styleTitle(ws.getCell('B2'), C);
  ws.mergeCells('B2:F2');
  ws.getCell('B3').value = 'Art. 383 ET + Decreto 0572/2025 — Depuración sobre honorarios, servicios o comisiones';
  ws.getCell('B3').font = { ...fontGray, size: 9, italic: true };
  ws.getCell('B3').fill = fillDark;

  let row = 5;
  ws.getCell(`B${row}`).value = '▼ DATOS DEL CONTRATO';
  styleSection(ws.getCell(`B${row}`), C);
  ws.mergeCells(`B${row}:C${row}`);
  row++;

  // Tipo de ingreso
  ws.getCell(`B${row}`).value = 'Tipo de ingreso';
  ws.getCell(`B${row}`).font = { ...fontWhite, size: 10 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = 'Honorarios';
  ws.getCell(`C${row}`).fill = fillInput;
  ws.getCell(`C${row}`).font = { ...fontGreen, size: 10 };
  ws.getCell(`C${row}`).dataValidation = { type: 'list', allowBlank: false, formulae: ['"Honorarios,Servicios,Comisiones"'] };
  const rTipo = row;
  row++;

  // Declarante
  ws.getCell(`B${row}`).value = '¿Es declarante de renta?';
  ws.getCell(`B${row}`).font = { ...fontWhite, size: 10 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = 'Sí';
  ws.getCell(`C${row}`).fill = fillInput;
  ws.getCell(`C${row}`).font = { ...fontGreen, size: 10 };
  ws.getCell(`C${row}`).dataValidation = { type: 'list', allowBlank: false, formulae: ['"Sí,No"'] };
  const rDecl = row;
  row++;

  // Ingreso bruto
  ws.getCell(`B${row}`).value = 'Ingreso bruto del contrato (pago mensual)';
  ws.getCell(`B${row}`).font = { ...fontWhite, size: 10 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = 0;
  ws.getCell(`C${row}`).fill = fillInput;
  ws.getCell(`C${row}`).font = { ...fontGreen, size: 11 };
  ws.getCell(`C${row}`).numFmt = numFmt;
  ws.getCell(`C${row}`).border = { bottom: { style: 'medium', color: { argb: C.yellowBorder } } };
  const rIng = row;
  row += 2;

  // ── Tarifas fijas Art. 392 (comparativo) ──
  ws.getCell(`B${row}`).value = '▼ TARIFA FIJA ART. 392 (comparativo rápido)';
  styleSection(ws.getCell(`B${row}`), C);
  ws.mergeCells(`B${row}:D${row}`);
  row++;

  ws.getCell(`B${row}`).value = 'Honorarios declarante: 10%';
  ws.getCell(`B${row}`).font = { ...fontWhite, size: 9 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = { formula: `IF(C${rTipo}="Honorarios",IF(C${rDecl}="Sí",ROUND(C${rIng}*0.1,0),ROUND(C${rIng}*0.11,0)),IF(C${rDecl}="Sí",ROUND(C${rIng}*0.04,0),ROUND(C${rIng}*0.06,0)))` };
  ws.getCell(`C${row}`).font = { ...fontOrange, size: 10 };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.getCell(`C${row}`).numFmt = numFmt;
  ws.getCell(`D${row}`).value = '← Tarifa fija sin depuración';
  ws.getCell(`D${row}`).font = { ...fontGray, size: 8 };
  ws.getCell(`D${row}`).fill = fillDark;
  const rFija = row;
  row += 2;

  // ── DEPURACIÓN ──
  ws.getCell(`B${row}`).value = '▼ DEPURACIÓN CON TABLA ART. 383';
  styleSection(ws.getCell(`B${row}`), C);
  ws.mergeCells(`B${row}:D${row}`);
  row++;

  ['Concepto', 'Valor $', 'Norma'].forEach((h, i) => {
    const cell = ws.getCell(row, 2 + i);
    cell.value = h;
    cell.font = { color: { argb: C.dark }, bold: true, size: 9 };
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.green } };
    cell.alignment = { horizontal: 'center' };
  });
  row++;

  const r0 = row;
  // Ingreso
  ws.getCell(`B${row}`).value = 'Ingreso bruto';
  ws.getCell(`B${row}`).font = { ...fontWhite, size: 10 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = { formula: `+C${rIng}` };
  ws.getCell(`C${row}`).font = { ...fontWhite, size: 10 };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.getCell(`C${row}`).numFmt = numFmt;
  row++;

  // Base cotización = 40% del ingreso
  const rBaseCot = row;
  ws.getCell(`B${row}`).value = 'Base cotización SS (40% del ingreso)';
  ws.getCell(`B${row}`).font = { ...fontGray, size: 9 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = { formula: `ROUND(C${rIng}*0.4,0)` };
  ws.getCell(`C${row}`).font = { ...fontGray, size: 9 };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.getCell(`C${row}`).numFmt = numFmt;
  ws.getCell(`D${row}`).value = 'Dec. 0572/2025';
  ws.getCell(`D${row}`).font = { ...fontGray, size: 8 };
  ws.getCell(`D${row}`).fill = fillDark;
  row++;

  // Salud 12.5%
  const rSalud = row;
  ws.getCell(`B${row}`).value = '(−) Aporte salud (12.5% sobre 40%)';
  ws.getCell(`B${row}`).font = { ...fontRed, size: 10 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = { formula: `ROUND(C${rBaseCot}*0.125,0)` };
  ws.getCell(`C${row}`).font = { ...fontRed, size: 10 };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.getCell(`C${row}`).numFmt = numFmt;
  row++;

  // Pensión 16%
  const rPen = row;
  ws.getCell(`B${row}`).value = '(−) Aporte pensión (16% sobre 40%)';
  ws.getCell(`B${row}`).font = { ...fontRed, size: 10 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = { formula: `ROUND(C${rBaseCot}*0.16,0)` };
  ws.getCell(`C${row}`).font = { ...fontRed, size: 10 };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.getCell(`C${row}`).numFmt = numFmt;
  row++;

  // Subtotal
  const rSub1 = row;
  ws.getCell(`B${row}`).value = 'Subtotal (ingreso - aportes SS)';
  ws.getCell(`B${row}`).font = { ...fontGreen, size: 10, bold: true };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = { formula: `C${r0}-C${rSalud}-C${rPen}` };
  ws.getCell(`C${row}`).font = { ...fontGreen, size: 11, bold: true };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.getCell(`C${row}`).numFmt = numFmt;
  row++;

  // Deducciones opcionales
  const rVolPen = row;
  ws.getCell(`B${row}`).value = '(−) Aportes voluntarios pensión AFP';
  ws.getCell(`B${row}`).font = { ...fontRed, size: 9 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = 0;
  ws.getCell(`C${row}`).fill = fillInput;
  ws.getCell(`C${row}`).font = { ...fontGreen, size: 10 };
  ws.getCell(`C${row}`).numFmt = numFmt;
  ws.getCell(`C${row}`).border = { bottom: { style: 'medium', color: { argb: C.yellowBorder } } };
  ws.getCell(`D${row}`).value = 'Art. 126-1 ET';
  ws.getCell(`D${row}`).font = { ...fontGray, size: 8 };
  ws.getCell(`D${row}`).fill = fillDark;
  row++;

  const rAFC = row;
  ws.getCell(`B${row}`).value = '(−) Aportes AFC / ahorro vivienda';
  ws.getCell(`B${row}`).font = { ...fontRed, size: 9 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = 0;
  ws.getCell(`C${row}`).fill = fillInput;
  ws.getCell(`C${row}`).font = { ...fontGreen, size: 10 };
  ws.getCell(`C${row}`).numFmt = numFmt;
  ws.getCell(`C${row}`).border = { bottom: { style: 'medium', color: { argb: C.yellowBorder } } };
  ws.getCell(`D${row}`).value = 'Art. 126-4 ET';
  ws.getCell(`D${row}`).font = { ...fontGray, size: 8 };
  ws.getCell(`D${row}`).fill = fillDark;
  row++;

  const rViv = row;
  ws.getCell(`B${row}`).value = '(−) Intereses crédito vivienda (máx 100 UVT)';
  ws.getCell(`B${row}`).font = { ...fontRed, size: 9 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = 0;
  ws.getCell(`C${row}`).fill = fillInput;
  ws.getCell(`C${row}`).font = { ...fontGreen, size: 10 };
  ws.getCell(`C${row}`).numFmt = numFmt;
  ws.getCell(`C${row}`).border = { bottom: { style: 'medium', color: { argb: C.yellowBorder } } };
  ws.getCell(`D${row}`).value = 'Art. 119 ET';
  ws.getCell(`D${row}`).font = { ...fontGray, size: 8 };
  ws.getCell(`D${row}`).fill = fillDark;
  row++;

  // Total deducciones
  const rTotDed = row;
  ws.getCell(`B${row}`).value = 'Total deducciones';
  ws.getCell(`B${row}`).font = { ...fontRed, size: 10, bold: true };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = { formula: `MIN(C${rVolPen},ROUND(C${rIng}*0.25,0),ROUND(3800*${UVT}/12,0))+MIN(C${rAFC},MAX(ROUND(C${rIng}*0.3,0)-MIN(C${rVolPen},ROUND(C${rIng}*0.25,0)),0))+MIN(C${rViv},ROUND(100*${UVT},0))` };
  ws.getCell(`C${row}`).font = { ...fontRed, size: 10, bold: true };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.getCell(`C${row}`).numFmt = numFmt;
  row++;

  // Subtotal 2
  const rSub2 = row;
  ws.getCell(`B${row}`).value = 'Subtotal 2 (después deducciones)';
  ws.getCell(`B${row}`).font = { ...fontGreen, size: 10, bold: true };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = { formula: `MAX(C${rSub1}-C${rTotDed},0)` };
  ws.getCell(`C${row}`).font = { ...fontGreen, size: 11, bold: true };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.getCell(`C${row}`).numFmt = numFmt;
  row++;

  // Renta exenta 25%
  const rExenta = row;
  ws.getCell(`B${row}`).value = '(−) Renta exenta 25% (máx 240 UVT/mes)';
  ws.getCell(`B${row}`).font = { ...fontRed, size: 10 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = { formula: `MIN(ROUND(C${rSub2}*0.25,0),ROUND(240*${UVT},0))` };
  ws.getCell(`C${row}`).font = { ...fontRed, size: 10 };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.getCell(`C${row}`).numFmt = numFmt;
  ws.getCell(`D${row}`).value = 'Art. 206 num.10 ET';
  ws.getCell(`D${row}`).font = { ...fontGray, size: 8 };
  ws.getCell(`D${row}`).fill = fillDark;
  row++;

  // BASE GRAVABLE
  row++;
  const rBase = row;
  ws.getCell(`B${row}`).value = '★ BASE GRAVABLE';
  ws.getCell(`B${row}`).font = { color: { argb: C.dark }, bold: true, size: 11 };
  ws.getCell(`B${row}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.green } };
  ws.getCell(`C${row}`).value = { formula: `MAX(C${rSub2}-C${rExenta},0)` };
  ws.getCell(`C${row}`).font = { color: { argb: C.dark }, bold: true, size: 12 };
  ws.getCell(`C${row}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.green } };
  ws.getCell(`C${row}`).numFmt = numFmt;
  ws.getCell(`D${row}`).value = { formula: `ROUND(C${row}/${UVT},2)` };
  ws.getCell(`D${row}`).font = { color: { argb: C.dark }, bold: true, size: 10 };
  ws.getCell(`D${row}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.green } };
  ws.getCell(`D${row}`).numFmt = uvtFmt;
  row += 2;

  // RETENCIÓN
  const baseUVT = `D${rBase}`;
  const retFormula = `IF(${baseUVT}<=95,0,IF(${baseUVT}<=150,(${baseUVT}-95)*0.19,IF(${baseUVT}<=360,(${baseUVT}-150)*0.28+10.56,IF(${baseUVT}<=640,(${baseUVT}-360)*0.33+69.36,IF(${baseUVT}<=945,(${baseUVT}-640)*0.35+162,IF(${baseUVT}<=2300,(${baseUVT}-945)*0.37+268.75,(${baseUVT}-2300)*0.39+770.35))))))`;

  ws.getCell(`B${row}`).value = 'Retención en UVT (tabla Art. 383)';
  ws.getCell(`B${row}`).font = { ...fontWhite, size: 10 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = { formula: retFormula };
  ws.getCell(`C${row}`).font = { ...fontWhite, size: 10 };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.getCell(`C${row}`).numFmt = uvtFmt;
  const rRetUVT = row;
  row++;

  ws.getCell(`B${row}`).value = '★ RETENCIÓN CON DEPURACIÓN';
  ws.getCell(`B${row}`).font = { color: { argb: C.dark }, bold: true, size: 11 };
  ws.getCell(`B${row}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.green } };
  ws.getCell(`C${row}`).value = { formula: `ROUND(C${rRetUVT}*${UVT},0)` };
  ws.getCell(`C${row}`).font = { color: { argb: C.dark }, bold: true, size: 13 };
  ws.getCell(`C${row}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.green } };
  ws.getCell(`C${row}`).numFmt = numFmt;
  const rRetCOP = row;
  row++;

  // Tasa efectiva
  ws.getCell(`B${row}`).value = 'Tasa efectiva de retención';
  ws.getCell(`B${row}`).font = { ...fontWhite, size: 10 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = { formula: `IF(C${rIng}=0,0,C${rRetCOP}/C${rIng})` };
  ws.getCell(`C${row}`).font = { ...fontBlue, size: 11, bold: true };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.getCell(`C${row}`).numFmt = pctFmt;
  row++;

  // Cuantía mínima
  ws.getCell(`B${row}`).value = '⚠ Cuantía mínima servicios: 2 UVT';
  ws.getCell(`B${row}`).font = { ...fontOrange, size: 9 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = { formula: `IF(C${rTipo}="Servicios",IF(C${rIng}<2*${UVT},"NO aplica retención (< cuantía mínima)","Sí aplica"),"Honorarios: sin cuantía mínima")` };
  ws.getCell(`C${row}`).font = { ...fontOrange, size: 9 };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.mergeCells(`C${row}:E${row}`);
  row += 2;

  // Comparativo vs tarifa fija
  ws.getCell(`B${row}`).value = '▼ COMPARATIVO: Depuración vs Tarifa Fija';
  styleSection(ws.getCell(`B${row}`), C);
  ws.mergeCells(`B${row}:D${row}`);
  row++;

  ws.getCell(`B${row}`).value = 'Retención con depuración (Art. 383)';
  ws.getCell(`B${row}`).font = { ...fontGreen, size: 10 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = { formula: `C${rRetCOP}` };
  ws.getCell(`C${row}`).font = { ...fontGreen, size: 11, bold: true };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.getCell(`C${row}`).numFmt = numFmt;
  row++;

  ws.getCell(`B${row}`).value = 'Retención con tarifa fija (Art. 392)';
  ws.getCell(`B${row}`).font = { ...fontOrange, size: 10 };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = { formula: `C${rFija}` };
  ws.getCell(`C${row}`).font = { ...fontOrange, size: 11, bold: true };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.getCell(`C${row}`).numFmt = numFmt;
  row++;

  ws.getCell(`B${row}`).value = '💰 AHORRO con depuración';
  ws.getCell(`B${row}`).font = { ...fontGreen, size: 10, bold: true };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.getCell(`C${row}`).value = { formula: `C${rFija}-C${rRetCOP}` };
  ws.getCell(`C${row}`).font = { ...fontGreen, size: 12, bold: true };
  ws.getCell(`C${row}`).fill = fillDark;
  ws.getCell(`C${row}`).numFmt = numFmt;
  row++;

  ws.getCell(`B${row}`).value = { formula: `IF(C${rFija}>C${rRetCOP},"✅ Te conviene la depuración Art. 383","⚠ La tarifa fija te sale más barata")` };
  ws.getCell(`B${row}`).font = { ...fontOrange, size: 10, bold: true };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.mergeCells(`B${row}:E${row}`);
}

// ═══════════════════════════════════════════════════════════
// SUGERENCIAS DE OPTIMIZACIÓN
// ═══════════════════════════════════════════════════════════
function buildSugerencias(ws, row, rRetCOP, ingresoRef, rDep, rViv, rMed, rVolPen, rAFC, UVT, C, fillDark, fillDark2, fillDark3, fontWhite, fontGreen, fontGray, fontOrange, fontBlue, borderThin, numFmt, retFormula, baseUVT, rBase, rSub2, rExenta, rTotDed, rSub1) {
  ws.getCell(`B${row}`).value = '▼ SUGERENCIAS PARA REDUCIR TU RETENCIÓN';
  styleSection(ws.getCell(`B${row}`), C);
  ws.mergeCells(`B${row}:F${row}`);
  row++;

  ws.getCell(`B${row}`).value = 'Cada sugerencia muestra cuánto ahorrarías SI la aplicaras al máximo permitido:';
  ws.getCell(`B${row}`).font = { ...fontGray, size: 9, italic: true };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.mergeCells(`B${row}:F${row}`);
  row++;

  const sugs = [
    {
      titulo: '1. Aportes voluntarios pensión AFP',
      norma: 'Art. 126-1 ET',
      desc: 'Hasta 25% del ingreso, máx 3.800 UVT/año',
      maxFormula: `MIN(ROUND(${ingresoRef}*0.25,0),ROUND(3800*${UVT}/12,0))`,
    },
    {
      titulo: '2. Aportes AFC / ahorro para vivienda',
      norma: 'Art. 126-4 ET',
      desc: 'Conjunto con pensión vol.: 30% ingreso, máx 3.800 UVT/año',
      maxFormula: `ROUND(${ingresoRef}*0.3,0)`,
    },
    {
      titulo: '3. Intereses crédito de vivienda',
      norma: 'Art. 119 ET',
      desc: 'Hasta 100 UVT/mes. Requiere certificado bancario.',
      maxFormula: `ROUND(100*${UVT},0)`,
    },
    {
      titulo: '4. Dependientes económicos (2 máx)',
      norma: 'Art. 387 ET',
      desc: '10% ingreso bruto, máx 32 UVT/mes × dependiente.',
      maxFormula: `MIN(ROUND(${ingresoRef}*0.1,0),ROUND(32*${UVT},0))*2`,
    },
    {
      titulo: '5. Medicina prepagada / seguros salud',
      norma: 'Art. 387 ET',
      desc: 'Hasta 16 UVT/mes. Solo asalariados.',
      maxFormula: `ROUND(16*${UVT},0)`,
    },
  ];

  ['Sugerencia', 'Máximo deducible', 'Ya aplicado', 'Norma'].forEach((h, i) => {
    const cell = ws.getCell(row, 2 + i);
    cell.value = h;
    cell.font = { color: { argb: C.dark }, bold: true, size: 9 };
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.green } };
    cell.alignment = { horizontal: 'center' };
    cell.border = borderThin;
  });
  row++;

  sugs.forEach((s, i) => {
    const r = row + i;
    ws.getCell(`B${r}`).value = s.titulo;
    ws.getCell(`B${r}`).font = { ...fontWhite, size: 9 };
    ws.getCell(`B${r}`).fill = i % 2 === 0 ? fillDark : fillDark2;
    ws.getCell(`B${r}`).border = borderThin;

    ws.getCell(`C${r}`).value = { formula: s.maxFormula };
    ws.getCell(`C${r}`).font = { ...fontBlue, size: 10 };
    ws.getCell(`C${r}`).fill = i % 2 === 0 ? fillDark : fillDark2;
    ws.getCell(`C${r}`).numFmt = numFmt;
    ws.getCell(`C${r}`).border = borderThin;

    // Ya aplicado — referencia a las celdas de deducción
    let yaRef = '0';
    if (i === 0) yaRef = `D${rVolPen}`;
    if (i === 1) yaRef = `D${rAFC}`;
    if (i === 2) yaRef = `D${rViv}`;
    if (i === 3) yaRef = `D${rDep}`;
    if (i === 4) yaRef = `D${rMed}`;
    ws.getCell(`D${r}`).value = { formula: yaRef };
    ws.getCell(`D${r}`).font = { ...fontOrange, size: 10 };
    ws.getCell(`D${r}`).fill = i % 2 === 0 ? fillDark : fillDark2;
    ws.getCell(`D${r}`).numFmt = numFmt;
    ws.getCell(`D${r}`).border = borderThin;

    ws.getCell(`E${r}`).value = s.norma;
    ws.getCell(`E${r}`).font = { ...fontGray, size: 8 };
    ws.getCell(`E${r}`).fill = i % 2 === 0 ? fillDark : fillDark2;
    ws.getCell(`E${r}`).border = borderThin;
  });
  row += sugs.length + 1;

  // Nota final
  ws.getCell(`B${row}`).value = '💡 Las celdas amarillas son editables. Modifica los valores y la retención se recalcula automáticamente.';
  ws.getCell(`B${row}`).font = { ...fontOrange, size: 9, italic: true };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.mergeCells(`B${row}:F${row}`);
  row++;
  ws.getCell(`B${row}`).value = '⚠ Este archivo es orientativo. Consulte siempre con su contador o asesor tributario. ExógenaDIAN.com';
  ws.getCell(`B${row}`).font = { ...fontGray, size: 8, italic: true };
  ws.getCell(`B${row}`).fill = fillDark;
  ws.mergeCells(`B${row}:F${row}`);
}

// ═══════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════
function applyDarkBg(ws, rows, cols) {
  for (let r = 1; r <= rows; r++) {
    for (let c = 1; c <= cols; c++) {
      const cell = ws.getCell(r, c);
      cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: '0A0F1E' } };
      cell.font = { color: { argb: 'FFFFFF' }, size: 10 };
    }
  }
}

function styleTitle(cell, C) {
  cell.font = { color: { argb: C.green }, bold: true, size: 13 };
  cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.dark } };
}

function styleSection(cell, C) {
  cell.font = { color: { argb: C.green }, bold: true, size: 10 };
  cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: C.dark3 } };
  cell.border = {
    bottom: { style: 'medium', color: { argb: C.green } },
  };
}

generarExcel().catch(console.error);
