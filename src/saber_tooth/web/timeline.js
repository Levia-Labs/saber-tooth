/* global window */
// Pure canvas drawing for proposal windows: a 4x3 lane grid per beat slice.
export const COLORS = { 0: "#ff3b4e", 1: "#2f9bff" };
const ARROW_ANGLE = { 0: -90, 1: 90, 2: 180, 3: 0, 4: -135, 5: -45, 6: 135, 7: 45 };
const BG = "#12131a";
const GRID = "#2a2d3a";

/** Beat window [start, end] covering all notes, padded to whole beats. */
export function beatWindow(...noteLists) {
  const beats = noteLists.flat().map((n) => n.beat);
  if (!beats.length) return { start: 0, end: 1 };
  return { start: Math.floor(Math.min(...beats)), end: Math.floor(Math.max(...beats)) + 1 };
}

/** True when neither side has notes (e.g. wall-only proposals): nothing to draw. */
export function isNotesless(before, after) {
  return !before.length && !after.length;
}

/** Distinct sorted beats present in the notes (the slices that get a grid). */
export function sliceBeats(notes) {
  return [...new Set(notes.map((n) => n.beat))].sort((a, b) => a - b);
}

function drawArrow(ctx, cx, cy, r, cut) {
  ctx.fillStyle = "#fff";
  if (cut === 8 || !(cut in ARROW_ANGLE)) {
    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.22, 0, Math.PI * 2);
    ctx.fill();
    return;
  }
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate((ARROW_ANGLE[cut] * Math.PI) / 180);
  ctx.beginPath();
  ctx.moveTo(r * 0.45, 0);
  ctx.lineTo(-r * 0.25, r * 0.35);
  ctx.lineTo(-r * 0.25, -r * 0.35);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

function drawSlice(ctx, notes, x0, y0, cell, label) {
  ctx.strokeStyle = GRID;
  ctx.lineWidth = 1;
  for (let gx = 0; gx < 4; gx++) {
    for (let gy = 0; gy < 3; gy++) {
      ctx.strokeRect(x0 + gx * cell + 0.5, y0 + (2 - gy) * cell + 0.5, cell - 1, cell - 1);
    }
  }
  const r = cell * 0.4;
  for (const n of notes) {
    const cx = x0 + n.x * cell + cell / 2;
    const cy = y0 + (2 - n.y) * cell + cell / 2;
    ctx.fillStyle = COLORS[n.color] || "#888";
    ctx.fillRect(cx - r, cy - r, r * 2, r * 2);
    drawArrow(ctx, cx, cy, r, n.cut);
  }
  ctx.fillStyle = "#9aa0b4";
  ctx.font = "11px system-ui, sans-serif";
  ctx.textAlign = "left";
  ctx.fillText(label, x0, y0 + cell * 3 + 13);
}

/** Layout metrics for one panel: slices laid out in a wrapping row. */
export function layout(sliceCount, width, cell) {
  const slicePitch = cell * 4 + 12;
  const perRow = Math.max(1, Math.floor(width / slicePitch));
  const rows = Math.max(1, Math.ceil(sliceCount / perRow));
  return { slicePitch, perRow, rows, rowHeight: cell * 3 + 24 };
}

function drawPanel(ctx, notes, x, width, title, cell) {
  const beats = sliceBeats(notes);
  ctx.fillStyle = "#e8eaf3";
  ctx.font = "600 12px system-ui, sans-serif";
  ctx.textAlign = "left";
  ctx.fillText(title, x + 4, 14);
  const { slicePitch, perRow } = layout(beats.length, width, cell);
  beats.forEach((beat, i) => {
    const col = i % perRow;
    const row = Math.floor(i / perRow);
    const at = notes.filter((n) => n.beat === beat);
    drawSlice(ctx, at, x + 4 + col * slicePitch, 24 + row * (cell * 3 + 24), cell, `beat ${beat}`);
  });
  if (!beats.length) {
    ctx.fillStyle = "#6b7089";
    ctx.fillText("no notes", x + 4, 40);
  }
}

/** Needed CSS height for the given notes and CSS width. */
export function timelineHeight(before, after, width, cell = 22) {
  const half = width / 2;
  const rows = Math.max(
    layout(sliceBeats(before).length, half, cell).rows,
    layout(sliceBeats(after).length, half, cell).rows,
  );
  return 24 + rows * (cell * 3 + 24);
}

/** Draw before (left) and after (right) panels. Sizes the canvas for devicePixelRatio. */
export function drawTimeline(canvas, before, after, opts = {}) {
  const cell = opts.cell || 22;
  const dpr = opts.dpr || (typeof window !== "undefined" && window.devicePixelRatio) || 1;
  const width = opts.width || canvas.clientWidth || 640;
  const height = timelineHeight(before, after, width, cell);
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  canvas.style.height = `${height}px`;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = BG;
  ctx.fillRect(0, 0, width, height);
  const half = width / 2;
  drawPanel(ctx, before, 0, half, "Before", cell);
  drawPanel(ctx, after, half, half, "After", cell);
  ctx.strokeStyle = GRID;
  ctx.beginPath();
  ctx.moveTo(half + 0.5, 0);
  ctx.lineTo(half + 0.5, height);
  ctx.stroke();
}
