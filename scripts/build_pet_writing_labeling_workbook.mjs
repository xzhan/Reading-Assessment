import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..");
const outputDir = path.join(repoRoot, "outputs", "pet_writing_labeling");
const outputPath = path.join(outputDir, "pet_writing_labeling_rubric_sheet.xlsx");

function headingFill() {
  return {
    type: "solid",
    color: { type: "theme", value: "accent1", transform: { darken: 8 } },
  };
}

function sectionFill() {
  return {
    type: "solid",
    color: { type: "theme", value: "accent1", transform: { lighten: 75 } },
  };
}

function noteFill() {
  return {
    type: "solid",
    color: { type: "theme", value: "accent2", transform: { lighten: 78 } },
  };
}

function setTitle(range) {
  range.format = {
    font: { name: "Calibri", size: 16, bold: true, color: "tx1" },
    fill: sectionFill(),
    wrapText: true,
  };
}

function setHeader(range) {
  range.format = {
    font: { name: "Calibri", size: 11, bold: true, color: "#FFFFFF" },
    fill: headingFill(),
    borders: { preset: "outside", style: "thin", color: "#D1D5DB" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
  };
}

function setTable(range) {
  range.format = {
    font: { name: "Calibri", size: 11, color: "tx1" },
    borders: { preset: "outside", style: "thin", color: "#D1D5DB" },
    verticalAlignment: "center",
    wrapText: true,
  };
}

function applyAltFill(range) {
  range.format.fill = noteFill();
}

function overallFormula(row) {
  return `=IF(COUNT(I${row}:L${row})=0,"",SUM(I${row}:L${row}))`;
}

function readinessFormula(row) {
  return `=IF(OR(M${row}="",M${row}=0),"",IF(M${row}>=15,"on_track",IF(M${row}>=11,"borderline","below_target")))`;
}

function reviewFormula(row) {
  return `=IF(OR(M${row}="",M${row}=0),"",IF(OR(M${row}<11,MIN(I${row}:L${row})<=1),"REVIEW","OK"))`;
}

function buildInstructionsSheet(workbook) {
  const sheet = workbook.worksheets.add("Instructions");
  sheet.getRange("A1:F1").values = [[
    "PET Writing Manual Labeling Pack",
    "",
    "",
    "",
    "",
    "",
  ]];
  setTitle(sheet.getRange("A1:F1"));

  const rows = [
    ["What this workbook is for", "Use this workbook to help teachers score PET Writing consistently before the essays are converted into JSONL training data."],
    ["Recommended workflow", "1. Read the prompt. 2. Read the essay once for meaning. 3. Score the four dimensions separately. 4. Add a brief strength note and issue note. 5. Flag REVIEW when confidence is low or the essay is far below target."],
    ["Score scale", "Use a 0-5 scale for each dimension. 0-1 = very weak, 2 = below PET target, 3 = borderline, 4 = solid PET level, 5 = strong PET-level response."],
    ["When to use REVIEW", "Use REVIEW when the essay is off-topic, very short, heavily unclear, or when the rater is not confident in one or more dimension scores."],
    ["What to avoid", "Do not let grammar automatically lower every dimension. Score Task, Organization, Grammar, and Lexical control separately."],
    ["Next step after scoring", "Copy completed rows into the JSONL labeling file once a second review or spot check is done."],
  ];
  sheet.getRange(`A3:B${rows.length + 2}`).values = rows;
  setHeader(sheet.getRange("A3:B3"));
  setTable(sheet.getRange(`A4:B${rows.length + 2}`));
  sheet.getRange(`A4:A${rows.length + 2}`).format.font = { name: "Calibri", size: 11, bold: true, color: "tx1" };
  sheet.getRange(`B4:B${rows.length + 2}`).format.wrapText = true;

  const quickChecklist = [
    ["Quick checklist before you save a row"],
    ["Did the student answer all parts of the task?"],
    ["Are the ideas linked clearly enough?"],
    ["Are grammar errors frequent or meaning-blocking?"],
    ["Is the vocabulary accurate and not overly repetitive?"],
  ];
  sheet.getRange("D3:D7").values = quickChecklist;
  setHeader(sheet.getRange("D3:D3"));
  sheet.getRange("D4:D7").format = {
    fill: noteFill(),
    borders: { preset: "outside", style: "thin", color: "#D1D5DB" },
    wrapText: true,
  };

  sheet.freezePanes.freezeRows(3);
  sheet.getRange("A1:F20").format.autofitColumns();
  sheet.getRange("A1:F20").format.autofitRows();
  return sheet;
}

function buildRubricSheet(workbook) {
  const sheet = workbook.worksheets.add("Rubric");
  sheet.getRange("A1:G1").values = [[
    "PET Writing Rubric Reference",
    "",
    "",
    "",
    "",
    "",
    "",
  ]];
  setTitle(sheet.getRange("A1:G1"));

  const rubricHeader = [["Dimension", "1", "2", "3", "4", "5", "Guiding question"]];
  sheet.getRange("A3:G3").values = rubricHeader;
  setHeader(sheet.getRange("A3:G3"));

  const rubricRows = [
    ["Task Achievement", "Very incomplete task response", "Covers some task points", "Covers most task points", "Clear response to the full task", "Complete and convincing PET-level response", "Did the student answer what the prompt asked?"],
    ["Organization & Coherence", "Ideas are disconnected", "Some order but weak linking", "Meaning can be followed", "Ideas are clearly organized", "Ideas flow smoothly and clearly", "Can the reader follow the message easily?"],
    ["Grammar Control", "Frequent errors block meaning", "Many errors reduce clarity", "Errors exist but meaning survives", "Mostly controlled grammar", "Strong control with few disruptive errors", "Do grammar errors seriously affect understanding?"],
    ["Lexical Range & Accuracy", "Very limited vocabulary", "Basic words with frequent misuse", "Simple but mostly usable vocabulary", "Adequate range for PET", "Flexible and accurate PET-level vocabulary", "Are the words varied and used accurately?"],
  ];
  sheet.getRange(`A4:G${rubricRows.length + 3}`).values = rubricRows;
  setTable(sheet.getRange(`A4:G${rubricRows.length + 3}`));
  sheet.getRange(`A4:A${rubricRows.length + 3}`).format.font = { name: "Calibri", size: 11, bold: true, color: "tx1" };
  applyAltFill(sheet.getRange("B4:F4"));
  applyAltFill(sheet.getRange("B6:F6"));

  const noteRows = [
    ["Dimension-specific note"],
    ["Task Achievement should carry the main penalty when the essay misses content points or is too short."],
    ["Organization should focus on paragraphing, logic, and connectors rather than grammar accuracy."],
    ["Grammar should reflect control of tense, verb forms, articles, and sentence clarity."],
    ["Lexical score should reflect variety and accuracy, not just advanced vocabulary."],
  ];
  sheet.getRange("A10:G14").values = noteRows.map((row) => [row[0], row[1] || "", "", "", "", "", ""]);
  setHeader(sheet.getRange("A10:G10"));
  sheet.getRange("A11:G14").format = {
    fill: noteFill(),
    borders: { preset: "outside", style: "thin", color: "#D1D5DB" },
    wrapText: true,
  };
  sheet.freezePanes.freezeRows(3);
  sheet.getRange("A1:G20").format.autofitColumns();
  sheet.getRange("A1:G20").format.autofitRows();
  return sheet;
}

function buildScoringSheet(workbook) {
  const sheet = workbook.worksheets.add("Scoring Sheet");
  sheet.getRange("A1:R1").values = [[
    "PET Writing Scoring Sheet",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
  ]];
  setTitle(sheet.getRange("A1:R1"));
  sheet.getRange("A2:R2").values = [[
    "Fill one row per essay. Score the four dimensions on a 0-5 scale. Overall, readiness, and review flag are calculated automatically.",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
  ]];
  sheet.getRange("A2:R2").format = {
    fill: noteFill(),
    font: { name: "Calibri", size: 10, italic: true, color: "tx1" },
    wrapText: true,
  };

  const headers = [[
    "Sample ID",
    "Student",
    "Prompt ID",
    "Type",
    "Rater",
    "Date",
    "Time (sec)",
    "Words",
    "Task",
    "Org",
    "Grammar",
    "Lexical",
    "Overall",
    "Readiness",
    "Review",
    "Strength Notes",
    "Issue Notes",
    "Status",
  ]];
  sheet.getRange("A4:R4").values = headers;
  setHeader(sheet.getRange("A4:R4"));

  const startRow = 5;
  const endRow = 44;
  const blankRows = [];
  for (let row = startRow; row <= endRow; row += 1) {
    blankRows.push(["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]);
  }
  sheet.getRange(`A${startRow}:R${endRow}`).values = blankRows;
  setTable(sheet.getRange(`A${startRow}:R${endRow}`));
  sheet.getRange(`M${startRow}:M${endRow}`).formulas = Array.from(
    { length: endRow - startRow + 1 },
    (_, index) => [overallFormula(startRow + index)],
  );
  sheet.getRange(`N${startRow}:N${endRow}`).formulas = Array.from(
    { length: endRow - startRow + 1 },
    (_, index) => [readinessFormula(startRow + index)],
  );
  sheet.getRange(`O${startRow}:O${endRow}`).formulas = Array.from(
    { length: endRow - startRow + 1 },
    (_, index) => [reviewFormula(startRow + index)],
  );
  sheet.getRange(`I${startRow}:L${endRow}`).dataValidation = {
    rule: { type: "whole", operator: "between", formula1: 0, formula2: 5 },
    errorAlert: {
      style: "stop",
      title: "Invalid score",
      message: "Enter a whole-number score between 0 and 5.",
    },
  };
  sheet.getRange(`D${startRow}:D${endRow}`).dataValidation = {
    allowBlank: true,
    list: { inCellDropDown: true, source: ["email", "article"] },
  };
  sheet.getRange(`R${startRow}:R${endRow}`).dataValidation = {
    allowBlank: true,
    list: { inCellDropDown: true, source: ["draft", "approved", "needs_review"] },
  };
  sheet.getRange(`P${startRow}:Q${endRow}`).format.wrapText = true;
  sheet.getRange(`G${startRow}:L${endRow}`).format.horizontalAlignment = "center";
  sheet.getRange(`M${startRow}:O${endRow}`).format.horizontalAlignment = "center";
  sheet.freezePanes.freezeRows(4);
  sheet.freezePanes.freezeColumns(3);
  sheet.getRange("A1:R44").format.autofitColumns();
  sheet.getRange("A1:R44").format.autofitRows();
  return sheet;
}

function buildSampleSheet(workbook) {
  const sheet = workbook.worksheets.add("Sample Filled");
  sheet.getRange("A1:R1").values = [[
    "Sample Filled Rows",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
  ]];
  setTitle(sheet.getRange("A1:R1"));
  const headers = [[
    "Sample ID",
    "Student",
    "Prompt ID",
    "Type",
    "Rater",
    "Date",
    "Time (sec)",
    "Words",
    "Task",
    "Org",
    "Grammar",
    "Lexical",
    "Overall",
    "Readiness",
    "Review",
    "Strength Notes",
    "Issue Notes",
    "Status",
  ]];
  sheet.getRange("A3:R3").values = headers;
  setHeader(sheet.getRange("A3:R3"));

  const rows = [
    ["email_001", "Student A", "wp_pet_email_001", "email", "teacher_01", "2026-04-23", 980, 43, 5, 4, 4, 4, "", "", "", "Complete task response and clear invitation.", "Could add slightly richer vocabulary in the middle paragraph.", "approved"],
    ["email_004", "Student B", "wp_pet_email_001", "email", "teacher_02", "2026-04-23", 540, 10, 2, 1, 1, 1, "", "", "", "The task topic is partly addressed.", "Very short response and grammar errors make the message unclear.", "needs_review"],
    ["article_005", "Student C", "wp_pet_article_001", "article", "teacher_03", "2026-04-23", 1110, 44, 5, 5, 4, 4, "", "", "", "Strong task completion and very clear organization.", "Grammar is good overall, but sentence variety could still grow.", "approved"],
  ];
  sheet.getRange(`A4:R${rows.length + 3}`).values = rows;
  setTable(sheet.getRange(`A4:R${rows.length + 3}`));
  sheet.getRange(`M4:M${rows.length + 3}`).formulas = Array.from(
    { length: rows.length },
    (_, index) => [overallFormula(4 + index)],
  );
  sheet.getRange(`N4:N${rows.length + 3}`).formulas = Array.from(
    { length: rows.length },
    (_, index) => [readinessFormula(4 + index)],
  );
  sheet.getRange(`O4:O${rows.length + 3}`).formulas = Array.from(
    { length: rows.length },
    (_, index) => [reviewFormula(4 + index)],
  );
  sheet.getRange("P4:Q6").format.wrapText = true;
  sheet.freezePanes.freezeRows(3);
  sheet.getRange("A1:R10").format.autofitColumns();
  sheet.getRange("A1:R10").format.autofitRows();
  return sheet;
}

async function main() {
  const workbook = Workbook.create();
  buildInstructionsSheet(workbook);
  buildRubricSheet(workbook);
  buildScoringSheet(workbook);
  buildSampleSheet(workbook);

  const inspectScoring = await workbook.inspect({
    kind: "table",
    range: "Scoring Sheet!A1:R12",
    include: "values,formulas",
    tableMaxRows: 12,
    tableMaxCols: 18,
  });
  console.log(inspectScoring.ndjson);

  const errorScan = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 100 },
    summary: "formula error scan",
  });
  console.log(errorScan.ndjson);

  await fs.mkdir(outputDir, { recursive: true });
  const instructionsPreview = await workbook.render({ sheetName: "Instructions", range: "A1:F16", scale: 2 });
  await fs.writeFile(
    path.join(outputDir, "preview_instructions.png"),
    Buffer.from(await instructionsPreview.arrayBuffer()),
  );
  const rubricPreview = await workbook.render({ sheetName: "Rubric", range: "A1:G16", scale: 2 });
  await fs.writeFile(
    path.join(outputDir, "preview_rubric.png"),
    Buffer.from(await rubricPreview.arrayBuffer()),
  );
  const scoringPreview = await workbook.render({ sheetName: "Scoring Sheet", range: "A1:R14", scale: 2 });
  await fs.writeFile(
    path.join(outputDir, "preview_scoring_sheet.png"),
    Buffer.from(await scoringPreview.arrayBuffer()),
  );
  const samplePreview = await workbook.render({ sheetName: "Sample Filled", range: "A1:R10", scale: 2 });
  await fs.writeFile(
    path.join(outputDir, "preview_sample_filled.png"),
    Buffer.from(await samplePreview.arrayBuffer()),
  );

  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);
  console.log(`Saved workbook to ${outputPath}`);
}

await main();
