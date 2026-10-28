import { useEffect, useMemo, useRef } from "react";
import { stopPreview, usePreviewPlayer } from "../lib/previewPlayer";
import { Icon } from "./icons";
import type { Span } from "./NpsChart";

const W = 1000;

/** Play or pause the selected section, centred over it; plays through the shared preview player. */
export function PlayButton({
  src,
  selection,
  duration,
}: {
  src: string;
  selection: Span;
  duration: number;
}) {
  const clip = useMemo(
    () => ({ start: selection.start_s, length: selection.end_s - selection.start_s }),
    [selection.start_s, selection.end_s],
  );
  const { playing, toggle } = usePreviewPlayer(src, clip);
  const live = useRef(playing);
  useEffect(() => {
    live.current = playing;
  }, [playing]);
  // A changed selection or a leaving chart ends the playback of the old window.
  useEffect(() => () => void (live.current && stopPreview()), [selection.start_s, selection.end_s]);
  const centre = ((selection.start_s + selection.end_s) / 2 / duration) * 100;
  return (
    <button
      type="button"
      className="btn icon nps-play"
      style={{ left: `${centre}%` }}
      aria-label={playing ? "Pause selected section" : "Play selected section"}
      aria-pressed={playing}
      title={playing ? "Pause" : "Play the selected section"}
      onClick={toggle}
    >
      <Icon name={playing ? "pause" : "play"} />
    </button>
  );
}

/** The line that travels across the selection while it plays; drawn inside the chart svg. */
export function Playhead({
  src,
  selection,
  duration,
  height,
}: {
  src: string;
  selection: Span;
  duration: number;
  height: number;
}) {
  const { playing, progress } = usePreviewPlayer(src);
  if (!playing || !(duration > 0)) return null;
  const at = selection.start_s + progress * (selection.end_s - selection.start_s);
  const x = (at / duration) * W;
  return <line className="nps-playhead" x1={x} x2={x} y1={0} y2={height} />;
}
