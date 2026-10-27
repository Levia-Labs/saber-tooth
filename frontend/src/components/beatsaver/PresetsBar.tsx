import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { bsKeys, deletePreset, savePreset, usePresets, type BsPreset } from "../../api/beatsaver";
import { errorMessage } from "../../api/client";
import { presetFilters, stateFromPreset, type BsState } from "../../lib/bsfilters";
import { BS_TIPS } from "../../lib/bstips";
import { Icon } from "../icons";
import { Tip } from "../Tip";

interface Props {
  state: BsState;
  onApply: (next: BsState) => void;
}

const same = (a: Record<string, string>, b: Record<string, string>) =>
  JSON.stringify(Object.entries(a).sort()) === JSON.stringify(Object.entries(b).sort());

/** Seeded presets come first; the rest keep the order the API gives. */
export function orderPresets(list: BsPreset[]): BsPreset[] {
  return [...list.filter((p) => p.seeded), ...list.filter((p) => !p.seeded)];
}

function SavePreset({ state }: { state: BsState }) {
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const save = useMutation({
    mutationFn: () => savePreset(name.trim(), presetFilters(state)),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: bsKeys.presets });
      setOpen(false);
      setName("");
    },
  });
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Tip text={BS_TIPS.savePreset}>
        <Dialog.Trigger className="btn plain preset-save">
          <Icon name="bookmark" />
          <span>Save current filters</span>
        </Dialog.Trigger>
      </Tip>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content className="modal" aria-describedby={undefined}>
          <Dialog.Title>Save current filters</Dialog.Title>
          <form
            className="filter-body"
            onSubmit={(e) => {
              e.preventDefault();
              if (name.trim()) save.mutate();
            }}
          >
            <label htmlFor="preset-name">Name</label>
            <input
              id="preset-name"
              type="text"
              value={name}
              maxLength={60}
              autoComplete="off"
              onChange={(e) => setName(e.target.value)}
            />
            {save.isError && <p className="err">{errorMessage(save.error)}</p>}
            <div className="row">
              <Dialog.Close className="btn plain" type="button">
                Cancel
              </Dialog.Close>
              <button
                type="submit"
                className="btn primary"
                disabled={!name.trim() || save.isPending}
              >
                Save
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/** Saved filter sets as chips, the seeded one first, and a button to save the current set. */
export function PresetsBar({ state, onApply }: Props) {
  const client = useQueryClient();
  const presets = usePresets();
  const remove = useMutation({
    mutationFn: (id: BsPreset["id"]) => deletePreset(id),
    onSuccess: () => void client.invalidateQueries({ queryKey: bsKeys.presets }),
  });
  const current = presetFilters(state);
  return (
    <div className="presets" role="group" aria-label="Saved filters">
      {orderPresets(presets.data ?? []).map((p) => {
        const active = same(presetFilters(stateFromPreset(p.filters)), current);
        return (
          <span key={p.id} className={`preset${active ? " active" : ""}`}>
            <Tip text={BS_TIPS.applyPreset}>
              <button
                type="button"
                className="preset-apply"
                aria-pressed={active}
                onClick={() => onApply(stateFromPreset(p.filters))}
              >
                {p.name}
              </button>
            </Tip>
            {!p.seeded && (
              <Tip text={BS_TIPS.deletePreset}>
                <button type="button" className="preset-remove" onClick={() => remove.mutate(p.id)}>
                  <Icon name="reject" />
                  <span className="sr">{`Delete saved filters ${p.name}`}</span>
                </button>
              </Tip>
            )}
          </span>
        );
      })}
      {presets.isError && <span className="err">Could not load saved filters.</span>}
      <SavePreset state={state} />
    </div>
  );
}
