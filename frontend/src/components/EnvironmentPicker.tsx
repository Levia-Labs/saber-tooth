import * as Dialog from "@radix-ui/react-dialog";
import { useQuery } from "@tanstack/react-query";
import { useId, useState } from "react";
import { getEnvironments } from "../api/client";
import { retry } from "../api/queries";
import { formatEnvironment } from "../lib/environment";

interface Props {
  /** The map's current environment; preselected. */
  current: string;
  /** True while the map has a job running or the relight job is in flight. */
  busy: boolean;
  /** Called after the user confirms a different environment. */
  onPick: (environment: string) => void;
}

/** Choose the vanilla environment for a relit copy; changing it asks first, then starts the job. */
export function EnvironmentPicker({ current, busy, onPick }: Props) {
  const id = useId();
  const [pending, setPending] = useState<string | null>(null);
  const list = useQuery({
    queryKey: ["lightshow", "environments"],
    queryFn: getEnvironments,
    retry,
    staleTime: 60_000,
  });
  const names = list.data?.environments ?? [];
  const options = current && !names.includes(current) ? [current, ...names] : names;
  if (options.length === 0) return current ? <span>{formatEnvironment(current)}</span> : null;
  return (
    <>
      <label className="env-pick" htmlFor={id}>
        <span className="env-pick-label">Environment</span>
        <select
          id={id}
          value={current}
          disabled={busy}
          onChange={(e) => e.target.value !== current && setPending(e.target.value)}
        >
          {!current && <option value="" />}
          {options.map((name) => (
            <option key={name} value={name} disabled={!names.includes(name)}>
              {formatEnvironment(name)}
            </option>
          ))}
        </select>
      </label>
      <Dialog.Root open={pending !== null} onOpenChange={(open) => !open && setPending(null)}>
        <Dialog.Portal>
          <Dialog.Overlay className="overlay" />
          <Dialog.Content className="modal">
            <Dialog.Title>Relight in {pending ? formatEnvironment(pending) : ""}?</Dialog.Title>
            <Dialog.Description>
              Writes a copy of this map with that environment and a new lightshow made from the
              learned templates. The original stays as it is.
            </Dialog.Description>
            <div className="row">
              <Dialog.Close className="btn plain">Cancel</Dialog.Close>
              <button
                type="button"
                className="btn primary"
                onClick={() => {
                  const next = pending;
                  setPending(null);
                  if (next) onPick(next);
                }}
              >
                Relight
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}
