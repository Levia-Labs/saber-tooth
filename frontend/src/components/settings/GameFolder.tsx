import { useState, type FormEvent } from "react";
import { useSaveSettings, useSettings } from "../../api/settings";
import { Alert } from "../Alert";

/** The game folder as the service sees it (inside the container): saved as a setting. */
export function GameFolder() {
  const saved = useSettings().data?.game_dir ?? "";
  const { mutate, isPending, isError, error } = useSaveSettings();
  const [typed, setTyped] = useState<string | null>(null);
  const value = typed ?? saved;
  const submit = (e: FormEvent) => {
    e.preventDefault();
    mutate({ game_dir: value.trim() }, { onSuccess: () => setTyped(null) });
  };
  return (
    <form className="settings-folder" onSubmit={submit}>
      <label htmlFor="game-folder">Game folder</label>
      <div className="settings-folder-row">
        <input
          id="game-folder"
          type="text"
          className="settings-input"
          placeholder="/game"
          spellCheck={false}
          autoComplete="off"
          value={value}
          onChange={(e) => setTyped(e.target.value)}
        />
        <button type="submit" className="btn" disabled={isPending || value.trim() === saved}>
          Save folder
        </button>
      </div>
      <p className="settings-hint">
        The path inside the container. Leave it empty to use the mounted folder.
      </p>
      {isError && <Alert variant="danger" title="Folder not saved" message={error.message} />}
    </form>
  );
}
