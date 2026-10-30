import { useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { errorMessage, getMap } from "../api/client";
import {
  createPlaylist,
  exportPlaylist,
  playlistKeys,
  updatePlaylist,
  usePlaylist,
  usePlaylistConfig,
  type SongPick,
} from "../api/playlists";
import type { MapItem } from "../api/types";
import { useAnnounce } from "../components/Announcer";
import { Alert } from "../components/Alert";
import { ActionButton } from "../components/Buttons";
import { BackLink } from "../components/BackLink";
import { PlaylistFooter } from "../components/playlists/PlaylistFooter";
import { SectionTabs } from "../components/SectionTabs";
import { backHref, FROM_PARAM } from "../lib/backlink";
import { useOrigin } from "../lib/useBacklink";
import { LpCover } from "../components/playlists/LpCover";
import { LpExport } from "../components/playlists/LpExport";
import { LpName } from "../components/playlists/LpName";
import { LpSongPicker } from "../components/playlists/LpSongPicker";
import { LpSongTable } from "../components/playlists/LpSongTable";
import { useDocumentTitle } from "../lib/hooks";
import { addPicks, draftOf, EMPTY_DRAFT, songId, toInput, type Draft } from "../lib/lpedit";
import { REFRESH_HINT } from "../lib/lpfilters";
import { rowsOf } from "../lib/lpsongs";

/** Section tabs (Playlists active) and the way back to the Playlists list, with its filters kept. */
function PlaylistBar() {
  const { origin, back, params } = useOrigin();
  // Without an origin the playlist was opened from the Playlists list.
  const to = params.has(FROM_PARAM) ? backHref(origin, back) : backHref({ kind: "playlists" });
  return (
    <>
      <div className="lib-bar map-bar">
        <div className="lib-title">
          <SectionTabs active="playlists" heading="Playlist" headingId="lp-heading" noHeading />
        </div>
      </div>
      <BackLink to={to} />
    </>
  );
}

/** The page for one playlist: details, cover, songs table and export settings. */
function PlaylistForm({ existing, initial }: { existing: string | null; initial: Draft }) {
  const client = useQueryClient();
  const navigate = useNavigate();
  const announce = useAnnounce();
  const config = usePlaylistConfig();
  const [draft, setDraft] = useState<Draft>(initial);
  const [base, setBase] = useState<string>(JSON.stringify(toInput(initial)));
  const [picking, setPicking] = useState(false);
  const [busy, setBusy] = useState(false);
  useDocumentTitle(draft.title || "New playlist");

  const rows = useMemo(() => rowsOf(draft.songs), [draft.songs]);
  const missing = rows.filter((r) => r.missing).length;
  const dirty = JSON.stringify(toInput(draft)) !== base || draft.cover !== undefined;
  const exportEnabled = config.data?.export_enabled ?? false;
  const set = (patch: Partial<Draft>) => setDraft((d) => ({ ...d, ...patch }));
  const fail = (title: string, err: unknown) =>
    announce({ variant: "danger", title, message: errorMessage(err) });

  const add = async (picks: SongPick[]) => {
    const items: Record<string, MapItem> = {};
    await Promise.all(
      picks.map(async (p) => {
        try {
          items[p.map_id] = await getMap(p.map_id);
        } catch {
          /* the table shows the song as missing until it is saved and reloaded */
        }
      }),
    );
    setDraft((d) => ({ ...d, songs: addPicks(d.songs, picks, items) }));
  };

  const save = async (exportAfter: boolean) => {
    setBusy(true);
    try {
      const body = toInput(draft);
      const saved = existing ? await updatePlaylist(existing, body) : await createPlaylist(body);
      announce({ variant: "success", title: `Saved ${saved.title}` });
      if (exportAfter) {
        const out = await exportPlaylist(saved.id, saved.folder);
        announce({
          variant: "success",
          title: `Exported ${saved.title}`,
          message: `${out.relative}. ${REFRESH_HINT}`,
        });
      }
      await client.invalidateQueries({ queryKey: playlistKeys.all });
      const next = draftOf(saved);
      setDraft(next);
      setBase(JSON.stringify(toInput(next)));
      if (!existing) void navigate(`/playlists/${saved.id}`, { replace: true });
    } catch (err) {
      fail("Save playlist", err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="page map-page lp-page">
      <PlaylistBar />
      <div className="map-scroll">
        <div className="maphead">
          <LpCover
            url={draft.coverUrl}
            onPick={(c) => set({ cover: { data: c.data }, coverUrl: c.url })}
            onError={(m) => announce({ variant: "danger", title: "Cover", message: m })}
          />
          <div className="mapmeta">
            <LpName value={draft.title} onCommit={(title) => set({ title })} />
            <p className="sub">
              {draft.author || "saber-tooth"} &middot; {rows.length}{" "}
              {rows.length === 1 ? "song" : "songs"}
              {missing > 0 && <span className="lp-missing"> &middot; {missing} missing</span>}
            </p>
            <div className="metarow">
              <ActionButton
                icon="ok"
                text
                variant="primary"
                label="Save"
                tip="Save the playlist"
                disabled={busy || !draft.title.trim() || (!dirty && !!existing)}
                onClick={() => void save(false)}
              />
              <ActionButton
                icon="download"
                text
                label="Save and export"
                tip={
                  exportEnabled ? "Save and write the .bplist" : "Playlist export is not configured"
                }
                disabled={busy || !draft.title.trim() || !exportEnabled}
                onClick={() => void save(true)}
              />
              {dirty && <span className="lp-sub">Unsaved changes</span>}
            </div>
          </div>
        </div>
        <div className="lp-section-head">
          <h2 className="lp-heading">Songs</h2>
          <ActionButton
            icon="bookmark-plus"
            text
            label={picking ? "Close the picker" : "Add songs"}
            tip="Add songs from the library or a job's output"
            aria-expanded={picking}
            onClick={() => setPicking((p) => !p)}
          />
        </div>
        {picking && (
          <LpSongPicker
            chosen={new Set(draft.songs.map(songId))}
            onAdd={(p) => void add(p)}
            onError={(m) => announce({ variant: "danger", title: "Playlist", message: m })}
          />
        )}
        <LpSongTable
          rows={rows}
          playlistId={existing}
          onRemove={(r) => set({ songs: draft.songs.filter((s) => s !== r.song) })}
        />
        <h2 className="lp-heading">Export</h2>
        <LpExport
          author={draft.author}
          description={draft.description}
          folder={draft.folder}
          sync={draft.sync}
          onAuthor={(author) => set({ author })}
          onDescription={(description) => set({ description })}
          onFolder={(folder) => set({ folder })}
          onSync={(sync) => set({ sync })}
        />
      </div>
      {existing && <PlaylistFooter id={existing} />}
    </section>
  );
}

/** The playlist page in its final layout while the playlist loads: header, button shapes, songs. */
function PlaylistSkeleton() {
  return (
    <section
      className="page map-page lp-page"
      aria-label="Loading playlist"
      aria-busy="true"
      data-skeleton="true"
    >
      <PlaylistBar />
      <div className="map-scroll">
        <div className="maphead" aria-hidden="true">
          <span className="sk cover cover-big" />
          <div className="mapmeta">
            <span className="sk sk-title" />
            <span className="sk sk-bar short" />
            <div className="metarow">
              <span className="sk sk-tool" />
              <span className="sk sk-tool wide" />
            </div>
          </div>
        </div>
        <div className="lp-section-head" aria-hidden="true">
          <span className="sk sk-bar short" />
        </div>
        <LpSongTable rows={[]} onRemove={() => undefined} loading />
      </div>
    </section>
  );
}

/** `/playlists/new` and `/playlists/:id`: one playlist, laid out like the map page. */
export function PlaylistPage() {
  const { id } = useParams();
  const existing = id && id !== "new" ? id : null;
  const loaded = usePlaylist(existing);
  if (!existing) return <PlaylistForm key="new" existing={null} initial={EMPTY_DRAFT} />;
  if (loaded.isError) {
    return (
      <section className="page lp-page">
        <PlaylistBar />
        <Alert
          variant="danger"
          title="Could not load the playlist"
          message={errorMessage(loaded.error)}
        />
      </section>
    );
  }
  if (!loaded.data) return <PlaylistSkeleton />;
  return <PlaylistForm key={existing} existing={existing} initial={draftOf(loaded.data)} />;
}
