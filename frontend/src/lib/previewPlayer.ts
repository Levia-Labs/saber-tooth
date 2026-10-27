// App-wide audio preview controller: one shared audio element, so starting a preview stops the last.
import { useCallback, useSyncExternalStore } from "react";

interface Snapshot {
  src: string | null;
  playing: boolean;
  /** Played fraction of the current preview, 0 to 1. */
  progress: number;
}

const IDLE: Snapshot = { src: null, playing: false, progress: 0 };
let snap: Snapshot = IDLE;
let audio: HTMLAudioElement | null = null;
const listeners = new Set<() => void>();

function publish(next: Snapshot): void {
  snap = next;
  for (const l of listeners) l();
}

function element(): HTMLAudioElement {
  if (audio) return audio;
  const el = new Audio();
  el.addEventListener("timeupdate", () => {
    const d = el.duration;
    if (snap.playing && d > 0) publish({ ...snap, progress: Math.min(1, el.currentTime / d) });
  });
  el.addEventListener("ended", () => stopPreview());
  el.addEventListener("error", () => stopPreview());
  audio = el;
  return el;
}

/** Stops whatever is playing. */
export function stopPreview(): void {
  audio?.pause();
  if (snap !== IDLE) publish(IDLE);
}

/** Starts `src`, replacing any other preview; a second call for the same `src` pauses it. */
export function togglePreview(src: string): void {
  if (snap.playing && snap.src === src) {
    stopPreview();
    return;
  }
  const el = element();
  el.pause();
  el.src = src;
  publish({ src, playing: true, progress: 0 });
  void Promise.resolve(el.play()).catch(() => {
    if (snap.src === src) stopPreview();
  });
}

const subscribe = (l: () => void) => {
  listeners.add(l);
  return () => void listeners.delete(l);
};

/** State of the preview for `src` (when absent, never playing) plus a toggle. */
export function usePreviewPlayer(src?: string | null) {
  const s = useSyncExternalStore(subscribe, () => snap);
  const mine = Boolean(src) && s.src === src;
  const toggle = useCallback(() => {
    if (src) togglePreview(src);
  }, [src]);
  return { playing: mine && s.playing, progress: mine ? s.progress : 0, toggle };
}
