# Task 13: Frontend types, client, query hook, pure crop helpers (part b)

Continues [task-13a.md](task-13a.md).

- [ ] **Step 3: Implement**

In `frontend/src/api/types.ts` replace the line `export type JobKind = "scan" | "apply" | "fix" | "generate" | "learn";` with:

```ts
export type JobKind = "scan" | "apply" | "fix" | "generate" | "learn" | "crop";

export type CropLength = "60" | "120";
export type EndKind = "section" | "phrase" | "bar4" | "bar";

export interface CropEnd {
  beat: number;
  seconds: number;
  kind: EndKind;
}

export interface CropStart {
  beat: number;
  seconds: number;
  ends: CropEnd[];
}

export interface CropWindow {
  start_beat: number;
  end_beat: number;
  start_s: number;
  end_s: number;
  length_s: number;
  end_kind: EndKind;
  score: number;
}

export interface CropPlan {
  enabled: boolean;
  /** Why this length is off, when it is. */
  reason: string | null;
  /** Allowed length in seconds: 54 to 66 or 108 to 132. */
  band: [number, number];
  /** The best window first, then the next two. */
  suggestions: CropWindow[];
  starts: CropStart[];
}

export interface CropSection {
  start_beat: number;
  end_beat: number;
  start_s: number;
  end_s: number;
  nps: number;
  intensity: number;
}

export interface Timeline {
  map_id: string;
  duration_s: number;
  bpm: number;
  hardest: string;
  /** True when the map has no audio analysis: sections come from the notes and lights only. */
  map_only: boolean;
  grid_drift_s: number | null;
  /** Notes per second in 1 s steps, per difficulty that has notes. */
  nps: Record<string, number[]>;
  sections: CropSection[];
  lengths: Record<CropLength, CropPlan>;
}

/** Result of a finished crop job. */
export interface CropResult {
  map_id: string;
  folder: string;
  cropped_id: string;
  label: string;
  start_beat: number;
  end_beat: number;
  length_s: number;
}
```

In `frontend/src/api/client.ts` change the type import line to `import type { Facets, Job, MapItem, MapPage, Proposal, Timeline } from "./types";` and add after the `fixMap` line:

```ts
export const getTimeline = (id: string, signal?: AbortSignal): Promise<Timeline> =>
  request("GET", `/api/maps/${seg(id)}/timeline`, undefined, signal);

export const cropMap = (id: string, startBeat: number, endBeat: number): Promise<Started> =>
  request("POST", `/api/maps/${seg(id)}/crop`, { start_beat: startBeat, end_beat: endBeat });
```

In `frontend/src/api/queries.ts` change the client import to include `getTimeline` (`import { getFacets, getJob, getMap, getProposals, getTimeline, isRetryable, listMaps } from "./client";`), add `timeline: (id: string) => ["timeline", id] as const,` to `keys` after the `proposals` entry, and add after `useProposals`:

```ts
export function useTimeline(id: string) {
  return useQuery({
    queryKey: keys.timeline(id),
    queryFn: ({ signal }) => getTimeline(id, signal),
    retry,
    staleTime: 60_000,
  });
}
```

In `frontend/src/lib/alerts.ts`: add `  crop: "Crop failed",` after `  learn: "Learning failed",` in `FAILED_TITLE`; add `  crop: "Cropped",` after `  learn: "Lightshows learned",` in `DONE_TITLE`; and in `success()` replace

```ts
        message: "The new lightshows are ready to use.",
      };
```

with

```ts
        message: "The new lightshows are ready to use.",
      };
    case "crop":
      return {
        variant: "success",
        title: DONE_TITLE.crop,
        message: where || "The cropped map was written.",
      };
```

Create `frontend/src/lib/crop.ts`:

```ts
// Pure helpers for the crop panel: snapping, stepping and re-picking the window edges.
import type { CropEnd, CropPlan, CropStart, EndKind } from "../api/types";

export const EPS = 1e-6;

/** Strongest kind first: the order the server prefers an end in. */
export const KIND_RANK: Record<EndKind, number> = { section: 0, phrase: 1, bar4: 2, bar: 3 };

export const KIND_LABEL: Record<EndKind, string> = {
  section: "section boundary",
  phrase: "phrase line",
  bar4: "4-bar line",
  bar: "bar line",
};

export const CROP_TIPS = {
  create:
    "Write the chosen stretch of the song as a new folder beside this map. The original is never changed.",
  reset: "Go back to the suggested window.",
} as const;

/** A chosen window, in beats. */
export interface Choice {
  start: number;
  end: number;
}

export const same = (a: number, b: number): boolean => Math.abs(a - b) < EPS;

/** "m:ss.s" for a time in seconds. */
export function clock(seconds: number): string {
  const tenths = Math.round(Math.max(0, seconds) * 10);
  const m = Math.floor(tenths / 600);
  return `${m}:${((tenths - m * 600) / 10).toFixed(1).padStart(4, "0")}`;
}

/** Song seconds under a pointer, clamped to the song. */
export function secondsAt(clientX: number, left: number, width: number, duration: number): number {
  if (width <= 0) return 0;
  return Math.min(duration, Math.max(0, ((clientX - left) / width) * duration));
}

export function nearest<T extends { seconds: number }>(points: readonly T[], seconds: number): T {
  let best = points[0] as T;
  for (const p of points) {
    if (Math.abs(p.seconds - seconds) < Math.abs(best.seconds - seconds)) best = p;
  }
  return best;
}

export const snapStart = (plan: CropPlan, seconds: number): CropStart =>
  nearest(plan.starts, seconds);

export const snapEnd = (start: CropStart, seconds: number): CropEnd => nearest(start.ends, seconds);

/** The strongest kind, then the length closest to the middle of the band, then the earlier end. */
export function pickEnd(start: CropStart, band: [number, number]): CropEnd {
  const target = (band[0] + band[1]) / 2;
  const off = (e: CropEnd) => Math.abs(e.seconds - start.seconds - target);
  return [...start.ends].sort(
    (a, b) => KIND_RANK[a.kind] - KIND_RANK[b.kind] || off(a) - off(b) || a.beat - b.beat,
  )[0] as CropEnd;
}

/** The end to show after the start changed: the old one when still allowed, else a new pick. */
export function endFor(start: CropStart, previous: number | null, band: [number, number]): CropEnd {
  const kept = start.ends.find((e) => previous !== null && same(e.beat, previous));
  return kept ?? pickEnd(start, band);
}

function stepIn<T extends { beat: number }>(
  points: readonly T[],
  current: number,
  dir: 1 | -1,
): T | undefined {
  const sorted = [...points].sort((a, b) => a.beat - b.beat);
  return dir === 1
    ? sorted.find((p) => p.beat > current + EPS)
    : sorted.reverse().find((p) => p.beat < current - EPS);
}

/** Next or previous start; every start is a section boundary, so Shift adds nothing here. */
export function stepStart(plan: CropPlan, current: number, dir: 1 | -1): CropStart {
  return (
    stepIn(plan.starts, current, dir) ??
    (plan.starts.find((s) => same(s.beat, current)) as CropStart)
  );
}

/** Next or previous allowed end; `jump` considers section ends only. */
export function stepEnd(start: CropStart, current: number, dir: 1 | -1, jump: boolean): CropEnd {
  const pool = jump ? start.ends.filter((e) => e.kind === "section") : start.ends;
  return (
    stepIn(pool, current, dir) ??
    start.ends.find((e) => same(e.beat, current)) ??
    (start.ends[0] as CropEnd)
  );
}

export function suggestion(plan: CropPlan): Choice | null {
  const best = plan.suggestions[0];
  return plan.enabled && best ? { start: best.start_beat, end: best.end_beat } : null;
}

/** Switching length: keep the start when the new plan has it and re-pick the end. */
export function keepStart(plan: CropPlan, choice: Choice | null): Choice | null {
  const start = choice ? plan.starts.find((s) => same(s.beat, choice.start)) : undefined;
  return start ? { start: start.beat, end: pickEnd(start, plan.band).beat } : null;
}
```

- [ ] **Step 4: Run to pass**

Run: `npx --prefix frontend vitest run --root frontend tests/croplib.test.ts tests/alerts.test.tsx`
Expected: all pass (`alerts.test.tsx` proves the exhaustive `JobKind` tables still hold).

- [ ] **Step 5: Gates**

Run: `npm --prefix frontend run typecheck`
Expected: no errors.
Run: `npm --prefix frontend run lint`
Expected: no warnings.
Run: `npx --prefix frontend prettier --config .crepidoma/configs/.prettierrc --check frontend/src/lib/crop.ts frontend/tests/croplib.test.ts frontend/tests/crophelpers.tsx`
Expected: all files pass; if not, run the same command with `--write` on those three files only.

- [ ] **Step 6: Commit:** main thread runs `task git:commit -- "feat: crop types, client, query hook and snapping helpers"` (subagents never commit).

---
