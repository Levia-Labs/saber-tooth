import * as Dialog from "@radix-ui/react-dialog";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { exportPlaylist, type BsMap } from "../../api/beatsaver";
import { errorMessage } from "../../api/client";
import { BS_TIPS } from "../../lib/bstips";
import { plural } from "../../lib/format";
import { Icon } from "../icons";
import { Tip } from "../Tip";
import type { Downloads } from "./downloads";
import type { Selection } from "./selection";

const LIST_CAP = 8;

function Names({ items }: { items: BsMap[] }) {
  const shown = items.slice(0, LIST_CAP);
  return (
    <ul className="confirm-list">
      {shown.map((m) => (
        <li key={m.id}>{m.song || m.name}</li>
      ))}
      {items.length > shown.length && <li>and {items.length - shown.length} more</li>}
    </ul>
  );
}

export const MAX_BATCH = 100;

/** Confirmation that lists what will be downloaded and what is skipped as already installed. */
export function DownloadConfirm(props: {
  items: BsMap[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (ids: string[]) => void;
}) {
  const fresh = props.items.filter((m) => !m.installed);
  const have = props.items.filter((m) => m.installed);
  const batch = fresh.slice(0, MAX_BATCH);
  return (
    <Dialog.Root open={props.open} onOpenChange={props.onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content className="modal" aria-describedby="confirm-desc">
          <Dialog.Title>Download maps</Dialog.Title>
          <p id="confirm-desc">
            {plural(batch.length, "new map")} will be downloaded into your CustomLevels folder.
            {have.length > 0 && ` ${plural(have.length, "map")} already installed will be skipped.`}
            {fresh.length > batch.length &&
              ` Only the first ${MAX_BATCH} go in one batch; repeat for the rest.`}
          </p>
          {fresh.length > 0 && (
            <>
              <h3>New ({fresh.length})</h3>
              <Names items={fresh} />
            </>
          )}
          {have.length > 0 && (
            <>
              <h3>Already installed ({have.length})</h3>
              <Names items={have} />
            </>
          )}
          <div className="row">
            <Dialog.Close className="btn plain">
              <Icon name="reject" />
              <span className="label-hide-mobile">Cancel</span>
            </Dialog.Close>
            <Dialog.Close
              className="btn primary"
              disabled={!batch.length}
              onClick={() => props.onConfirm(batch.map((m) => m.id))}
            >
              <Icon name="download" />
              <span className="label-hide-mobile">{`Download ${batch.length} new`}</span>
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function ExportDialog({ ids }: { ids: string[] }) {
  const [title, setTitle] = useState("Saber Tooth selection");
  const out = useMutation({ mutationFn: () => exportPlaylist(title.trim(), ids) });
  return (
    <Dialog.Root onOpenChange={() => out.reset()}>
      <Tip text={BS_TIPS.export}>
        <Dialog.Trigger className="btn plain">
          <Icon name="playlist" />
          <span className="label-hide-mobile">Export playlist</span>
        </Dialog.Trigger>
      </Tip>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content className="modal" aria-describedby={undefined}>
          <Dialog.Title>Export playlist</Dialog.Title>
          <div className="filter-body">
            <label htmlFor="playlist-title">Playlist name</label>
            <input
              id="playlist-title"
              type="text"
              value={title}
              maxLength={80}
              onChange={(e) => setTitle(e.target.value)}
            />
            {out.isError && <p className="err">{errorMessage(out.error)}</p>}
            {out.data && <p className="ok">Written to: {out.data.path}</p>}
          </div>
          <div className="row">
            <Dialog.Close className="btn plain">
              <Icon name="reject" />
              <span className="label-hide-mobile">Close</span>
            </Dialog.Close>
            <button
              type="button"
              className="btn primary"
              disabled={!title.trim() || out.isPending}
              onClick={() => out.mutate()}
            >
              <Icon name="playlist" />
              <span className="label-hide-mobile">Export {plural(ids.length, "map")}</span>
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

interface Props {
  selection: Selection;
  downloads: Downloads;
  playlistsEnabled: boolean;
}

/** Appears when maps are ticked: Download N, Export playlist (when enabled) and Clear. */
export function SelectionBar({ selection, downloads, playlistsEnabled }: Props) {
  const [open, setOpen] = useState(false);
  const n = selection.items.length;
  if (n === 0) return null;
  return (
    <div className="selection-bar" role="region" aria-label="Selection">
      <span className="count" aria-live="polite">
        {n} selected
      </span>
      <Tip text={BS_TIPS.downloadSelected}>
        <button
          type="button"
          className="btn primary"
          disabled={downloads.runner.busy}
          onClick={() => setOpen(true)}
        >
          <Icon name="download" />
          <span className="label-hide-mobile">{`Download ${n}`}</span>
        </button>
      </Tip>
      <DownloadConfirm
        items={selection.items}
        open={open}
        onOpenChange={setOpen}
        onConfirm={(ids) => {
          void downloads.start(ids);
          selection.clear();
        }}
      />
      {playlistsEnabled && <ExportDialog ids={selection.items.map((m) => m.id)} />}
      <Tip text={BS_TIPS.clearSelection}>
        <button type="button" className="btn plain" onClick={selection.clear}>
          <Icon name="reject" />
          <span className="label-hide-mobile">Clear selection</span>
        </button>
      </Tip>
    </div>
  );
}
