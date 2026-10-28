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
