import { useEffect, useMemo, useRef } from "react";
import { useInRouterContext, useLocation } from "react-router";
import { PREVIEW_SECONDS, stopPreview, usePreviewPlayer } from "../lib/previewPlayer";
import { Icon } from "./icons";
import { Tip } from "./Tip";

const R = 15;
const CIRC = 2 * Math.PI * R;

/** Stops the preview when the route changes. */
function StopOnRoute() {
  const { pathname } = useLocation();
  const first = useRef(pathname);
  useEffect(() => {
    if (first.current !== pathname) {
      first.current = pathname;
      stopPreview();
    }
  }, [pathname]);
  return null;
}

interface Props {
  /** Audio address; the button renders nothing without one. */
  src?: string | null;
  title: string;
  /** Second the preview starts at; it then plays for 15 seconds. Omitted: the whole file. */
  start?: number | null;
}

/** Play/pause toggle with a thin progress ring; shared by BeatSaver and the Library. */
export function PreviewButton({ src, title, start }: Props) {
  const clip = useMemo(
    () => (start == null ? undefined : { start: Math.max(0, start), length: PREVIEW_SECONDS }),
    [start],
  );
  const { playing, progress, toggle } = usePreviewPlayer(src, clip);
  const inRouter = useInRouterContext();
  if (!src) return null;
  return (
    <>
      {inRouter && <StopOnRoute />}
      <Tip text="Play a short preview">
        <button
          type="button"
          className="btn icon preview-btn"
          aria-pressed={playing}
          aria-label={playing ? "Pause preview" : `Play preview of ${title}`}
          onClick={toggle}
        >
          {playing && (
            <svg className="preview-ring" viewBox="0 0 36 36" aria-hidden="true">
              <circle
                cx="18"
                cy="18"
                r={R}
                strokeDasharray={CIRC}
                strokeDashoffset={CIRC * (1 - progress)}
                data-progress={progress}
              />
            </svg>
          )}
          <Icon name={playing ? "stop" : "play"} />
        </button>
      </Tip>
    </>
  );
}
