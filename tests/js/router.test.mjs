import assert from "node:assert/strict";
import { test } from "node:test";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const url = pathToFileURL(resolve("src/saber_tooth/web/router.js")).href;
const { isPlainClick, mapHref, matchRoute } = await import(url);

test("static routes match, with or without a trailing slash", () => {
  assert.deepEqual(matchRoute("/"), { name: "library" });
  assert.deepEqual(matchRoute(""), { name: "library" });
  assert.deepEqual(matchRoute("/new"), { name: "new" });
  assert.deepEqual(matchRoute("/new/"), { name: "new" });
});

test("map routes decode the id", () => {
  assert.deepEqual(matchRoute("/maps/abc123"), { name: "map", id: "abc123" });
  assert.deepEqual(matchRoute("/maps/a%20b"), { name: "map", id: "a b" });
});

test("unknown, nested and malformed paths are not found", () => {
  for (const path of ["/maps", "/maps/", "/maps/a/b", "/api/maps", "/other", "/maps/%E0%A4%A"]) {
    assert.equal(matchRoute(path).name, "notfound", path);
  }
});

test("mapHref encodes ids and matches back", () => {
  assert.equal(mapHref("x/y z"), "/maps/x%2Fy%20z");
  assert.deepEqual(matchRoute(mapHref("x/y z")), { name: "map", id: "x/y z" });
});

test("only plain same-origin clicks on router paths are intercepted", () => {
  const origin = "http://localhost:8000";
  const click = { button: 0, defaultPrevented: false };
  const link = (href, extra = {}) => ({ href: origin + href, target: "", download: "", ...extra });
  assert.equal(isPlainClick(click, link("/maps/1"), origin), true);
  assert.equal(isPlainClick({ ...click, ctrlKey: true }, link("/maps/1"), origin), false);
  assert.equal(isPlainClick({ ...click, button: 1 }, link("/"), origin), false);
  assert.equal(isPlainClick(click, link("/", { target: "_blank" }), origin), false);
  assert.equal(isPlainClick(click, link("/api/maps"), origin), false);
  assert.equal(isPlainClick(click, { href: "https://example.com/new", target: "" }, origin), false);
});
