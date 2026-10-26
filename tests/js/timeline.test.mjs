import assert from "node:assert/strict";
import { test } from "node:test";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const url = pathToFileURL(resolve("src/saber_tooth/web/timeline.js")).href;
const { isNotesless, beatWindow, sliceBeats, layout, timelineHeight } = await import(url);

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
