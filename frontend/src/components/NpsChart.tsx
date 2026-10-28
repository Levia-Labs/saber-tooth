import { useState, type KeyboardEvent, type PointerEvent } from "react";
import type { CropSection, EndKind } from "../api/types";
import { KIND_LABEL, clock, secondsAt } from "../lib/crop";

const W = 1000;
const H = 160;
const PAD = 8;
const MARK_LEN: Record<EndKind, number> = { section: 30, phrase: 22, bar4: 14, bar: 7 };

export type Edge = "start" | "end";

export interface Span {
  start_s: number;
  end_s: number;
}

export interface EndMark {
  seconds: number;
  kind: EndKind;
}

interface Props {
  nps: Record<string, number[]>;
  hardest: string;
  sections: CropSection[];
  duration: number;
  selection: Span | null;
  faint: Span[];
  endMarks: EndMark[];
  onMove: (edge: Edge, seconds: number) => void;
  onStep: (edge: Edge, dir: 1 | -1, jump: boolean) => void;
}

const px = (seconds: number, duration: number): number =>
  duration > 0 ? (seconds / duration) * W : 0;

function line(values: number[], top: number, duration: number): string {
  return values
    .map((v, i) => {
      const y = H - PAD - (v / top) * (H - 2 * PAD);
      return `${i === 0 ? "M" : "L"}${px(i + 0.5, duration).toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");
}

function hoverText(seconds: number, nps: Props["nps"], sections: CropSection[]): string {
  const at = sections.findIndex((s) => s.start_s <= seconds && seconds < s.end_s);
  const where = at === -1 ? "no section" : `section ${at + 1} of ${sections.length}`;
  const rates = Object.entries(nps).map(([name, v]) => `${name} ${v[Math.floor(seconds)] ?? 0}`);
  return `${clock(seconds)}, ${where}, notes per second: ${rates.join(", ")}`;
}

function capture(el: Element | null, id: number): void {
  if (el && "setPointerCapture" in el) el.setPointerCapture(id);
}

interface HandleProps {
  edge: Edge;
  seconds: number;
  duration: number;
  onDown: (e: PointerEvent<SVGGElement>) => void;
  onStep: Props["onStep"];
}

function Handle({ edge, seconds, duration, onDown, onStep }: HandleProps) {
  const onKey = (e: KeyboardEvent) => {
    const dir =
      e.key === "ArrowRight" || e.key === "ArrowUp"
        ? 1
        : e.key === "ArrowLeft" || e.key === "ArrowDown"
          ? -1
          : 0;
    if (dir === 0) return;
    e.preventDefault();
    onStep(edge, dir, e.shiftKey);
  };
  const x = px(seconds, duration);
  return (
    <g
      className={`nps-handle nps-handle-${edge}`}
      role="slider"
      tabIndex={0}
      aria-label={edge === "start" ? "Crop start" : "Crop end"}
      aria-orientation="horizontal"
      aria-valuemin={0}
      aria-valuemax={Math.round(duration)}
      aria-valuenow={Math.round(seconds * 10) / 10}
      aria-valuetext={clock(seconds)}
      onKeyDown={onKey}
      onPointerDown={onDown}
    >
      <line x1={x} x2={x} y1={0} y2={H} />
      <rect x={x - 6} y={H / 2 - 14} width={12} height={28} rx={3} />
    </g>
  );
}

/** Notes per second across the song: one line per difficulty, sections as bands, the chosen window
 * and its two draggable, keyboard-steppable edges. */
export function NpsChart({
  nps,
  hardest,
  sections,
  duration,
  selection,
  faint,
  endMarks,
  onMove,
  onStep,
}: Props) {
  const [hover, setHover] = useState<number | null>(null);
  const [drag, setDrag] = useState<Edge | null>(null);
  const top = Math.max(1, ...Object.values(nps).flat());
  const begin = (edge: Edge) => (e: PointerEvent<SVGGElement>) => {
    capture(e.currentTarget.ownerSVGElement, e.pointerId);
    setDrag(edge);
  };
  const move = (e: PointerEvent<SVGSVGElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    const seconds = secondsAt(e.clientX, box.left, box.width, duration);
    if (drag) onMove(drag, seconds);
    else setHover(seconds);
  };
  const span = (s: Span) => ({
    x: px(s.start_s, duration),
    width: px(s.end_s - s.start_s, duration),
  });
  return (
    <div className="nps-chart">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        role="group"
        aria-label="Notes per second across the song"
        onPointerMove={move}
        onPointerUp={() => setDrag(null)}
        onPointerCancel={() => setDrag(null)}
        onPointerLeave={() => setHover(null)}
      >
        {sections.map((s, i) => (
          <rect
            key={s.start_beat}
            className={i % 2 === 0 ? "nps-section" : "nps-section nps-section-odd"}
            {...span(s)}
            y={0}
            height={H}
            style={{ opacity: 0.12 + 0.3 * s.intensity }}
          />
        ))}
        {faint.map((w) => (
          <rect key={w.start_s} className="nps-faint" {...span(w)} y={0} height={H} />
        ))}
        {selection && <rect className="nps-selection" {...span(selection)} y={0} height={H} />}
        {Object.entries(nps).map(([name, values]) => (
          <path
            key={name}
            className={name === hardest ? "nps-line nps-line-hardest" : "nps-line"}
            data-difficulty={name}
            d={line(values, top, duration)}
            fill="none"
          />
        ))}
        {endMarks.map((m) => (
          <line
            key={m.seconds}
            className={`nps-end nps-end-${m.kind}`}
            data-kind={m.kind}
            x1={px(m.seconds, duration)}
            x2={px(m.seconds, duration)}
            y1={H}
            y2={H - MARK_LEN[m.kind]}
          >
            <title>{KIND_LABEL[m.kind]}</title>
          </line>
        ))}
        {selection && (
          <>
            <Handle
              edge="start"
              seconds={selection.start_s}
              duration={duration}
              onDown={begin("start")}
              onStep={onStep}
            />
            <Handle
              edge="end"
              seconds={selection.end_s}
              duration={duration}
              onDown={begin("end")}
              onStep={onStep}
            />
          </>
        )}
      </svg>
      <p className="nps-hover" aria-live="off">
        {hover === null
          ? "Hover the chart for time, section and notes per second."
          : hoverText(hover, nps, sections)}
      </p>
    </div>
  );
}
