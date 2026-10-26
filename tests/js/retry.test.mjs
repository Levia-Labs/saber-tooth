import assert from "node:assert/strict";
import { test } from "node:test";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const url = pathToFileURL(resolve("src/saber_tooth/web/retry.js")).href;
const { isRetryable } = await import(url);

test("network errors, 5xx and 429 retry", () => {
  assert.equal(isRetryable(new TypeError("fetch failed")), true);
  assert.equal(isRetryable({ status: 503 }), true);
  assert.equal(isRetryable({ status: 429 }), true);
});

test("other 4xx surface immediately", () => {
  assert.equal(isRetryable({ status: 404 }), false);
  assert.equal(isRetryable({ status: 400 }), false);
});
