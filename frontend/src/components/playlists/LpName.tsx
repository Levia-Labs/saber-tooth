import { useRef, useState, type KeyboardEvent } from "react";
import { ActionButton } from "../Buttons";

interface Props {
  value: string;
  onCommit: (name: string) => void;
}

/** The playlist's name as the page title; click it or the pencil to edit in place. */
export function LpName({ value, onCommit }: Props) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(value);
  const settled = useRef(false);
  const open = () => {
    settled.current = false;
    setText(value);
    setEditing(true);
  };
  const finish = (save: boolean) => {
    if (settled.current) return;
    settled.current = true;
    const name = text.trim();
    if (save && name && name !== value) onCommit(name);
    setEditing(false);
  };
  const key = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") finish(true);
    else if (e.key === "Escape") finish(false);
  };
  if (editing) {
    return (
      <h1 className="lp-name-h" tabIndex={-1} data-page-heading>
        <input
          className="lp-name-input"
          aria-label="Playlist name"
          value={text}
          maxLength={120}
          // eslint-disable-next-line jsx-a11y/no-autofocus
          autoFocus
          onChange={(e) => setText(e.target.value)}
          onKeyDown={key}
          onBlur={() => finish(true)}
        />
      </h1>
    );
  }
  return (
    <h1 className="lp-name-h" tabIndex={-1} data-page-heading>
      <button type="button" className="lp-name-text" onClick={open}>
        {value || "Untitled playlist"}
      </button>
      <ActionButton icon="edit" label="Edit name" tip="Edit the playlist name" onClick={open} />
    </h1>
  );
}
