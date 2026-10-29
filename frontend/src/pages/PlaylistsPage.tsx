import { useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { errorMessage } from "../api/client";
import {
  createPlaylist,
  deletePlaylist,
  exportPlaylist,
  getPlaylist,
  playlistKeys,
  updatePlaylist,
  usePlaylistConfig,
  usePlaylists,
  type Playlist,
} from "../api/playlists";
import { useAnnounce } from "../components/Announcer";
import { ActionButton } from "../components/Buttons";
import { LpEditor } from "../components/playlists/LpEditor";
import { LpTable } from "../components/playlists/LpTable";
import { SectionTabs } from "../components/SectionTabs";
import { useDocumentTitle } from "../lib/hooks";
import { draftOf, EMPTY_DRAFT, toInput, type Draft } from "../lib/lpedit";
import {
  filterPlaylists,
  LP_DEFAULT,
  lpFiltered,
  REFRESH_HINT,
  sortPlaylists,
  type LpState,
} from "../lib/lpfilters";

/** `/playlists`: the local playlists table plus the create and edit panel. */
export function PlaylistsPage() {
  useDocumentTitle("Playlists");
  const client = useQueryClient();
  const announce = useAnnounce();
  const lists = usePlaylists();
  const config = usePlaylistConfig();
  const [state, setState] = useState<LpState>(LP_DEFAULT);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [editing, setEditing] = useState<Playlist | null>(null);
  const [busy, setBusy] = useState(false);
  const all = useMemo(() => lists.data?.items ?? [], [lists.data]);
  const rows = useMemo(() => sortPlaylists(filterPlaylists(all, state), state), [all, state]);
  const exportEnabled = config.data?.export_enabled ?? false;
  const fail = (title: string, err: unknown) =>
    announce({ variant: "danger", title, message: errorMessage(err) });
  const refresh = () => client.invalidateQueries({ queryKey: playlistKeys.all });

  const doExport = async (p: Playlist) => {
    try {
      const out = await exportPlaylist(p.id, p.folder);
      announce({
        variant: "success",
        title: `Exported ${p.title}`,
        message: `${out.relative}. ${REFRESH_HINT}`,
      });
      await refresh();
    } catch (err) {
      fail(`Export ${p.title}`, err);
    }
  };
  const edit = async (p: Playlist) => {
    try {
      setDraft(draftOf(await getPlaylist(p.id)));
      setEditing(p);
    } catch (err) {
      fail(`Open ${p.title}`, err);
    }
  };
  const save = async (exportAfter: boolean) => {
    if (!draft) return;
    setBusy(true);
    try {
      const body = toInput(draft);
      const saved = editing ? await updatePlaylist(editing.id, body) : await createPlaylist(body);
      announce({ variant: "success", title: `Saved ${saved.title}` });
      if (exportAfter) await doExport(saved);
      await refresh();
      setDraft(null);
      setEditing(null);
    } catch (err) {
      fail("Save playlist", err);
    } finally {
      setBusy(false);
    }
  };
  const remove = async (p: Playlist) => {
    try {
      await deletePlaylist(p.id);
      await refresh();
    } catch (err) {
      fail(`Delete ${p.title}`, err);
    }
  };
  const empty =
    all.length > 0 && lpFiltered(state) ? (
      <p className="jobs-empty">
        No playlists match the filters.{" "}
        <ActionButton
          icon="filter-x"
          label="Clear filters"
          tip="Show every playlist again"
          text
          onClick={() => setState({ ...LP_DEFAULT, sort: state.sort, ascending: state.ascending })}
        />
      </p>
    ) : (
      <p className="jobs-empty">{lists.isPending ? "Loading playlists." : "No playlists yet."}</p>
    );
  return (
    <section className="library jobs lp" aria-labelledby="playlists-heading">
      <div className="lib-bar">
        <div className="lib-title">
          <SectionTabs active="playlists" heading="Playlists" headingId="playlists-heading" />
        </div>
        <ActionButton
          icon="tag-plus"
          text
          variant="primary"
          label="New playlist"
          tip="Create a playlist"
          onClick={() => {
            setEditing(null);
            setDraft(EMPTY_DRAFT);
          }}
        />
      </div>
      {draft && (
        <LpEditor
          draft={draft}
          editing={editing}
          exportEnabled={exportEnabled}
          busy={busy}
          onChange={setDraft}
          onSave={(x) => void save(x)}
          onCancel={() => {
            setDraft(null);
            setEditing(null);
          }}
          onError={(m) => announce({ variant: "danger", title: "Playlist", message: m })}
        />
      )}
      <LpTable
        rows={rows}
        all={all}
        state={state}
        update={(patch) => setState((s) => ({ ...s, ...patch }))}
        exportEnabled={exportEnabled}
        onEdit={(p) => void edit(p)}
        onExport={(p) => void doExport(p)}
        onDelete={(p) => void remove(p)}
        empty={empty}
      />
      <p className="lp-hint" role="note">
        {REFRESH_HINT}
      </p>
    </section>
  );
}
