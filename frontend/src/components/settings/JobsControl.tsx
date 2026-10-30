import { useEffect, useState } from "react";
import { useSaveSettings, type SettingsView } from "../../api/settings";
import { clampJobs } from "../../lib/settingsfmt";
import { Alert } from "../Alert";

export const SAVE_DELAY_MS = 300;

/** The cap on concurrent fix and scan jobs: a slider with step buttons, saved shortly after the last change. */
export function JobsControl({ settings }: { settings: SettingsView }) {
  const { mutate, isError, error } = useSaveSettings();
  const saved = settings.max_concurrent_jobs;
  const max = Math.max(settings.recommended_max, saved);
  const [draft, setDraft] = useState<number | null>(null);
  const value = draft ?? saved;
  const locked = max <= 1;

  useEffect(() => {
    if (draft === null || draft === saved) return;
    const timer = setTimeout(
      () => mutate({ max_concurrent_jobs: draft }, { onSettled: () => setDraft(null) }),
      SAVE_DELAY_MS,
    );
    return () => clearTimeout(timer);
  }, [draft, saved, mutate]);

  const set = (next: number) => setDraft(clampJobs(next, max));
  return (
    <div className="settings-jobs">
      <label htmlFor="jobs-cap">Concurrent fix and scan jobs</label>
      <div className="settings-stepper">
        <button
          type="button"
          className="btn"
          aria-label="Fewer jobs at once"
          disabled={locked || value <= 1}
          onClick={() => set(value - 1)}
        >
          −
        </button>
        <input
          id="jobs-cap"
          type="range"
          min={1}
          max={max}
          step={1}
          value={value}
          disabled={locked}
          onChange={(e) => set(Number(e.target.value))}
        />
        <button
          type="button"
          className="btn"
          aria-label="More jobs at once"
          disabled={locked || value >= max}
          onClick={() => set(value + 1)}
        >
          +
        </button>
        <output className="settings-value" htmlFor="jobs-cap">
          {value}
        </output>
      </div>
      <p className="settings-hint">
        Recommended maximum: {settings.recommended_max}. A change applies to jobs that start
        afterwards; running jobs finish as they are.
      </p>
      {isError && <Alert variant="danger" title="Could not save" message={error.message} />}
    </div>
  );
}
