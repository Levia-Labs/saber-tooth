import fc from "fast-check";
import { describe, expect, test } from "vitest";
import { cropMap, getTimeline } from "../src/api/client";
import type { CropStart } from "../src/api/types";
import { toAlert } from "../src/lib/alerts";
import {
  clampStart,
  clock,
  keepStart,
  moveEdge,
  nudgeEdge,
  pickEnd,
  sameSpan,
  sectionAt,
  secondsAt,
  shiftWindow,
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

describe("choosing an end", () => {
  test("pickEnd prefers the strongest kind, then the length closest to the band middle", () => {
    expect(pickEnd(S0, [54, 66]).beat).toBe(128);
    expect(pickEnd(S128, [54, 66]).beat).toBe(256); // phrase beats bar4
  });
});

describe("free edges", () => {
  const span = { start_s: 10, end_s: 70 };

  test("an edge moves to any second, not to a section or phrase point", () => {
    expect(moveEdge(span, "start", 12.34, 1, 140)).toEqual({ start_s: 12.34, end_s: 70 });
    expect(moveEdge(span, "end", 99.9, 1, 140)).toEqual({ start_s: 10, end_s: 99.9 });
  });

  test("the song edges and the minimum length clamp an edge", () => {
    expect(moveEdge(span, "start", -5, 1, 140).start_s).toBe(0);
    expect(moveEdge(span, "start", 200, 1, 140).start_s).toBe(69);
    expect(moveEdge(span, "end", 500, 1, 140).end_s).toBe(140);
    expect(moveEdge(span, "end", 0, 1, 140).end_s).toBe(11);
    expect(moveEdge(span, "end", 0, 2.5, 140).end_s).toBe(12.5);
  });

  test("nudges are 0.1 s, or 1 s with Shift, and do not drift", () => {
    expect(nudgeEdge(span, "end", 1, false, 1, 140).end_s).toBe(70.1);
    expect(nudgeEdge(span, "end", -1, true, 1, 140).end_s).toBe(69);
    let at = span;
    for (let i = 0; i < 30; i++) at = nudgeEdge(at, "start", 1, false, 1, 140);
    expect(at.start_s).toBe(13);
  });

  test("the whole window keeps its length and stays inside the song", () => {
    expect(shiftWindow(span, 33.3, 140)).toEqual({ start_s: 33.3, end_s: 93.3 });
    expect(shiftWindow(span, -4, 140)).toEqual({ start_s: 0, end_s: 60 });
    expect(shiftWindow(span, 500, 140)).toEqual({ start_s: 80, end_s: 140 });
  });

  test("any edge move or nudge ends inside the song and at least the minimum long", () => {
    const edge = fc.constantFrom("start" as const, "end" as const);
    fc.assert(
      fc.property(
        fc.double({ min: 0, max: 100, noNaN: true }),
        fc.double({ min: 1, max: 100, noNaN: true }),
        edge,
        fc.double({ min: -500, max: 500, noNaN: true }),
        (a, len, which, to) => {
          const start = { start_s: a, end_s: a + len };
          const moved = moveEdge(start, which, to, 1, 200);
          expect(moved.start_s).toBeGreaterThanOrEqual(0);
          expect(moved.end_s).toBeLessThanOrEqual(200);
          expect(moved.end_s - moved.start_s).toBeGreaterThanOrEqual(1 - 1e-9);
          const nudged = nudgeEdge(moved, which, 1, true, 1, 200);
          expect(nudged.end_s - nudged.start_s).toBeGreaterThanOrEqual(1 - 1e-9);
          expect(nudged.end_s).toBeLessThanOrEqual(200);
        },
      ),
    );
  });

  test("sameSpan compares to the millisecond", () => {
    expect(sameSpan(span, { start_s: 10.0001, end_s: 70 })).toBe(true);
    expect(sameSpan(span, { start_s: 10.01, end_s: 70 })).toBe(false);
  });
});

describe("selection", () => {
  test("suggestion is the best window, or null when the length is off", () => {
    expect(suggestion(P60)).toEqual({ start_s: 0, end_s: 64 });
    expect(suggestion({ ...P60, enabled: false })).toBeNull();
  });

  test("switching length keeps the start when the new plan has it", () => {
    expect(keepStart(P120, { start_s: 0, end_s: 64 })).toEqual({ start_s: 0, end_s: 112 });
    expect(keepStart(P120, { start_s: 64, end_s: 128 })).toBeNull();
    expect(keepStart(P120, { start_s: 12.3, end_s: 64 })).toBeNull();
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

describe("window and section helpers", () => {
  test("clampStart keeps the window inside the song", () => {
    expect(clampStart(-5, 64, 140)).toBe(0);
    expect(clampStart(50, 64, 140)).toBe(50);
    expect(clampStart(100, 64, 140)).toBe(76);
    expect(clampStart(10, 200, 140)).toBe(0);
  });

  test("sectionAt finds the band holding a second", () => {
    expect(sectionAt(TIMELINE.sections, 0)?.start_s).toBe(0);
    expect(sectionAt(TIMELINE.sections, 64)?.start_s).toBe(64);
    expect(sectionAt(TIMELINE.sections, 140)).toBeUndefined();
  });
});
