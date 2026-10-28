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
  // The fixed-copy filter runs in the browser, so only the loaded matches can be counted.
  const count = view.presets.includes("fixed")
    ? shown.length
    : (library.data?.pages.at(-1)?.total ?? 0);
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
        {library.isPending ? "" : `${count} ${count === 1 ? "map" : "maps"}`}
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
