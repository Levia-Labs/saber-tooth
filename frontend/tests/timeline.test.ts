import { describe, expect, test } from "vitest";
import type { Wall } from "../src/api/types";
import {
  beatWindow,
  isNotesless,
  layout,
  sliceBeats,
  timelineHeight,
  wallLayers,
  wallRects,
} from "../src/lib/timeline";

const wall = (patch: Partial<Wall>): Wall => ({
  beat: 4,
  duration: 2,
  x: 0,
  y: 0,
  width: 1,
  height: 5,
  ...patch,
});

describe("timeline geometry", () => {
  test("beatWindow pads to whole beats", () => {
    expect(beatWindow([{ beat: 2.5 }], [{ beat: 4.2 }])).toEqual({ start: 2, end: 5 });
    expect(beatWindow()).toEqual({ start: 0, end: 1 });
    expect(beatWindow([], [])).toEqual({ start: 0, end: 1 });
  });

  test("sliceBeats dedupes and sorts", () => {
    expect(sliceBeats([{ beat: 3 }, { beat: 1 }, { beat: 3 }])).toEqual([1, 3]);
    expect(sliceBeats([])).toEqual([]);
  });

  test("layout wraps slices into rows and keeps one column and row", () => {
    expect(layout(5, 200, 22)).toEqual({ slicePitch: 100, perRow: 2, rows: 3, rowHeight: 90 });
    const tiny = layout(0, 10, 22);
    expect([tiny.perRow, tiny.rows]).toEqual([1, 1]);
  });

  test("timelineHeight uses the taller panel", () => {
    const after = [{ beat: 1 }, { beat: 2 }, { beat: 3 }];
    expect(timelineHeight([{ beat: 1 }], after, 400)).toBe(24 + 2 * 90);
    expect(timelineHeight([], [], 400)).toBe(24 + 90);
  });

  test("isNotesless is true only when nothing is drawn", () => {
    expect(isNotesless([], [])).toBe(true);
    expect(isNotesless([{ beat: 1 }], [])).toBe(false);
    expect(isNotesless([], [], [{ beat: 1 }])).toBe(false);
  });

  test("wallRects maps walls to clipped grid rectangles", () => {
    const g = { x0: 10, y0: 20, cell: 10 };
    expect(wallRects([wall({})], { start: 5, end: 5 }, g)).toEqual([
      { x: 10, y: 20, w: 10, h: 30 },
    ]);
    const crouch = wall({ x: 1, y: 2, duration: 1, width: 2, height: 3 });
    expect(wallRects([crouch], { start: 4, end: 4 }, g)).toEqual([{ x: 20, y: 20, w: 20, h: 10 }]);
  });

  test("wallRects skips walls outside the window", () => {
    const g = { x0: 0, y0: 0, cell: 10 };
    expect(wallRects([wall({})], { start: 7, end: 8 }, g)).toEqual([]);
    expect(wallRects([], { start: 0, end: 1 }, g)).toEqual([]);
  });

  test("context walls are painted first and fainter than changed walls", () => {
    const changed = wall({});
    const around = wall({ beat: 5, x: 3 });
    const [under, over] = wallLayers([changed], [around]);
    expect(under.walls).toEqual([around]);
    expect(over.walls).toEqual([changed]);
    expect(under.fill).not.toBe(over.fill);
    expect(wallLayers().map((l) => l.walls)).toEqual([[], []]);
  });
});
