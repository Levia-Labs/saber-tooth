import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test } from "vitest";

const read = (rel: string) => readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf-8");
const css = read("../src/styles/about.css").replace(/\/\*[\s\S]*?\*\//g, "");

/** The body of the first rule for `selector` inside the media block that starts with `query`. */
function inMedia(query: string, selector: string): string {
  const start = css.indexOf(`@media ${query}`);
  expect(start, `media ${query}`).toBeGreaterThan(-1);
  const open = css.indexOf("{", start);
  let depth = 1;
  let i = open + 1;
  while (depth > 0 && i < css.length) {
    if (css[i] === "{") depth++;
    if (css[i] === "}") depth--;
    i++;
  }
  const block = css.slice(open + 1, i - 1);
  const rule = new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*\\{([^}]*)\\}`);
  return rule.exec(block)?.[1] ?? "";
}

test("the desktop masthead actions stay absolutely placed", () => {
  const body = /^\.masthead \.masthead-actions\s*\{([^}]*)\}/m.exec(css)?.[1] ?? "";
  expect(body).toMatch(/position:\s*absolute/);
});

test("under 420px the actions sit in their own row below the logo", () => {
  const body = inMedia("(max-width: 419px)", ".masthead .masthead-actions");
  expect(body).toMatch(/position:\s*static/);
  expect(body).toMatch(/transform:\s*none/);
  expect(body).toMatch(/width:\s*100%/);
  const inner = inMedia("(max-width: 419px)", ".masthead .masthead-inner");
  expect(inner).toMatch(/flex-wrap:\s*wrap/);
});
