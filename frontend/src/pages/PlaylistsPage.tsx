import { useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { errorMessage } from "../api/client";
import {
  deletePlaylist,
  exportPlaylist,
  playlistKeys,
  usePlaylistConfig,
  usePlaylists,
  type Playlist,
} from "../api/playlists";
import { useAnnounce } from "../components/Announcer";
import { ActionButton, ActionLink } from "../components/Buttons";
import { LpTable } from "../components/playlists/LpTable";
import { SectionTabs } from "../components/SectionTabs";
import { Spinner } from "../components/Spinner";
import { useDocumentTitle } from "../lib/hooks";
import {
  filterPlaylists,
  LP_DEFAULT,
  lpFiltered,
  REFRESH_HINT,
  sortPlaylists,
  type LpState,
} from "../lib/lpfilters";

/** `/playlists`: the local playlists table; a playlist opens on its own page. */
export function PlaylistsPage() {
  useDocumentTitle("Playlists");
  const client = useQueryClient();
  const navigate = useNavigate();
  const announce = useAnnounce();
  const lists = usePlaylists();
  const config = usePlaylistConfig();
  const [state, setState] = useState<LpState>(LP_DEFAULT);
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
      <p className="jobs-empty">
        {lists.isPending ? <Spinner label="Loading playlists" /> : "No playlists yet."}
      </p>
    );
  return (
    <section className="library jobs lp" aria-labelledby="playlists-heading">
      <div className="lib-bar">
        <div className="lib-title">
          <SectionTabs active="playlists" heading="Playlists" headingId="playlists-heading" />
        </div>
        <ActionLink
          icon="plus"
          text
          variant="primary"
          label="New playlist"
          tip="Create a playlist"
          to="/playlists/new"
        />
      </div>
      <LpTable
        rows={rows}
        all={all}
        state={state}
        update={(patch) => setState((s) => ({ ...s, ...patch }))}
        exportEnabled={exportEnabled}
        onEdit={(p) => void navigate(`/playlists/${p.id}`)}
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
