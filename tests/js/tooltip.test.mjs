import assert from "node:assert/strict";
import { test } from "node:test";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const url = pathToFileURL(resolve("src/saber_tooth/web/tooltip.js")).href;
const { placeTooltip } = await import(url);

const viewport = { width: 400, height: 600 };
const tip = { width: 200, height: 60 };

test("centers above the anchor when there is room", () => {
  const anchor = { left: 150, top: 300, width: 100, height: 40 };
  const out = placeTooltip({ anchor, tip, viewport });
  assert.equal(out.placement, "top");
  assert.equal(out.left, 100);
  assert.equal(out.top, 300 - 8 - 60);
});

test("flips below when the top edge is too close", () => {
  const anchor = { left: 150, top: 20, width: 100, height: 40 };
  const out = placeTooltip({ anchor, tip, viewport });
  assert.equal(out.placement, "bottom");
  assert.equal(out.top, 20 + 40 + 8);
});

test("clamps horizontally inside the viewport and keeps the arrow on the anchor", () => {
  const near = placeTooltip({
    anchor: { left: 0, top: 300, width: 40, height: 40 },
    tip,
    viewport,
  });
  assert.equal(near.left, 8);
  assert.equal(near.arrowX, 12);
  const far = placeTooltip({
    anchor: { left: 360, top: 300, width: 40, height: 40 },
    tip,
    viewport,
  });
  assert.equal(far.left, 400 - 200 - 8);
  assert.ok(far.arrowX <= tip.width - 12);
});

test("stays on screen when neither side fits", () => {
  const out = placeTooltip({
    anchor: { left: 100, top: 40, width: 40, height: 40 },
    tip: { width: 200, height: 90 },
    viewport: { width: 400, height: 120 },
  });
  assert.ok(out.top >= 8);
});

test("a tooltip wider than the viewport pins to the margin", () => {
  const out = placeTooltip({
    anchor: { left: 10, top: 300, width: 40, height: 40 },
    tip: { width: 500, height: 60 },
    viewport,
  });
  assert.equal(out.left, 8);
});
