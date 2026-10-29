import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "vitest";

const css = readFileSync(join(process.cwd(), "src", "styles", "about.css"), "utf-8");

// The About content was a centred 72rem column, narrower than the tab bar and the mode toggle
// above it; it now spans the same width as the library table.
test("the About content is not narrowed or centred", () => {
  const about = /(^|\n)\.about\s*\{([^}]*)\}/.exec(css)?.[2] ?? "";
  expect(about).not.toBe("");
  expect(about).not.toMatch(/max-width/);
  expect(about).not.toMatch(/margin:\s*0 auto/);
  expect(about).not.toMatch(/padding:\s*[\d.]+rem\s+[\d.]+rem/);
});
