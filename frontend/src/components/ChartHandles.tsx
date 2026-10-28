import type { KeyboardEvent, PointerEvent } from "react";
import { clock } from "../lib/crop";
import type { Edge } from "./NpsChart";

export const W = 1000;
export const H = 160;

export const px = (seconds: number, duration: number): number =>
  duration > 0 ? (seconds / duration) * W : 0;

interface HandleProps {
  edge: Edge;
  seconds: number;
  duration: number;
  onDown: (e: PointerEvent<SVGGElement>) => void;
  onStep: (edge: Edge, dir: 1 | -1, jump: boolean) => void;
  onFocus: () => void;
  onBlur: () => void;
}

/** Route later pointer events to `el` so a drag keeps working outside it. */
export function capture(el: Element | null, id: number): void {
  if (el && "setPointerCapture" in el) el.setPointerCapture(id);
}

/** A draggable edge of the window; arrows nudge it 0.1 s, Shift and arrows 1 s. */
export function Handle({ edge, seconds, duration, onDown, onStep, onFocus, onBlur }: HandleProps) {
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
      onFocus={onFocus}
      onBlur={onBlur}
      onPointerDown={onDown}
    >
      <line x1={x} x2={x} y1={0} y2={H} />
      <rect x={x - 6} y={H / 2 - 14} width={12} height={28} rx={3} />
    </g>
  );
}
