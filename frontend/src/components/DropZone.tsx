import { useId, useRef, useState, type DragEvent, type KeyboardEvent } from "react";
import { AUDIO_ACCEPT, AUDIO_HINT, isAudioFile } from "../lib/generate";
import { Icon } from "./icons";

interface Props {
  file: File | null;
  onFile: (file: File | null) => void;
  /** Called with a plain-words reason when a dropped or picked file is not audio. */
  onRefuse: (message: string) => void;
  disabled?: boolean;
}

/** Drop target and keyboard-reachable picker for one audio file. */
export function DropZone({ file, onFile, onRefuse, disabled = false }: Props) {
  const [over, setOver] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const hintId = useId();

  const take = (picked: File | undefined) => {
    if (!picked) return;
    if (!isAudioFile(picked)) {
      onRefuse(`${picked.name} is not an audio file. Use ${AUDIO_HINT}.`);
      return;
    }
    onFile(picked);
  };
  const open = () => {
    if (!disabled) input.current?.click();
  };
  const onKey = (e: KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      open();
    }
  };
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    if (!disabled) take(e.dataTransfer.files[0]);
  };

  return (
    <div className="drop-wrap">
      <div
        className={over ? "drop-zone drop-over" : "drop-zone"}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled}
        aria-describedby={hintId}
        data-over={over}
        onClick={open}
        onKeyDown={onKey}
        onDragEnter={(e) => {
          e.preventDefault();
          if (!disabled) setOver(true);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={onDrop}
      >
        <Icon name="upload" />
        <span className="drop-main">
          {file ? file.name : "Drop an audio file here, or click to choose one"}
        </span>
        <span id={hintId} className="drop-hint">
          {file ? "Click to choose a different file." : `Audio only: ${AUDIO_HINT}.`}
        </span>
      </div>
      <input
        ref={input}
        className="sr-only"
        type="file"
        accept={AUDIO_ACCEPT}
        aria-label="Audio file"
        tabIndex={-1}
        disabled={disabled}
        onChange={(e) => {
          take(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      {file && !disabled && (
        <button type="button" className="drop-clear" onClick={() => onFile(null)}>
          Remove file
        </button>
      )}
    </div>
  );
}
