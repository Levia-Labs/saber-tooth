import { useRef, useState } from "react";
import { errorText } from "../lib/jobtoasts";
import { Icon } from "./icons";

export const MAX_MAP_NAME = 120;

/** The map heading: click it or the pencil to edit; Enter or blur saves, Escape cancels. */
export function MapTitle({
  name,
  onSave,
}: {
  name: string;
  /** Resolves when the rename is stored; a rejection is shown under the field. */
  onSave: (name: string) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(name);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const busy = useRef(false);

  const open = () => {
    setValue(name);
    setError("");
    setEditing(true);
  };
  const cancel = () => {
    busy.current = false;
    setError("");
    setEditing(false);
  };
  const save = async () => {
    if (busy.current) return;
    const next = value.trim();
    if (next === name) return cancel();
    if (!next || next.length > MAX_MAP_NAME) {
      setError(`Enter a name of 1 to ${MAX_MAP_NAME} characters.`);
      return;
    }
    if (/[\\/]/.test(next)) {
      setError("A name cannot contain / or \\.");
      return;
    }
    busy.current = true;
    setSaving(true);
    setError("");
    try {
      await onSave(next);
      setEditing(false);
    } catch (err) {
      setError(errorText(err));
    } finally {
      busy.current = false;
      setSaving(false);
    }
  };

  return (
    <h1 tabIndex={-1} data-page-heading className="map-title">
      {editing ? (
        <>
          <input
            className="map-title-input"
            type="text"
            value={value}
            maxLength={MAX_MAP_NAME}
            ref={(el) => el?.focus()}
            aria-label="Map name"
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? "map-title-error" : undefined}
            readOnly={saving}
            onFocus={(e) => e.currentTarget.select()}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void save();
              } else if (e.key === "Escape") {
                e.preventDefault();
                cancel();
              }
            }}
            onBlur={() => void save()}
          />
          {saving && (
            <span role="status" aria-label="Saving the map name" className="map-title-busy">
              <Icon name="spinner" />
            </span>
          )}
          {error && (
            <span id="map-title-error" role="alert" className="err map-title-error">
              {error}
            </span>
          )}
        </>
      ) : (
        <>
          <button
            type="button"
            className="map-title-text"
            aria-label={`Rename map: ${name}`}
            onClick={open}
          >
            {name}
          </button>
          <button
            type="button"
            className="btn plain icon map-title-edit"
            aria-label="Edit map name"
            title="Rename"
            onClick={open}
          >
            <Icon name="pencil" />
          </button>
        </>
      )}
    </h1>
  );
}
