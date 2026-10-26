import assert from "node:assert/strict";
import { test } from "node:test";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const url = pathToFileURL(resolve("src/saber_tooth/web/timeline.js")).href;
const { isNotesless, beatWindow, sliceBeats, layout, timelineHeight, wallRects } = await import(
  url
);

test("beatWindow pads to whole beats", () => {
  assert.deepEqual(beatWindow([{ beat: 2.5 }], [{ beat: 4.2 }]), { start: 2, end: 5 });
});

test("beatWindow of nothing is [0, 1]", () => {
  assert.deepEqual(beatWindow(), { start: 0, end: 1 });
  assert.deepEqual(beatWindow([], []), { start: 0, end: 1 });
});

test("sliceBeats dedupes and sorts", () => {
  assert.deepEqual(sliceBeats([{ beat: 3 }, { beat: 1 }, { beat: 3 }]), [1, 3]);
  assert.deepEqual(sliceBeats([]), []);
});

test("layout wraps slices into rows", () => {
  const l = layout(5, 200, 22);
  assert.equal(l.slicePitch, 100);
  assert.equal(l.perRow, 2);
  assert.equal(l.rows, 3);
  assert.equal(l.rowHeight, 90);
});

test("layout keeps at least one column and row", () => {
  const l = layout(0, 10, 22);
  assert.equal(l.perRow, 1);
  assert.equal(l.rows, 1);
});

test("timelineHeight uses the taller panel", () => {
  const before = [{ beat: 1 }];
  const after = [{ beat: 1 }, { beat: 2 }, { beat: 3 }];
  assert.equal(timelineHeight(before, after, 400), 24 + 2 * 90);
  assert.equal(timelineHeight([], [], 400), 24 + 90);
});

test("isNotesless is true only when both sides are empty", () => {
  assert.equal(isNotesless([], []), true);
  assert.equal(isNotesless([{ beat: 1 }], []), false);
});

test("wallRects maps walls to clipped grid rectangles", () => {
  const g = { x0: 10, y0: 20, cell: 10 };
  const wall = { beat: 4, x: 0, y: 0, duration: 2, width: 1, height: 5 };
  assert.deepEqual(wallRects([wall], { start: 5, end: 5 }, g), [{ x: 10, y: 20, w: 10, h: 30 }]);
  const crouch = { beat: 4, x: 1, y: 2, duration: 1, width: 2, height: 3 };
  assert.deepEqual(wallRects([crouch], { start: 4, end: 4 }, g), [{ x: 20, y: 20, w: 20, h: 10 }]);
});

test("wallRects skips walls outside the window", () => {
  const g = { x0: 0, y0: 0, cell: 10 };
  const wall = { beat: 4, x: 0, y: 0, duration: 2, width: 1, height: 5 };
  assert.deepEqual(wallRects([wall], { start: 7, end: 8 }, g), []);
  assert.deepEqual(wallRects([], { start: 0, end: 1 }, g), []);
});
