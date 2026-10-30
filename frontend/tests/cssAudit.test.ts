import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, test } from "vitest";

const DIR = join(__dirname, "..", "src", "styles");

/** Selector lists declared more than once inside the same at-rule context of one file. */
export function duplicateSelectors(css: string): string[] {
  const text = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const seen = new Set<string>();
  const dupes: string[] = [];
  const stack: string[] = [];
  let head = "";
  for (const ch of text) {
    if (ch === "{") {
      const sel = head.trim().replace(/\s+/g, " ");
      const key = `${stack.join(">")}|${sel}`;
      if (!sel.startsWith("@") && !stack.some((s) => s.startsWith("@keyframes"))) {
        if (seen.has(key)) dupes.push(sel);
        seen.add(key);
      }
      stack.push(sel);
      head = "";
    } else if (ch === "}") {
      stack.pop();
      head = "";
    } else if (ch === ";") {
      head = "";
    } else {
      head += ch;
    }
  }
  return dupes;
}

describe("stylesheets", () => {
  test("the audit finds a repeated selector", () => {
    expect(duplicateSelectors(".a{x:1}\n.a{y:2}\n@media (x){.a{z:3}}")).toEqual([".a"]);
  });

  for (const file of readdirSync(DIR).filter((f) => f.endsWith(".css"))) {
    test(`${file} declares each selector once`, () => {
      expect(duplicateSelectors(readFileSync(join(DIR, file), "utf8"))).toEqual([]);
    });
  }
});
