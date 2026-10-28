# Task 13: VR Library screen (part d)

Continues [task-13c.md](task-13c.md).

- [ ] **Step 7: Implement the screen**

Create `frontend/src/vr/VrLibraryPage.tsx`:

```tsx
import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";
import { useLibrary, useLiveRows } from "../api/queries";
import { SpecAlert } from "../components/Alert";
import { FixOutcomes } from "../components/FixOutcomes";
import { errorToAlert } from "../lib/alerts";
import { useDocumentTitle } from "../lib/hooks";
import {
  VR_PRESETS,
  VR_SORTS,
  encodeVrView,
  isFixedCopy,
  parseVrView,
  togglePreset,
  vrState,
  type VrView,
} from "./presets";
import { useNearEnd } from "./useNearEnd";
import { VrCard } from "./VrCard";
import { VrNav } from "./VrNav";

export function VrLibraryPage() {
  useDocumentTitle("Library");
  const [params, setParams] = useSearchParams();
  const search = params.toString();
  const view = useMemo(() => parseVrView(search), [search]);
  const library = useLibrary(useMemo(() => vrState(view), [view]));
  const { fetchNextPage, hasNextPage, isFetchingNextPage } = library;
  const items = useMemo(() => library.data?.pages.flatMap((p) => p.items) ?? [], [library.data]);
  const shown = view.presets.includes("fixed") ? items.filter(isFixedCopy) : items;
  const total = library.data?.pages.at(-1)?.total ?? 0;
  useLiveRows(items);

  const loadMore = useCallback(() => void fetchNextPage(), [fetchNextPage]);
  const end = useNearEnd(loadMore, Boolean(hasNextPage) && !isFetchingNextPage);
  const change = (next: VrView) => setParams(encodeVrView(next));

  return (
    <section className="vr-screen" aria-labelledby="vr-library-heading">
      <VrNav active="library" />
      <h1 id="vr-library-heading" className="vr-heading" tabIndex={-1} data-page-heading>
        Library
      </h1>
      <p className="vr-help" aria-live="polite">
        {library.isPending ? "" : `${total} ${total === 1 ? "map" : "maps"}`}
      </p>
      <FixOutcomes />
      <div className="vr-toggles" role="group" aria-label="Show">
        {VR_PRESETS.map((p) => (
          <div key={p.key} className="vr-toggle">
            <button
              type="button"
              aria-pressed={view.presets.includes(p.key)}
              onClick={() => change(togglePreset(view, p.key))}
            >
              {p.label}
            </button>
            <small className="vr-help">{p.help}</small>
          </div>
        ))}
      </div>
      <div className="vr-toggles" role="radiogroup" aria-label="Sort by">
        {VR_SORTS.map((s) => (
          <button
            key={s.key}
            type="button"
            role="radio"
            aria-checked={view.sort === s.key}
            onClick={() => change({ ...view, sort: s.key })}
          >
            {s.label}
          </button>
        ))}
      </div>
      <div className="vr-scroll">
        {library.isPending && (
          <p className="vr-help" role="status">
            Loading maps
          </p>
        )}
        {library.isError && !library.data && (
          <SpecAlert
            spec={errorToAlert(library.error, "Could not load the library")}
            onRetry={() => void library.refetch()}
          />
        )}
        {library.data && shown.length === 0 && !hasNextPage && (
          <p className="vr-empty">No maps match. Turn a filter off to see more.</p>
        )}
        <div className="vr-grid">
          {shown.map((item) => (
            <VrCard key={item.id} item={item} />
          ))}
        </div>
        <div ref={end} aria-hidden="true" />
        {isFetchingNextPage && (
          <p className="vr-help" role="status">
            Loading more maps
          </p>
        )}
      </div>
    </section>
  );
}
```

Append to `frontend/src/styles/vr.css`:

```css
/* Library cards. */
[data-ui="vr"] .vr-toggle {
  display: flex;
  flex-direction: column;
  gap: var(--vr-gap);
  max-width: 22rem;
}
[data-ui="vr"] .vr-card {
  display: flex;
  gap: var(--vr-gap);
  padding: var(--vr-gap);
  border: 2px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
}
[data-ui="vr"] .vr-card-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  gap: var(--vr-gap);
}
[data-ui="vr"] .vr-card-title {
  margin: 0;
  font-size: calc(var(--vr-text) * 1.2);
  overflow-wrap: anywhere;
}
[data-ui="vr"] .vr-card-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--vr-gap);
}
```

Append to `frontend/src/vr/README.md`:

```markdown
4. `presets.ts`, `VrNav.tsx`, `useNearEnd.ts`, `VrCard.tsx`, `VrLibraryPage.tsx`: the `/vr` Library screen (presets map onto the library query, state in the address, more cards on scroll).
```

- [ ] **Step 8: Run the tests to see them pass**

Run: `npx --prefix frontend vitest run --root frontend tests/vrpresets.test.ts tests/vrlibrary.test.tsx tests/vrcss.test.ts`
Expected: PASS, 36 passed in the first two files and the 10 of `vrcss.test.ts`.

- [ ] **Step 9: Type check and lint**

Run: `npm --prefix frontend run typecheck` then `npm --prefix frontend run lint`
Expected: both exit 0.

- [ ] **Step 10: Commit**

Commit: main thread runs `task st:commit -- -m "feat(vr): VR library screen with presets, sort and scroll loading" frontend/src/vr frontend/src/styles/vr.css frontend/tests/vrhelpers.tsx frontend/tests/vrpresets.test.ts frontend/tests/vrlibrary.test.tsx`
