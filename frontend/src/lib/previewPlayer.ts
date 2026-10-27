// App-wide audio preview controller: one shared audio element, so starting a preview stops the last.
import { useCallback, useSyncExternalStore } from "react";

interface Snapshot {
  src: string | null;
  playing: boolean;
  /** Played fraction of the current preview, 0 to 1. */
  progress: number;
}

/** Where a preview starts and how long it plays; without it the whole file plays. */
export interface PreviewWindow {
  /** Second to seek to on play. */
  start: number;
  /** Seconds to play before stopping by itself. */
  length: number;
}

/** Length of a preview clip when the caller gives a start second only. */
export const PREVIEW_SECONDS = 15;

const IDLE: Snapshot = { src: null, playing: false, progress: 0 };
let window_: PreviewWindow | null = null;
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
    if (!snap.playing) return;
    if (window_) {
      const played = el.currentTime - window_.start;
      if (played >= window_.length) return stopPreview();
      publish({ ...snap, progress: Math.max(0, Math.min(1, played / window_.length)) });
      return;
    }
    const d = el.duration;
    if (d > 0) publish({ ...snap, progress: Math.min(1, el.currentTime / d) });
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
export function togglePreview(src: string, clip?: PreviewWindow): void {
  if (snap.playing && snap.src === src) {
    stopPreview();
    return;
  }
  const el = element();
  el.pause();
  el.src = src;
  window_ = clip && clip.start > 0 ? clip : clip ? { ...clip, start: 0 } : null;
  if (window_ && window_.start > 0) {
    const start = window_.start;
    // Seeking needs the metadata; the server answers Range requests, so no full download.
    el.addEventListener(
      "loadedmetadata",
      () => {
        if (snap.src === src) el.currentTime = start;
      },
      { once: true },
    );
  }
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
export function usePreviewPlayer(src?: string | null, clip?: PreviewWindow) {
  const s = useSyncExternalStore(subscribe, () => snap);
  const mine = Boolean(src) && s.src === src;
  const toggle = useCallback(() => {
    if (src) togglePreview(src, clip);
  }, [src, clip]);
  return { playing: mine && s.playing, progress: mine ? s.progress : 0, toggle };
}
