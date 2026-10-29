import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "vitest";

// The About page showed "Version 0.0.0": the bundle took the version from frontend/package.json,
// which is never released. The project version lives in pyproject.toml.
test("the bundled app version is the project version from pyproject.toml", () => {
  const pyproject = readFileSync(join(process.cwd(), "..", "pyproject.toml"), "utf8");
  const version = /^version\s*=\s*"([^"]+)"/m.exec(pyproject)?.[1];
  expect(version).toBeTruthy();
  expect(__APP_VERSION__).toBe(version);
});
