import { useEffect, useRef, useState } from "react";
import { BS_TIPS } from "../../lib/bstips";
import { claimPreview, createPreview, releasePreview } from "../../lib/preview";
import { Icon } from "../icons";
import { Tip } from "../Tip";

/** Plays one preview at a time; starting another stops the first. */
export function PreviewButton({ url, name }: { url: string; name: string }) {
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(
    () => () => {
      const el = audioRef.current;
      if (!el) return;
      el.pause();
      releasePreview(el);
    },
    [],
  );

  const toggle = () => {
    const audio = audioRef.current;
    if (audio && playing) {
      audio.pause();
      setPlaying(false);
      return;
    }
    const el = audio ?? createPreview(url, () => setPlaying(false));
    audioRef.current = el;
    claimPreview(el, () => {
      el.pause();
      setPlaying(false);
    });
    void el.play().then(
      () => setPlaying(true),
      () => setPlaying(false),
    );
  };

  return (
    <Tip text={playing ? BS_TIPS.stopPreview : BS_TIPS.preview}>
      <button type="button" className="btn icon" aria-pressed={playing} onClick={toggle}>
        <Icon name={playing ? "stop" : "play"} />
        <span className="sr">{playing ? `Stop preview of ${name}` : `Preview ${name}`}</span>
        <span className="short" aria-hidden="true">
          {playing ? "Stop" : "Preview"}
        </span>
      </button>
    </Tip>
  );
}
