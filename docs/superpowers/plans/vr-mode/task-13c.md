# Task 13: VR Library screen (part c)

Continues [task-13b.md](task-13b.md).

- [ ] **Step 5: Implement the pure presets**

Create `frontend/src/vr/presets.ts`:

```ts
// The VR library presets and sorts, and how they map onto the library query. Pure functions.
import type { LevelKey, MapItem, StatusKey } from "../api/types";
import { STATUS_ORDER } from "../lib/status";
import { DEFAULT_STATE, type LibraryState } from "../lib/urlstate";

export const VR_PRESETS = [
  { key: "needs-fix", label: "Needs fix", help: "Maps with errors or warnings." },
  {
    key: "missing-levels",
    label: "Missing levels",
    help: "Maps never scanned that lack one of the five levels.",
  },
  { key: "unscanned", label: "Not scanned", help: "Maps that have not been scanned yet." },
  { key: "fixed", label: "Fixed copies", help: "The [saber-tooth] copies that Fix wrote." },
  { key: "expert-plus", label: "Expert+", help: "Maps that have an Expert+ level." },
] as const;
export type VrPreset = (typeof VR_PRESETS)[number]["key"];

export const VR_SORTS = [
  { key: "title", label: "Title", sort: "title", order: "asc" },
  { key: "errors", label: "Most errors", sort: "errors", order: "desc" },
  { key: "recent", label: "Recently scanned", sort: "scanned_at", order: "desc" },
  { key: "length", label: "Longest", sort: "duration", order: "desc" },
] as const;
export type VrSort = (typeof VR_SORTS)[number]["key"];

export interface VrView {
  presets: VrPreset[];
  sort: VrSort;
}

/** Known presets in the fixed order, once each, and a known sort; anything else is ignored. */
export function parseVrView(search: string): VrView {
  const params = new URLSearchParams(search);
  const wanted = (params.get("p") ?? "").split(",");
  const sort = VR_SORTS.find((s) => s.key === params.get("sort"))?.key ?? "title";
  return { presets: VR_PRESETS.map((p) => p.key).filter((k) => wanted.includes(k)), sort };
}

export function encodeVrView(view: VrView): URLSearchParams {
  const params = new URLSearchParams();
  if (view.presets.length) params.set("p", view.presets.join(","));
  if (view.sort !== "title") params.set("sort", view.sort);
  return params;
}

export function togglePreset(view: VrView, key: VrPreset): VrView {
  const on = view.presets.includes(key);
  const presets = VR_PRESETS.map((p) => p.key).filter((k) =>
    k === key ? !on : view.presets.includes(k),
  );
  return { ...view, presets };
}

/** The library query for a view. Status presets combine as OR; Expert+ narrows them. */
export function vrState(view: VrView): LibraryState {
  const status = new Set<StatusKey>();
  if (view.presets.includes("needs-fix")) status.add("error").add("warn");
  if (view.presets.includes("missing-levels")) status.add("incomplete");
  if (view.presets.includes("unscanned")) status.add("unscanned");
  const by = VR_SORTS.find((s) => s.key === view.sort) ?? VR_SORTS[0];
  const level: LevelKey[] = view.presets.includes("expert-plus") ? ["ExpertPlus"] : [];
  return {
    ...DEFAULT_STATE,
    status: STATUS_ORDER.filter((s) => status.has(s)),
    level,
    sort: by.sort,
    order: by.order,
  };
}

/** The API has no filter for fixed copies; a fixed copy is a map that records its original. */
export const isFixedCopy = (item: Partial<Pick<MapItem, "original_id">>): boolean =>
  Boolean(item.original_id);
```

- [ ] **Step 6: Implement the nav, the end sentinel hook and the card**

Create `frontend/src/vr/VrNav.tsx`:

```tsx
import { Link } from "react-router";

const ITEMS = [
  { key: "library", to: "/vr", label: "Library" },
  { key: "beatsaver", to: "/vr/beatsaver", label: "BeatSaver" },
] as const;

/** Library | BeatSaver as two large links at the top of each VR list screen. */
export function VrNav({ active }: { active: "library" | "beatsaver" }) {
  return (
    <nav className="vr-nav" aria-label="Section">
      {ITEMS.map((i) => (
        <Link
          key={i.key}
          className="vr-target"
          to={i.to}
          aria-current={i.key === active ? "page" : undefined}
        >
          {i.label}
        </Link>
      ))}
    </nav>
  );
}
```

Create `frontend/src/vr/useNearEnd.ts`:

```ts
import { useEffect, useRef, type RefObject } from "react";

/** Calls `onNear` when the ref'd end sentinel comes within 600 px of view; off when `enabled` is false. */
export function useNearEnd(onNear: () => void, enabled: boolean): RefObject<HTMLDivElement | null> {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = ref.current;
    if (!enabled || !node || typeof IntersectionObserver === "undefined") return undefined;
    const seen = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) onNear();
      },
      { rootMargin: "600px" },
    );
    seen.observe(node);
    return () => seen.disconnect();
  }, [enabled, onNear]);
  return ref;
}
```

Create `frontend/src/vr/VrCard.tsx`:

```tsx
import { Link } from "react-router";
import { useFix } from "../api/fix";
import type { MapItem } from "../api/types";
import { Cover, LevelChips, StatusChip } from "../components/Chips";
import { PreviewButton } from "../components/PreviewButton";
import { formatDuration } from "../lib/format";
import { mapName } from "../lib/status";

/** One map as a large card: cover, title, status, levels, length and the three actions. */
export function VrCard({ item }: { item: MapItem }) {
  const name = mapName(item);
  const fix = useFix(item, name);
  const busy = item.job !== null || item.status === "unreadable";
  const copy = item.fixed_copy_id;
  return (
    <article className="vr-card" data-map={item.id}>
      <Cover url={item.cover_url} big />
      <div className="vr-card-body">
        <h2 className="vr-card-title">{name}</h2>
        <p className="vr-help">{item.mapper || "Unknown mapper"}</p>
        <div className="vr-card-meta">
          <StatusChip item={item} />
          <LevelChips names={item.difficulties} />
          <span>{formatDuration(item.duration_s)}</span>
        </div>
        <div className="vr-actions">
          <PreviewButton src={item.audio_url} start={item.preview_start} title={name} />
          <button
            type="button"
            className="btn accent"
            aria-label={`Fix ${name}`}
            disabled={busy}
            onClick={() => void fix()}
          >
            Fix
          </button>
          <Link
            className="btn plain"
            aria-label={`${copy ? "Open fixed copy of" : "Open"} ${name}`}
            to={`/vr/maps/${encodeURIComponent(copy || item.id)}`}
          >
            {copy ? "Open fixed copy" : "Open"}
          </Link>
        </div>
      </div>
    </article>
  );
}
```

Continued in [task-13d.md](task-13d.md).
