import { useEffect, useRef, useState } from "react";
import { Icon } from "./icons";

export const SEARCH_DEBOUNCE_MS = 250;

interface TextProps {
  q: string;
  /** Accessible name of the text box, e.g. "Title contains". Not shown on screen. */
  label: string;
  /** Short hint inside the empty box, e.g. "Title". */
  placeholder?: string;
  onChange: (q: string, replace: boolean) => void;
}

/** Debounced "contains" text box shared by the Title and Author filters. */
export function TextFilterBody({ q, label, placeholder, onChange }: TextProps) {
  const [text, setText] = useState(q);
  const [emitted, setEmitted] = useState(q);
  const [seen, setSeen] = useState(q);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  // An outside change (clear all, back button) replaces the text; our own debounced echo does not.
  if (q !== seen) {
    setSeen(q);
    if (q !== emitted) {
      setEmitted(q);
      setText(q);
    }
  }
  const pending = useRef<string | null>(null);
  const emit = useRef(onChange);
  useEffect(() => {
    emit.current = onChange;
  }, [onChange]);
  // Closing the popover unmounts this body: send a search typed in the last 250 ms before it goes.
  useEffect(
    () => () => {
      clearTimeout(timer.current);
      if (pending.current !== null) emit.current(pending.current, true);
    },
    [],
  );
  const change = (value: string) => {
    setText(value);
    clearTimeout(timer.current);
    pending.current = value;
    timer.current = setTimeout(() => {
      pending.current = null;
      setEmitted(value);
      onChange(value, true);
    }, SEARCH_DEBOUNCE_MS);
  };
  return (
    <div className="filter-body">
      <div className="field">
        <input
          type="text"
          aria-label={label}
          placeholder={placeholder}
          value={text}
          maxLength={200}
          autoComplete="off"
          onChange={(e) => change(e.target.value)}
        />
        {text && (
          <button
            type="button"
            className="field-clear"
            aria-label="Clear"
            onClick={() => {
              clearTimeout(timer.current);
              pending.current = null;
              setText("");
              setEmitted("");
              onChange("", true);
            }}
          >
            <Icon name="reject" />
          </button>
        )}
      </div>
    </div>
  );
}
