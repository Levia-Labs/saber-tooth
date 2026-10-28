# Task 15: VR BeatSaver screen (part c)

Continues [task-15b.md](task-15b.md).

- [ ] **Step 5: Implement the screen**

Create `frontend/src/vr/VrBeatSaverPage.tsx`:

```tsx
import { useCallback, useMemo } from "react";
import { Link, useSearchParams } from "react-router";
import { useBsSearch, usePresets } from "../api/beatsaver";
import { useDownloads, type Downloads } from "../components/beatsaver/downloads";
import { DEFAULT_BS_STATE, encodeBsState, stateFromPreset, type BsOrder } from "../lib/bsfilters";
import { useDocumentTitle } from "../lib/hooks";
import { describePreset } from "../lib/presetdescribe";
import { useBsState } from "../lib/useBsState";
import { VrBsList } from "./VrBsCard";
import { VrBsPlaylistMaps, VrBsPlaylists } from "./VrBsPlaylists";
import { VrNav } from "./VrNav";

const ORDERS: readonly BsOrder[] = ["Latest", "Rating", "Curated", "Duration"];

function VrBsMaps({ downloads }: { downloads: Downloads }) {
  const { state, set, update } = useBsState();
  const query = useBsSearch(state);
  const presets = usePresets();
  const maps = useMemo(() => query.data?.pages.flatMap((p) => p.items) ?? [], [query.data]);
  const here = encodeBsState(state).toString();
  const { fetchNextPage } = query;
  const more = useCallback(() => void fetchNextPage(), [fetchNextPage]);
  return (
    <>
      <div className="vr-toggles" role="group" aria-label="Presets">
        {(presets.data ?? []).map((p) => {
          const next = stateFromPreset(p.filters);
          const on = encodeBsState(next).toString() === here;
          return (
            <div key={p.id} className="vr-toggle">
              <button
                type="button"
                aria-pressed={on}
                onClick={() => set(on ? DEFAULT_BS_STATE : next)}
              >
                {p.name}
              </button>
              <small className="vr-help">{describePreset(p.filters)}</small>
            </div>
          );
        })}
      </div>
      <div className="vr-toggles" role="radiogroup" aria-label="Sort by">
        {ORDERS.map((order) => (
          <button
            key={order}
            type="button"
            role="radio"
            aria-checked={state.order === order && state.localSort === null}
            onClick={() => update({ order, localSort: null })}
          >
            {order}
          </button>
        ))}
      </div>
      <VrBsList
        maps={maps}
        pending={query.isPending}
        error={query.error}
        onRetry={() => void query.refetch()}
        hasNext={query.hasNextPage}
        fetching={query.isFetchingNextPage}
        onMore={more}
        downloads={downloads}
        emptyText="No maps match. Pick another preset."
      />
    </>
  );
}

export function VrBeatSaverPage() {
  useDocumentTitle("BeatSaver");
  const [params] = useSearchParams();
  const downloads = useDownloads();
  const playlists = params.get("view") === "playlists";
  const playlist = params.get("playlist");
  return (
    <section className="vr-screen" aria-labelledby="vr-bs-heading">
      <VrNav active="beatsaver" />
      <h1 id="vr-bs-heading" className="vr-heading" tabIndex={-1} data-page-heading>
        BeatSaver
      </h1>
      <nav className="vr-nav" aria-label="BeatSaver sections">
        <Link
          className="vr-target"
          to="/vr/beatsaver"
          aria-current={playlists ? undefined : "page"}
        >
          Maps
        </Link>
        <Link
          className="vr-target"
          to="/vr/beatsaver?view=playlists"
          aria-current={playlists ? "page" : undefined}
        >
          Playlists
        </Link>
      </nav>
      {!playlists && <VrBsMaps downloads={downloads} />}
      {playlists && !playlist && <VrBsPlaylists />}
      {playlists && playlist && <VrBsPlaylistMaps id={playlist} downloads={downloads} />}
    </section>
  );
}
```

Append to `frontend/src/vr/README.md`:

```markdown
6. `VrBsCard.tsx`, `VrBsPlaylists.tsx`, `VrBeatSaverPage.tsx`: the `/vr/beatsaver` screen (preset toggles, sort, cursor paging on scroll, playlists, large Download per card; no text search).
```

No new CSS is needed: the cards, toggles, grid and `.vr-back` classes come from Tasks 12 to 14.

- [ ] **Step 6: Run the tests to see them pass**

Run: `npx --prefix frontend vitest run --root frontend tests/vrbeatsaver.test.tsx tests/vrlibrary.test.tsx`
Expected: PASS, 14 passed in `vrbeatsaver.test.tsx`.

- [ ] **Step 7: Type check and lint**

Run: `npm --prefix frontend run typecheck` then `npm --prefix frontend run lint`
Expected: both exit 0.

- [ ] **Step 8: Commit**

Commit: main thread runs `task st:commit -- -m "feat(vr): VR BeatSaver screen with presets, playlists and large Download" frontend/src/vr frontend/tests/vrbeatsaver.test.tsx`
