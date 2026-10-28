import { useState, type MouseEvent, type PointerEvent } from "react";
import type { CropSection, EndKind } from "../api/types";
import { npsTicks, yFrac } from "../lib/axis";
import { KIND_LABEL, clampStart, clock, sectionAt, secondsAt } from "../lib/crop";
import { levelColor } from "../lib/levels";
import { Legend, TimeAxis, YAxis } from "./ChartAxes";
import { H, Handle, MoveButtons, W, px } from "./ChartHandles";
import { PlayButton, Playhead } from "./ChartPlayback";

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
  /** A handle moved to this second while being dragged. */
  onMove: (edge: Edge, seconds: number) => void;
  onStep: (edge: Edge, dir: 1 | -1, jump: boolean) => void;
  /** The whole window was dragged and released with its start at this second. */
  onShift: (startSeconds: number) => void;
  /** A section other than the selection was double-clicked: move the selection to start there. */
  onJump: (sectionStartSeconds: number) => void;
  /** Step the whole window to the previous or next allowed start. */
  onShiftStep: (dir: 1 | -1) => void;
  canShift: { earlier: boolean; later: boolean };
  /** Map audio; without it there is no play button. */
  audioUrl?: string | null;
}

type Drag = { kind: Edge } | { kind: "window"; grab: number; at: number; moved: boolean };

function line(values: number[], top: number, duration: number): string {
  return values
    .map((v, i) => {
      const y = H - yFrac(v, top) * H;
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

/** Notes per second across the song: one coloured line per difficulty, sections as bands, axes, the
 * chosen window with two draggable, keyboard-steppable edges, and a body that drags as a whole. */
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
  onShift,
  onJump,
  onShiftStep,
  canShift,
  audioUrl,
}: Props) {
  const [hover, setHover] = useState<number | null>(null);
  const [drag, setDrag] = useState<Drag | null>(null);
  const [focus, setFocus] = useState<Edge | null>(null);
  const names = Object.keys(nps);
  const { ticks, top } = npsTicks(Math.max(0, ...Object.values(nps).flat()));
  const length = selection ? selection.end_s - selection.start_s : 0;
  const live =
    selection && drag?.kind === "window"
      ? { start_s: drag.at, end_s: drag.at + length }
      : selection;
  const at = (e: PointerEvent<Element>, svg: SVGSVGElement | null): number => {
    const box = (svg ?? (e.currentTarget as SVGSVGElement)).getBoundingClientRect();
    return secondsAt(e.clientX, box.left, box.width, duration);
  };
  const beginEdge = (edge: Edge) => (e: PointerEvent<SVGGElement>) => {
    capture(e.currentTarget.ownerSVGElement, e.pointerId);
    setDrag({ kind: edge });
  };
  const beginWindow = (e: PointerEvent<SVGRectElement>) => {
    if (!selection) return;
    const svg = e.currentTarget.ownerSVGElement;
    capture(svg, e.pointerId);
    setDrag({
      kind: "window",
      grab: at(e, svg) - selection.start_s,
      at: selection.start_s,
      moved: false,
    });
  };
  const move = (e: PointerEvent<SVGSVGElement>) => {
    const seconds = at(e, null);
    if (drag?.kind === "window") {
      setDrag({ ...drag, at: clampStart(seconds - drag.grab, length, duration), moved: true });
    } else if (drag) onMove(drag.kind, seconds);
    else setHover(seconds);
  };
  const release = (commit: boolean) => {
    if (commit && drag?.kind === "window" && drag.moved) onShift(drag.at);
    setDrag(null);
  };
  const jump = (e: MouseEvent<SVGSVGElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    const seconds = secondsAt(e.clientX, box.left, box.width, duration);
    const inside = selection && seconds >= selection.start_s && seconds < selection.end_s;
    const band = sectionAt(sections, seconds);
    if (band && !inside) onJump(band.start_s);
  };
  const focused = focus && selection ? selection[focus === "start" ? "start_s" : "end_s"] : null;
  const shown = hover ?? focused;
  const span = (s: Span) => ({
    x: px(s.start_s, duration),
    width: px(s.end_s - s.start_s, duration),
  });
  return (
    <div className="nps-chart">
      <div className="nps-grid">
        <YAxis ticks={ticks} top={top} />
        <div className="nps-stage">
          <svg
            viewBox={`0 0 ${W} ${H}`}
            preserveAspectRatio="none"
            role="group"
            aria-label="Notes per second across the song"
            onPointerMove={move}
            onPointerUp={() => release(true)}
            onPointerCancel={() => release(false)}
            onPointerLeave={() => setHover(null)}
            onDoubleClick={jump}
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
            {live && (
              <rect
                className="nps-selection"
                {...span(live)}
                y={0}
                height={H}
                onPointerDown={beginWindow}
              />
            )}
            {ticks.map((t) => (
              <line
                key={t}
                className="nps-grid-line"
                x1={0}
                x2={W}
                y1={H - yFrac(t, top) * H}
                y2={H - yFrac(t, top) * H}
              />
            ))}
            {names.map((name) => {
              const colour = levelColor(name);
              return (
                <path
                  key={name}
                  className={[
                    "nps-line",
                    name === hardest ? "nps-line-hardest" : "",
                    colour ? "" : "nps-line-plain",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  data-difficulty={name}
                  d={line(nps[name] ?? [], top, duration)}
                  fill="none"
                  stroke={colour}
                />
              );
            })}
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
            {audioUrl && selection && (
              <Playhead src={audioUrl} selection={selection} duration={duration} height={H} />
            )}
            {live && (
              <>
                <Handle
                  edge="start"
                  seconds={live.start_s}
                  duration={duration}
                  onDown={beginEdge("start")}
                  onStep={onStep}
                  onFocus={() => setFocus("start")}
                  onBlur={() => setFocus(null)}
                />
                <Handle
                  edge="end"
                  seconds={live.end_s}
                  duration={duration}
                  onDown={beginEdge("end")}
                  onStep={onStep}
                  onFocus={() => setFocus("end")}
                  onBlur={() => setFocus(null)}
                />
              </>
            )}
          </svg>
          {audioUrl && selection && (
            <PlayButton src={audioUrl} selection={selection} duration={duration} />
          )}
        </div>
        <div className="nps-under">
          <TimeAxis duration={duration} />
          {selection && (
            <MoveButtons
              selection={live ?? selection}
              duration={duration}
              canShift={canShift}
              onShiftStep={onShiftStep}
            />
          )}
        </div>
      </div>
      <Legend names={names} />
      <p className="nps-hover" aria-live="polite">
        {shown === null ? "" : hoverText(shown, nps, sections)}
      </p>
    </div>
  );
}
