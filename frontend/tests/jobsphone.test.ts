import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test } from "vitest";

const read = (rel: string) =>
  readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf-8").replace(
    /\/\*[\s\S]*?\*\//g,
    "",
  );
const css = read("../src/styles/jobs.css");
const phone = css.slice(css.lastIndexOf("@media (max-width: 719.98px)"));

test("on a phone the Jobs table drops Image, Length and Operation and never forces a minimum width", () => {
  for (const col of ["jc-cover", "jc-length", "jc-operation"]) {
    expect(phone).toContain(`.jobs-grid > .${col}`);
  }
  expect(phone).toMatch(/\.jc-operation \{[^}]*display:\s*none/);
  expect(phone).toMatch(/\.jobs-table\.lib-table \{[^}]*min-width:\s*0/);
  expect(phone).toMatch(/grid-template-columns:\s*minmax\(0, 1fr\) 106px 64px/);
});
