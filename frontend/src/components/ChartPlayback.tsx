import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { NUDGE_BIG_S, NUDGE_S, clock, secondsAt, type Span } from "../lib/crop";
import { stopPreview, togglePreview, usePreviewPlayer } from "../lib/previewPlayer";
import { capture } from "./ChartHandles";
import { Icon } from "./icons";

const W = 1000;
const MIN_CLIP_S = 0.1;

const clamp = (v: number, lo: number, hi: number): number => Math.max(lo, Math.min(hi, v));

/**
 * Playback of the selected window through the shared preview player, with a cue point: where play
 * starts while paused, and the playhead position while playing or being dragged.
 */
export function usePlayback(src: string | null | undefined, selection: Span | null) {
  const start = selection?.start_s ?? 0;
  const end = selection?.end_s ?? 0;
  const [cue, setCue] = useState<number | null>(null);
  const [dragAt, setDragAt] = useState<number | null>(null);
  const from = cue !== null && cue >= start && cue <= end ? cue : start;
  const has = selection !== null;
  const clip = useMemo(
    () => (has ? { start: from, length: Math.max(MIN_CLIP_S, end - from) } : undefined),
    [has, from, end],
  );
  const { playing, progress, toggle } = usePreviewPlayer(src, clip);
  const live = useRef(playing);
  useEffect(() => {
    live.current = playing;
  }, [playing]);
  // A changed selection or a leaving chart ends the playback of the old window.
  useEffect(() => () => void (live.current && stopPreview()), [start, end]);
  const at = dragAt ?? (playing ? from + progress * (end - from) : from);
  return {
    playing,
    at,
    /** Play, or pause and keep the paused position as the next start. */
    press: () => {
      if (playing) setCue(at);
      toggle();
    },
    /** Show the cue at `seconds` while it is dragged; null drops the drag. */
    preview: setDragAt,
    /** Put the cue at `seconds`; a playing preview restarts there. */
    seek: (seconds: number) => {
      setDragAt(null);
      setCue(seconds);
      if (playing && src) {
        stopPreview();
        togglePreview(src, { start: seconds, length: Math.max(MIN_CLIP_S, end - seconds) });
      }
    },
  };
}

/** Play or pause the selected section, centred over it as a bare green icon. */
export function PlayButton({
  playing,
  centre,
  onPress,
}: {
  playing: boolean;
  /** Middle of the selection, in percent of the chart width. */
  centre: number;
  onPress: () => void;
}) {
  return (
    <button
      type="button"
      className="nps-play"
      style={{ left: `${centre}%` }}
      aria-label={playing ? "Pause selected section" : "Play selected section"}
      aria-pressed={playing}
      title={playing ? "Pause" : "Play the selected section"}
      onClick={onPress}
    >
      <Icon name={playing ? "pause" : "play"} filled />
    </button>
  );
}

/** The vertical line at the playback position; drawn inside the chart svg. */
export function Playhead({
  at,
  duration,
  height,
}: {
  at: number;
  duration: number;
  height: number;
}) {
  if (!(duration > 0)) return null;
  const x = (at / duration) * W;
  return <line className="nps-playhead" x1={x} x2={x} y1={0} y2={height} />;
}

interface CueProps {
  at: number;
  selection: Span;
  duration: number;
  onPreview: (seconds: number | null) => void;
  onSeek: (seconds: number) => void;
}

/** The green triangle under the playhead: drag it, or use the arrow keys, to set the position. */
export function CueHandle({ at, selection, duration, onPreview, onSeek }: CueProps) {
  const dragging = useRef(false);
  const inside = (v: number) => clamp(v, selection.start_s, selection.end_s);
  const under = (e: PointerEvent<HTMLElement>): number => {
    const box = e.currentTarget.parentElement?.querySelector("svg")?.getBoundingClientRect();
    return inside(secondsAt(e.clientX, box?.left ?? 0, box?.width ?? 0, duration));
  };
  const onKey = (e: KeyboardEvent) => {
    const dir =
      e.key === "ArrowRight" || e.key === "ArrowUp"
        ? 1
        : e.key === "ArrowLeft" || e.key === "ArrowDown"
          ? -1
          : 0;
    if (dir === 0) return;
    e.preventDefault();
    onSeek(inside(Math.round((at + dir * (e.shiftKey ? NUDGE_BIG_S : NUDGE_S)) * 1000) / 1000));
  };
  return (
    <div
      className="nps-cue"
      role="slider"
      tabIndex={0}
      aria-label="Playback position"
      aria-orientation="horizontal"
      aria-valuemin={Math.round(selection.start_s * 10) / 10}
      aria-valuemax={Math.round(selection.end_s * 10) / 10}
      aria-valuenow={Math.round(at * 10) / 10}
      aria-valuetext={clock(at)}
      style={{ left: `${duration > 0 ? (at / duration) * 100 : 0}%` }}
      onKeyDown={onKey}
      onPointerDown={(e) => {
        capture(e.currentTarget, e.pointerId);
        dragging.current = true;
      }}
      onPointerMove={(e) => {
        if (dragging.current) onPreview(under(e));
      }}
      onPointerUp={(e) => {
        if (!dragging.current) return;
        dragging.current = false;
        onSeek(under(e));
      }}
      onPointerCancel={() => {
        dragging.current = false;
        onPreview(null);
      }}
    >
      <svg viewBox="0 0 16 12" aria-hidden="true" focusable="false">
        <path d="M8 0L16 12H0z" />
      </svg>
    </div>
  );
}
