import { useState, type FormEvent } from "react";
import { useSaveSettings, type SettingsView } from "../../api/settings";
import { mmss, parseMmss } from "../../lib/cropauto";
import { Alert } from "../Alert";

/** The shortest song, as mm:ss, that a map must exceed to be offered a crop. */
export function CropLength({ settings }: { settings: SettingsView }) {
  const saved = mmss(settings.crop_min_length_s);
  const { mutate, isPending, isError, error } = useSaveSettings();
  const [typed, setTyped] = useState<string | null>(null);
  const value = typed ?? saved;
  const seconds = parseMmss(value);
  const invalid = typed !== null && seconds === null;
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (seconds !== null)
      mutate({ crop_min_length_s: seconds }, { onSuccess: () => setTyped(null) });
  };
  return (
    <form className="settings-folder" onSubmit={submit}>
      <label htmlFor="crop-min-length">Qualified for crop</label>
      <div className="settings-folder-row">
        <input
          id="crop-min-length"
          type="text"
          inputMode="numeric"
          className="settings-input"
          placeholder="mm:ss"
          pattern="[0-9]{1,3}:[0-5][0-9]"
          maxLength={6}
          spellCheck={false}
          autoComplete="off"
          aria-invalid={invalid}
          value={value}
          onChange={(e) => setTyped(e.target.value)}
        />
        <button
          type="submit"
          className="btn"
          disabled={isPending || seconds === null || value.trim() === saved}
        >
          Save length
        </button>
      </div>
      <p className="settings-hint">
        A good map longer than this shows as qualified for a crop. Enter minutes and seconds, for
        example 2:30.
      </p>
      {invalid && <p className="settings-hint">Use the form mm:ss, with seconds from 00 to 59.</p>}
      {isError && <Alert variant="danger" title="Length not saved" message={error.message} />}
    </form>
  );
}
