import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useJobLists } from "../../api/joblist";
import { request } from "../../api/client";
import { jobPicks, livePicks, type SongPick } from "../../api/playlists";
import type { MapItem } from "../../api/types";
import { ActionButton } from "../Buttons";
import { Cover } from "../Chips";

interface Props {
  /** Map ids already in the draft. */
  chosen: ReadonlySet<string>;
  onAdd: (picks: SongPick[]) => void;
  onError: (message: string) => void;
}

const LIVE_SOURCES = [
  ["latest-generated", "Latest generated"],
  ["latest-fixed", "Latest fixed"],
] as const;
const PICK_KINDS = new Set(["generate", "fix"]);

function LibraryPicker({ chosen, onAdd }: Pick2) {
  const [q, setQ] = useState("");
  const found = useQuery({
    queryKey: ["playlists", "library-search", q],
    queryFn: ({ signal }) =>
      request<{ items: MapItem[] }>(
        "GET",
        `/api/maps?limit=12&q=${encodeURIComponent(q.trim())}`,
        undefined,
        signal,
      ),
  });
  return (
    <div className="lp-pick">
      <input
        type="search"
        className="input"
        aria-label="Search the library"
        placeholder="Search the library"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      <ul className="lp-list" aria-label="Library results">
        {(found.data?.items ?? []).map((m) => (
          <li key={m.id}>
            <Cover url={m.cover_url} />
            <span className="lp-song-name">
              {m.title}
              <span className="lp-sub">{m.mapper}</span>
            </span>
            <ActionButton
              icon="bookmark-plus"
              label={`Add ${m.title}`}
              tip="Add to the playlist"
              disabled={chosen.has(m.id)}
              onClick={() => onAdd([{ map_id: m.id, song_name: m.title, mapper: m.mapper }])}
            />
          </li>
        ))}
      </ul>
    </div>
  );
}

type Pick2 = Omit<Props, "onError">;

function OutputPicker({ onAdd, onError }: Omit<Props, "chosen">) {
  const lists = useJobLists();
  const jobs = lists.recent.filter((j) => j.status === "done" && PICK_KINDS.has(j.kind));
  const run = (load: () => Promise<{ items: SongPick[] }>) =>
    load().then(
      (r) => onAdd(r.items),
      (e: unknown) => onError(e instanceof Error ? e.message : String(e)),
    );
  return (
    <div className="lp-pick">
      <div className="lp-live">
        {LIVE_SOURCES.map(([name, label]) => (
          <ActionButton
            key={name}
            icon="queue"
            text
            label={label}
            tip={`Add the ${label.toLowerCase()} maps`}
            onClick={() => void run(() => livePicks(name))}
          />
        ))}
      </div>
      <ul className="lp-list" aria-label="Job output">
        {jobs.length === 0 && <li className="lp-sub">No finished generate or fix jobs.</li>}
        {jobs.map((j) => (
          <li key={j.id}>
            <span className="lp-song-name">
              {j.title}
              <span className="lp-sub">{j.kind}</span>
            </span>
            <ActionButton
              icon="bookmark-plus"
              label={`Add output of ${j.title}`}
              tip="Add this job's map"
              onClick={() => void run(() => jobPicks(j.id))}
            />
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Add songs from the library, a finished job's output or the latest generated or fixed maps. */
export function LpSongPicker({ chosen, onAdd, onError }: Props) {
  const [tab, setTab] = useState<"library" | "output">("library");
  return (
    <div className="lp-picker">
      <div role="tablist" aria-label="Song source" className="lp-tabs">
        {(["library", "output"] as const).map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            className={`btn plain${tab === t ? " active" : ""}`}
            onClick={() => setTab(t)}
          >
            {t === "library" ? "Library" : "Job output"}
          </button>
        ))}
      </div>
      {tab === "library" ? (
        <LibraryPicker chosen={chosen} onAdd={onAdd} />
      ) : (
        <OutputPicker onAdd={onAdd} onError={onError} />
      )}
    </div>
  );
}
