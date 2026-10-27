// One audio preview at a time: starting a preview stops the one already playing.
let current: { audio: HTMLAudioElement; stop: () => void } | null = null;

export function claimPreview(audio: HTMLAudioElement, stop: () => void): void {
  if (current && current.audio !== audio) current.stop();
  current = { audio, stop };
}

export function releasePreview(audio: HTMLAudioElement): void {
  if (current?.audio === audio) current = null;
}

/** A fresh audio element that calls `onEnd` when it ends or fails. */
export function createPreview(url: string, onEnd: () => void): HTMLAudioElement {
  const audio = new Audio(url);
  audio.onended = onEnd;
  audio.onerror = onEnd;
  return audio;
}
