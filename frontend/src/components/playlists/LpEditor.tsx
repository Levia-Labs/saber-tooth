import { useRef, useState } from "react";
import type { Playlist, SongPick } from "../../api/playlists";
import { addPicks, readCover, type Draft, type DraftSong } from "../../lib/lpedit";
import { exportHint, REFRESH_HINT } from "../../lib/lpfilters";
import { Box } from "../beatsaver/Box";
import { ActionButton } from "../Buttons";
import { Cover } from "../Chips";
import { LpSongPicker } from "./LpSongPicker";

interface Props {
  draft: Draft;
  /** The playlist being edited; null while creating. */
  editing: Playlist | null;
  exportEnabled: boolean;
  busy: boolean;
  onChange: (draft: Draft) => void;
  onSave: (exportAfter: boolean) => void;
  onCancel: () => void;
  onError: (message: string) => void;
}

function Songs({ draft, onChange }: Pick<Props, "draft" | "onChange">) {
  const remove = (i: number) =>
    onChange({ ...draft, songs: draft.songs.filter((_, k) => k !== i) });
  const asCover = (s: DraftSong) =>
    s.map_id && onChange({ ...draft, cover: { map_id: s.map_id }, coverUrl: s.cover_url });
  return (
    <ol className="lp-list lp-chosen" aria-label="Songs in the playlist">
      {draft.songs.length === 0 && <li className="lp-sub">No songs yet.</li>}
      {draft.songs.map((s, i) => (
        <li key={s.map_id ?? s.hash ?? i} className={s.missing ? "lp-gone" : undefined}>
          <Cover url={s.cover_url} />
          <span className="lp-song-name">
            {s.song_name || s.hash}
            <span className="lp-sub">
              {s.mapper}
              {s.missing && " · missing: no installed map matches"}
            </span>
          </span>
          {s.map_id && (
            <ActionButton
              icon="library"
              label={`Use ${s.song_name} as cover`}
              tip="Use this map's cover for the playlist"
              onClick={() => asCover(s)}
            />
          )}
          <ActionButton
            icon="trash"
            label={`Remove ${s.song_name}`}
            tip="Remove from the playlist"
            onClick={() => remove(i)}
          />
        </li>
      ))}
    </ol>
  );
}

/** Create or edit one playlist: details, cover, songs and the export settings. */
export function LpEditor(props: Props) {
  const { draft, editing, exportEnabled, busy, onChange, onSave, onCancel, onError } = props;
  const file = useRef<HTMLInputElement>(null);
  const [picked, setPicked] = useState(0);
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    onChange({ ...draft, [key]: value });
  const upload = async (f: File | undefined) => {
    if (!f) return;
    const read = await readCover(f);
    if (typeof read === "string") return onError(read);
    onChange({ ...draft, cover: { data: read.data }, coverUrl: read.url });
  };
  const chosen = new Set(draft.songs.map((s) => s.map_id).filter((m): m is string => !!m));
  const add = (picks: SongPick[]) => {
    setPicked((n) => n + picks.length);
    onChange({ ...draft, songs: addPicks(draft.songs, picks) });
  };
  return (
    <section className="lp-editor" aria-label={editing ? "Edit playlist" : "New playlist"}>
      <h2 className="lp-heading">{editing ? `Edit ${editing.title}` : "New playlist"}</h2>
      <div className="lp-fields">
        <label>
          Name
          <input
            className="input"
            value={draft.title}
            onChange={(e) => set("title", e.target.value)}
          />
        </label>
        <label>
          Author
          <input
            className="input"
            value={draft.author}
            placeholder="saber-tooth"
            onChange={(e) => set("author", e.target.value)}
          />
        </label>
        <label className="lp-wide">
          Description
          <textarea
            className="input"
            rows={2}
            value={draft.description}
            onChange={(e) => set("description", e.target.value)}
          />
        </label>
        <div className="lp-cover">
          <Cover url={draft.coverUrl} big />
          <input
            ref={file}
            type="file"
            accept="image/png,image/jpeg"
            aria-label="Upload a cover"
            hidden
            onChange={(e) => void upload(e.target.files?.[0])}
          />
          <ActionButton
            icon="upload"
            text
            label="Upload cover"
            tip="Upload a PNG or JPEG cover"
            onClick={() => file.current?.click()}
          />
          {draft.coverUrl && (
            <ActionButton
              icon="reject"
              text
              label="Remove cover"
              tip="Remove the cover"
              onClick={() => onChange({ ...draft, cover: { clear: true }, coverUrl: null })}
            />
          )}
        </div>
      </div>
      <h3 className="lp-heading">Songs ({draft.songs.length})</h3>
      <Songs draft={draft} onChange={onChange} />
      <p className="lp-sub" aria-live="polite">
        {picked > 0 && `${picked} added from the pickers.`}
      </p>
      <LpSongPicker chosen={chosen} onAdd={add} onError={onError} />
      <h3 className="lp-heading">Export</h3>
      <div className="lp-fields">
        <label>
          Subfolder
          <input
            className="input"
            value={draft.folder}
            placeholder="saber-tooth"
            onChange={(e) => set("folder", e.target.value)}
          />
          <span className="lp-sub">Written to {exportHint(draft.folder)}</span>
        </label>
        <Box id="lp-sync" checked={draft.sync} onToggle={() => set("sync", !draft.sync)}>
          Keep in sync (PlaylistManager refreshes it from this server)
        </Box>
      </div>
      <p className="lp-hint" role="note">
        {REFRESH_HINT}
      </p>
      <div className="lp-buttons">
        <ActionButton
          icon="ok"
          text
          variant="primary"
          label="Save"
          tip="Save the playlist"
          disabled={busy || !draft.title.trim()}
          onClick={() => onSave(false)}
        />
        <ActionButton
          icon="download"
          text
          label="Save and export"
          tip={exportEnabled ? "Save and write the .bplist" : "Playlist export is not configured"}
          disabled={busy || !draft.title.trim() || !exportEnabled}
          onClick={() => onSave(true)}
        />
        <ActionButton icon="back" text label="Cancel" tip="Discard changes" onClick={onCancel} />
      </div>
    </section>
  );
}
