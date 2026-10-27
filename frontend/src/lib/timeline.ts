// Canvas drawing for proposal windows: a 4x3 lane grid per beat slice. Geometry is pure.
import type { Note, Wall } from "../api/types";

export const COLORS: Record<number, string> = { 0: "#ff3b4e", 1: "#2f9bff" };
const ARROW_ANGLE: Record<number, number> = {
  0: -90,
  1: 90,
  2: 180,
  3: 0,
  4: -135,
  5: -45,
  6: 135,
  7: 45,
};
const BG = "#12131a";
const GRID = "#2a2d3a";
const WALL = "rgba(150, 130, 200, 0.35)";
const WALL_CONTEXT = "rgba(150, 130, 200, 0.14)";

type Beat = { beat: number };
export interface BeatWindow {
  start: number;
  end: number;
}
export interface Geometry {
  x0: number;
  y0: number;
  cell: number;
}
export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}
export interface Layer {
  walls: Wall[];
  fill: string;
}
export interface TimelineOptions {
  cell?: number;
  dpr?: number;
  width?: number;
  wallsBefore?: Wall[];
  wallsAfter?: Wall[];
  wallsContext?: Wall[];
}

/** Beat window [start, end] covering all notes, padded to whole beats. */
export function beatWindow(...lists: Beat[][]): BeatWindow {
  const beats = lists.flat().map((n) => n.beat);
  if (!beats.length) return { start: 0, end: 1 };
  return { start: Math.floor(Math.min(...beats)), end: Math.floor(Math.max(...beats)) + 1 };
}

/** True when neither side has notes (e.g. wall-only proposals): nothing to draw. */
export function isNotesless(before: Beat[], after: Beat[], walls: Beat[] = []): boolean {
  return !before.length && !after.length && !walls.length;
}

/** Distinct sorted beats present in the notes (the slices that get a grid). */
export function sliceBeats(notes: Beat[]): number[] {
  return [...new Set(notes.map((n) => n.beat))].sort((a, b) => a - b);
}

/** Grid rectangles for walls overlapping the beat window, clipped to the 4x3 grid. */
export function wallRects(walls: Wall[] | undefined, window: BeatWindow, g: Geometry): Rect[] {
  const rects: Rect[] = [];
  for (const w of walls ?? []) {
    if (w.beat > window.end || w.beat + w.duration < window.start) continue;
    const left = Math.max(0, w.x);
    const right = Math.min(4, w.x + w.width);
    const bottom = Math.max(0, w.y);
    const top = Math.min(3, w.y + w.height);
    if (right <= left || top <= bottom) continue;
    rects.push({
      x: g.x0 + left * g.cell,
      y: g.y0 + (3 - top) * g.cell,
      w: (right - left) * g.cell,
      h: (top - bottom) * g.cell,
    });
  }
  return rects;
}

/** Wall layers in paint order: fainter context walls under the changed walls. */
export function wallLayers(walls?: Wall[], context?: Wall[]): [Layer, Layer] {
  return [
    { walls: context ?? [], fill: WALL_CONTEXT },
    { walls: walls ?? [], fill: WALL },
  ];
}

/** Layout metrics for one panel: slices laid out in a wrapping row. */
export function layout(sliceCount: number, width: number, cell: number) {
  const slicePitch = cell * 4 + 12;
  const perRow = Math.max(1, Math.floor(width / slicePitch));
  const rows = Math.max(1, Math.ceil(sliceCount / perRow));
  return { slicePitch, perRow, rows, rowHeight: cell * 3 + 24 };
}

/** Needed CSS height for the given notes and CSS width. */
export function timelineHeight(before: Beat[], after: Beat[], width: number, cell = 22): number {
  const half = width / 2;
  const rows = Math.max(
    layout(sliceBeats(before).length, half, cell).rows,
    layout(sliceBeats(after).length, half, cell).rows,
  );
  return 24 + rows * (cell * 3 + 24);
}

type Ctx = CanvasRenderingContext2D;

function drawArrow(ctx: Ctx, cx: number, cy: number, r: number, cut: number): void {
  ctx.fillStyle = "#fff";
  const angle = ARROW_ANGLE[cut];
  if (cut === 8 || angle === undefined) {
    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.22, 0, Math.PI * 2);
    ctx.fill();
    return;
  }
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate((angle * Math.PI) / 180);
  ctx.beginPath();
  ctx.moveTo(r * 0.45, 0);
  ctx.lineTo(-r * 0.25, r * 0.35);
  ctx.lineTo(-r * 0.25, -r * 0.35);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

function drawSlice(ctx: Ctx, notes: Note[], layers: Layer[], g: Geometry, beat: number): void {
  const { x0, y0, cell } = g;
  for (const layer of layers) {
    ctx.fillStyle = layer.fill;
    for (const r of wallRects(layer.walls, { start: beat, end: beat }, g)) {
      ctx.fillRect(r.x, r.y, r.w, r.h);
    }
  }
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
    ctx.fillStyle = COLORS[n.color] ?? "#888";
    ctx.fillRect(cx - r, cy - r, r * 2, r * 2);
    drawArrow(ctx, cx, cy, r, n.cut);
  }
  ctx.fillStyle = "#9aa0b4";
  ctx.font = "11px system-ui, sans-serif";
  ctx.textAlign = "left";
  ctx.fillText(`beat ${beat}`, x0, y0 + cell * 3 + 13);
}

function drawPanel(ctx: Ctx, notes: Note[], layers: [Layer, Layer], panel: PanelBox): void {
  const { x, width, title, cell } = panel;
  const beats = sliceBeats([...notes, ...layers[1].walls]);
  ctx.fillStyle = "#e8eaf3";
  ctx.font = "600 12px system-ui, sans-serif";
  ctx.textAlign = "left";
  ctx.fillText(title, x + 4, 14);
  const { slicePitch, perRow } = layout(beats.length, width, cell);
  beats.forEach((beat, i) => {
    const at = notes.filter((n) => n.beat === beat);
    const g = {
      x0: x + 4 + (i % perRow) * slicePitch,
      y0: 24 + Math.floor(i / perRow) * (cell * 3 + 24),
      cell,
    };
    drawSlice(ctx, at, layers, g, beat);
  });
  if (!beats.length) {
    ctx.fillStyle = "#6b7089";
    ctx.fillText("nothing here", x + 4, 40);
  }
}

interface PanelBox {
  x: number;
  width: number;
  title: string;
  cell: number;
}

/** Draw before (left) and after (right) panels. Sizes the canvas for devicePixelRatio. */
export function drawTimeline(
  canvas: HTMLCanvasElement,
  before: Note[],
  after: Note[],
  opts: TimelineOptions = {},
): void {
  const cell = opts.cell ?? 22;
  const dpr = opts.dpr ?? window.devicePixelRatio ?? 1;
  const width = opts.width ?? (canvas.clientWidth || 640);
  const wb = opts.wallsBefore ?? [];
  const wa = opts.wallsAfter ?? [];
  const context = opts.wallsContext ?? [];
  const height = timelineHeight([...before, ...wb], [...after, ...wa], width, cell);
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  canvas.style.height = `${height}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = BG;
  ctx.fillRect(0, 0, width, height);
  const half = width / 2;
  drawPanel(ctx, before, wallLayers(wb, context), { x: 0, width: half, title: "Before", cell });
  drawPanel(ctx, after, wallLayers(wa, context), { x: half, width: half, title: "After", cell });
  ctx.strokeStyle = GRID;
  ctx.beginPath();
  ctx.moveTo(half + 0.5, 0);
  ctx.lineTo(half + 0.5, height);
  ctx.stroke();
}

const BEATS_PER_BAR = 4;

function bar(beat: number): string {
  const b = Math.max(0, beat);
  return `${Math.floor(b / BEATS_PER_BAR) + 1}:${Math.floor(b % BEATS_PER_BAR) + 1}`;
}

/** "bars:beats" range (1-based, 4 beats to a bar) covering everything a proposal touches. */
export function beatRange(...lists: Beat[][]): string {
  if (!lists.some((l) => l.length)) return "no notes";
  const { start, end } = beatWindow(...lists);
  const last = end - 1;
  return start === last ? bar(start) : `${bar(start)} - ${bar(last)}`;
}

type Placed = Partial<Note> & Partial<Wall> & { beat: number };

function keyOf(item: Placed): string {
  return [item.beat, item.x, item.y, item.color, item.cut, item.duration, item.width, item.height]
    .map((v) => v ?? "")
    .join("/");
}

/** Operations a proposal performs: items only in the before side plus items only in the after. */
export function countOperations(before: Placed[], after: Placed[]): number {
  const a = new Set(before.map(keyOf));
  const b = new Set(after.map(keyOf));
  let n = 0;
  for (const k of a) if (!b.has(k)) n += 1;
  for (const k of b) if (!a.has(k)) n += 1;
  return n;
}
