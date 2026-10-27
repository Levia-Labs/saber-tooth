import { useEffect, useRef } from "react";
import type { Note, Wall } from "../api/types";
import { drawTimeline } from "../lib/timeline";

const RESIZE_DEBOUNCE_MS = 150;

interface Props {
  label: string;
  before: Note[];
  after: Note[];
  wallsBefore: Wall[];
  wallsAfter: Wall[];
  wallsContext: Wall[];
}

/** Before and after note grids (with walls) drawn on a canvas that redraws on resize. */
export function TimelineCanvas(props: Props) {
  const { label, before, after, wallsBefore, wallsAfter, wallsContext } = props;
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const draw = () =>
      drawTimeline(canvas, before, after, { wallsBefore, wallsAfter, wallsContext });
    draw();
    let timer: ReturnType<typeof setTimeout> | undefined;
    const onResize = () => {
      clearTimeout(timer);
      timer = setTimeout(draw, RESIZE_DEBOUNCE_MS);
    };
    window.addEventListener("resize", onResize);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("resize", onResize);
    };
  }, [before, after, wallsBefore, wallsAfter, wallsContext]);

  return <canvas ref={ref} className="timeline" role="img" aria-label={label} />;
}
