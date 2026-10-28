import { useState, type MouseEvent, type PointerEvent } from "react";
import type { CropSection } from "../api/types";
import { npsTicks, yFrac } from "../lib/axis";
import { clampStart, clock, sectionAt, secondsAt, type Span } from "../lib/crop";
import { levelColor } from "../lib/levels";
import { Legend, TimeAxis, YAxis } from "./ChartAxes";
import { H, Handle, W, capture, px } from "./ChartHandles";
import { CueHandle, PlayButton, Playhead, usePlayback } from "./ChartPlayback";

export type Edge = "start" | "end";
export type { Span };

interface Props {
  nps: Record<string, number[]>;
  hardest: string;
  sections: CropSection[];
  duration: number;
  selection: Span | null;
  faint: Span[];
  /** A handle moved to this second while being dragged. */
  onMove: (edge: Edge, seconds: number) => void;
  /** An arrow key on a handle: one nudge in `dir`; `big` when Shift is held. */
  onStep: (edge: Edge, dir: 1 | -1, big: boolean) => void;
  /** The whole window was dragged and released with its start at this second. */
  onShift: (startSeconds: number) => void;
  /** A section other than the selection was double-clicked: move the selection to start there. */
  onJump: (sectionStartSeconds: number) => void;
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

/** Notes per second across the song: one coloured line per difficulty, sections as bands, axes, the
 * chosen window with two freely draggable, keyboard-nudged edges, a body that drags as a whole, and
 * a playhead with a draggable cue. */
export function NpsChart({
  nps,
  hardest,
  sections,
  duration,
  selection,
  faint,
  onMove,
  onStep,
  onShift,
  onJump,
  audioUrl,
}: Props) {
  const [hover, setHover] = useState<number | null>(null);
  const [drag, setDrag] = useState<Drag | null>(null);
  const [focus, setFocus] = useState<Edge | null>(null);
  const playback = usePlayback(audioUrl, selection);
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
            {audioUrl && selection && <Playhead at={playback.at} duration={duration} height={H} />}
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
          {audioUrl && selection && live && (
            <PlayButton
              playing={playback.playing}
              centre={((live.start_s + live.end_s) / 2 / duration) * 100}
              onPress={playback.press}
            />
          )}
          {audioUrl && selection && (
            <CueHandle
              at={playback.at}
              selection={selection}
              duration={duration}
              onPreview={playback.preview}
              onSeek={playback.seek}
            />
          )}
        </div>
        <div className="nps-under">
          <TimeAxis duration={duration} />
        </div>
      </div>
      <Legend names={names} />
      <p className="nps-hover" aria-live="polite">
        {shown === null ? "" : hoverText(shown, nps, sections)}
      </p>
    </div>
  );
}
