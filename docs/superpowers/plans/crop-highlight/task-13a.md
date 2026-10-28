# Task 13: Frontend types, client, query hook, pure crop helpers

**Files:**

- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/queries.ts`
- Modify: `frontend/src/lib/alerts.ts`
- Create: `frontend/src/lib/crop.ts`
- Create: `frontend/tests/crophelpers.tsx`
- Test: `frontend/tests/croplib.test.ts`

**Interfaces:**

Consumes: `request<T>(method, path, body?, signal?)` and `seg` in `client.ts`; `Started` (`{ job: string }`); `keys`, `retry`, `useQuery` in `queries.ts`; `toAlert`, `FAILED_TITLE`, `DONE_TITLE` in `lib/alerts.ts`; `mockFetch`, `item` in `tests/helpers.tsx`.

Produces (`api/types.ts`): `JobKind` gains `"crop"`; new `CropLength = "60" | "120"`, `EndKind = "section" | "phrase" | "bar4" | "bar"`, `CropEnd {beat, seconds, kind}`, `CropStart {beat, seconds, ends}`, `CropWindow {start_beat, end_beat, start_s, end_s, length_s, end_kind, score}`, `CropPlan {enabled, reason, band: [number, number], suggestions, starts}`, `CropSection {start_beat, end_beat, start_s, end_s, nps, intensity}`, `Timeline {map_id, duration_s, bpm, hardest, map_only, grid_drift_s, nps, sections, lengths: Record<CropLength, CropPlan>}`, `CropResult {map_id, folder, cropped_id, label, start_beat, end_beat, length_s}`.

Produces (`api/client.ts`): `getTimeline(id: string, signal?: AbortSignal): Promise<Timeline>`; `cropMap(id: string, startBeat: number, endBeat: number): Promise<Started>`.

Produces (`api/queries.ts`): `keys.timeline(id)`; `useTimeline(id: string)`.

Produces (`lib/crop.ts`): `EPS`, `KIND_RANK`, `KIND_LABEL`, `CROP_TIPS`, `Choice {start, end}` (beats), `same(a, b)`, `clock(seconds)` as `m:ss.s`, `secondsAt(clientX, left, width, duration)`, `nearest(points, seconds)`, `snapStart(plan, seconds): CropStart`, `snapEnd(start, seconds): CropEnd`, `pickEnd(start, band): CropEnd`, `endFor(start, previous: number | null, band): CropEnd`, `stepStart(plan, current, dir): CropStart`, `stepEnd(start, current, dir, jump): CropEnd`, `suggestion(plan): Choice | null`, `keepStart(plan, choice: Choice | null): Choice | null`.

Rules the tests pin: the start edge snaps to section boundaries only (every start point is one); the end edge snaps to the start's allowed ends; an arrow key steps to the next or previous allowed point and stays put at the ends; Shift+arrow on the end edge jumps to the next or previous `section` end (for the start edge Shift changes nothing, every step is already a section); after the start changes the old end is kept when still allowed, else the strongest kind closest to the band midpoint is picked (the server's rule); switching length keeps the start when the new plan has it.

- [ ] **Step 1: Write the failing tests**

Create `frontend/tests/crophelpers.tsx`:

```tsx
import type { CropEnd, CropPlan, CropWindow, EndKind, Timeline } from "../src/api/types";

const series = (scale: number): number[] =>
  Array.from({ length: 140 }, (_, i) => Math.round(((i % 20) / 20) * scale * 10) / 10);

/** An end at `beat` on a 120 bpm map: seconds are half the beats. */
const end = (beat: number, kind: EndKind): CropEnd => ({ beat, seconds: beat / 2, kind });

const win = (start: number, stop: number, kind: EndKind): CropWindow => ({
  start_beat: start,
  end_beat: stop,
  start_s: start / 2,
  end_s: stop / 2,
  length_s: (stop - start) / 2,
  end_kind: kind,
  score: 0.5,
});

const PLAN_60: CropPlan = {
  enabled: true,
  reason: null,
  band: [54, 66],
  suggestions: [win(0, 128, "section"), win(128, 256, "phrase")],
  starts: [
    {
      beat: 0,
      seconds: 0,
      ends: [end(112, "bar4"), end(116, "bar"), end(128, "section"), end(132, "bar")],
    },
    { beat: 128, seconds: 64, ends: [end(240, "bar4"), end(256, "phrase")] },
  ],
};

const PLAN_120: CropPlan = {
  enabled: true,
  reason: null,
  band: [108, 132],
  suggestions: [win(0, 224, "section")],
  starts: [{ beat: 0, seconds: 0, ends: [end(224, "section"), end(240, "phrase")] }],
};

/** A 140 s song at 120 bpm with three sections and both lengths enabled. */
export const TIMELINE: Timeline = {
  map_id: "id0000000001",
  duration_s: 140,
  bpm: 120,
  hardest: "ExpertPlus",
  map_only: false,
  grid_drift_s: 0,
  nps: { Expert: series(4), ExpertPlus: series(6) },
  sections: [
    { start_beat: 0, end_beat: 128, start_s: 0, end_s: 64, nps: 3, intensity: 0.4 },
    { start_beat: 128, end_beat: 224, start_s: 64, end_s: 112, nps: 6, intensity: 1 },
    { start_beat: 224, end_beat: 280, start_s: 112, end_s: 140, nps: 2, intensity: 0.3 },
  ],
  lengths: { "60": PLAN_60, "120": PLAN_120 },
};
```

Create `frontend/tests/croplib.test.ts`:

```ts
import { describe, expect, test } from "vitest";
import { cropMap, getTimeline } from "../src/api/client";
import type { CropStart } from "../src/api/types";
import { toAlert } from "../src/lib/alerts";
import {
  clock,
  endFor,
  keepStart,
  pickEnd,
  secondsAt,
  snapEnd,
  snapStart,
  stepEnd,
  stepStart,
  suggestion,
} from "../src/lib/crop";
import { TIMELINE } from "./crophelpers";
import { mockFetch } from "./helpers";

const P60 = TIMELINE.lengths["60"];
const P120 = TIMELINE.lengths["120"];
const S0 = P60.starts[0] as CropStart;
const S128 = P60.starts[1] as CropStart;

describe("clock and pointer mapping", () => {
  test("clock rounds to tenths and carries into the minute", () => {
    expect(clock(0)).toBe("0:00.0");
    expect(clock(58)).toBe("0:58.0");
    expect(clock(64.04)).toBe("1:04.0");
    expect(clock(59.96)).toBe("1:00.0");
  });

  test("secondsAt maps a pointer to the song and clamps to it", () => {
    expect(secondsAt(500, 0, 1000, 140)).toBe(70);
    expect(secondsAt(-5, 0, 1000, 140)).toBe(0);
    expect(secondsAt(5000, 0, 1000, 140)).toBe(140);
    expect(secondsAt(100, 0, 0, 140)).toBe(0);
  });
});

describe("snapping", () => {
  test("the start snaps to the nearest section boundary", () => {
    expect(snapStart(P60, 10).beat).toBe(0);
    expect(snapStart(P60, 70).beat).toBe(128);
  });

  test("the end snaps to the nearest allowed end of that start", () => {
    expect(snapEnd(S0, 59).beat).toBe(116);
    expect(snapEnd(S0, 200).beat).toBe(132);
  });

  test("pickEnd prefers the strongest kind, then the length closest to the band middle", () => {
    expect(pickEnd(S0, [54, 66]).beat).toBe(128);
    expect(pickEnd(S128, [54, 66]).beat).toBe(256); // phrase beats bar4
  });

  test("endFor keeps a still-allowed end and re-picks otherwise", () => {
    expect(endFor(S0, 116, [54, 66]).beat).toBe(116);
    expect(endFor(S128, 128, [54, 66]).beat).toBe(256);
    expect(endFor(S0, null, [54, 66]).beat).toBe(128);
  });
});

describe("stepping", () => {
  test("arrows step to the next or previous start and stay at the ends", () => {
    expect(stepStart(P60, 0, 1).beat).toBe(128);
    expect(stepStart(P60, 128, 1).beat).toBe(128);
    expect(stepStart(P60, 128, -1).beat).toBe(0);
    expect(stepStart(P60, 0, -1).beat).toBe(0);
  });

  test("arrows step through every allowed end", () => {
    expect(stepEnd(S0, 128, -1, false).beat).toBe(116);
    expect(stepEnd(S0, 128, 1, false).beat).toBe(132);
    expect(stepEnd(S0, 132, 1, false).beat).toBe(132);
  });

  test("shift jumps to the next or previous section end only", () => {
    expect(stepEnd(S0, 116, 1, true).beat).toBe(128);
    expect(stepEnd(S0, 132, -1, true).beat).toBe(128);
    expect(stepEnd(S0, 128, -1, true).beat).toBe(128); // no earlier section end
  });
});

describe("selection", () => {
  test("suggestion is the best window, or null when the length is off", () => {
    expect(suggestion(P60)).toEqual({ start: 0, end: 128 });
    expect(suggestion({ ...P60, enabled: false })).toBeNull();
  });

  test("switching length keeps the start when the new plan has it", () => {
    expect(keepStart(P120, { start: 0, end: 128 })).toEqual({ start: 0, end: 224 });
    expect(keepStart(P120, { start: 128, end: 256 })).toBeNull();
    expect(keepStart(P60, null)).toBeNull();
  });
});

describe("client and alerts", () => {
  test("getTimeline reads the timeline of one map", async () => {
    const { calls } = mockFetch(() => TIMELINE);
    await expect(getTimeline("id0000000001")).resolves.toEqual(TIMELINE);
    expect(calls[0]?.pathname).toBe("/api/maps/id0000000001/timeline");
  });

  test("cropMap posts the chosen beats", async () => {
    const { fn } = mockFetch(() => ({ job: "j1" }));
    await expect(cropMap("id0000000001", 0, 128)).resolves.toEqual({ job: "j1" });
    const [path, init] = fn.mock.calls[0] as unknown as [string, RequestInit];
    expect(path).toBe("/api/maps/id0000000001/crop");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({ start_beat: 0, end_beat: 128 });
  });

  test("a failed crop job reads as a danger alert and a done one names the folder", () => {
    const failed = {
      id: "j",
      kind: "crop" as const,
      status: "failed" as const,
      error: "ffmpeg failed: x",
      result: null,
    };
    expect(toAlert(failed)).toMatchObject({ variant: "danger", title: "Crop failed" });
    const done = {
      id: "j",
      kind: "crop" as const,
      status: "done" as const,
      error: null,
      result: { folder: "Song [1 min]" },
    };
    expect(toAlert(done)).toMatchObject({
      variant: "success",
      title: "Cropped",
      message: "Written to Song [1 min].",
    });
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx --prefix frontend vitest run --root frontend tests/croplib.test.ts`
Expected: FAIL: `Failed to resolve import "../src/lib/crop"`.

Continued in [task-13b.md](task-13b.md).
