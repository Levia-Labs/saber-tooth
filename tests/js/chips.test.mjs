import assert from "node:assert/strict";
import { test } from "node:test";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const url = pathToFileURL(resolve("src/saber_tooth/web/chips.js")).href;
const { pipLabel, statusKind, statusLabel } = await import(url);

test("status labels carry counts with correct plurals", () => {
  assert.equal(statusLabel({ status: "error", errors: 3, warnings: 0 }), "3 errors");
  assert.equal(statusLabel({ status: "error", errors: 1, warnings: 2 }), "1 error");
  assert.equal(statusLabel({ status: "warn", errors: 0, warnings: 1 }), "1 warning");
  assert.equal(statusLabel({ status: "warn", errors: 0, warnings: 4 }), "4 warnings");
});

test("fixed labels for ok, unscanned and unreadable", () => {
  assert.equal(statusLabel({ status: "ok" }), "All good");
  assert.equal(statusLabel({ status: "unscanned" }), "Not scanned");
  assert.equal(statusLabel({ status: "unreadable" }), "Unreadable");
});

test("unknown status falls back to unscanned", () => {
  assert.equal(statusKind("weird"), "unscanned");
  assert.equal(statusKind("warn"), "warn");
});

test("pip labels abbreviate known difficulties", () => {
  assert.equal(pipLabel("ExpertPlus"), "Ex+");
  assert.equal(pipLabel("Easy"), "E");
  assert.equal(pipLabel("Custom"), "Cu");
});
