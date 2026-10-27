import assert from "node:assert/strict";
import { test } from "node:test";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const url = pathToFileURL(resolve("src/saber_tooth/web/urlstate.js")).href;
const { DEFAULTS, apiQuery, encodeState, nextSort, parseState } = await import(url);

test("empty or garbage search parses to defaults", () => {
  assert.deepEqual(parseState(""), DEFAULTS);
  assert.deepEqual(parseState("?status=bogus&sort=nope&order=sideways"), DEFAULTS);
});

test("default state encodes to an empty string", () => {
  assert.equal(encodeState(DEFAULTS), "");
});

test("encode then parse round-trips non-default state", () => {
  const state = { q: "daft punk & co", status: "warn", sort: "errors", order: "desc" };
  assert.deepEqual(parseState(encodeState(state)), state);
});

test("only non-default keys reach the address bar", () => {
  assert.equal(encodeState({ ...DEFAULTS, status: "error" }), "?status=error");
  assert.equal(encodeState({ ...DEFAULTS, q: "  " }), "");
});

test("api query carries paging, sort and optional filters", () => {
  const base = new URLSearchParams(apiQuery(DEFAULTS, 0, 40));
  assert.equal(base.get("offset"), "0");
  assert.equal(base.get("limit"), "40");
  assert.equal(base.get("sort"), "title");
  assert.equal(base.get("order"), "asc");
  assert.equal(base.has("q"), false);
  assert.equal(base.has("status"), false);
  const full = new URLSearchParams(apiQuery({ ...DEFAULTS, q: " hi ", status: "ok" }, 80, 40));
  assert.equal(full.get("q"), "hi");
  assert.equal(full.get("status"), "ok");
  assert.equal(full.get("offset"), "80");
});

test("header clicks flip order on the same key and pick a natural order on a new one", () => {
  assert.deepEqual(nextSort(DEFAULTS, "title"), { sort: "title", order: "desc" });
  assert.deepEqual(nextSort(DEFAULTS, "status"), { sort: "status", order: "asc" });
  assert.deepEqual(nextSort(DEFAULTS, "errors"), { sort: "errors", order: "desc" });
});
