import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "vitest";

const css = readFileSync(resolve(__dirname, "../src/styles/emptystate.css"), "utf-8").replace(
  /\/\*[\s\S]*?\*\//g,
  "",
);
const rule = (selector: string) =>
  new RegExp(`${selector.replace(/[.]/g, "\\.")}\\s*\\{([^}]*)\\}`).exec(css)?.[1] ?? "";

test("the empty state centres both ways in a column", () => {
  const body = rule(".empty-state");
  expect(body).toMatch(/flex-direction:\s*column/);
  expect(body).toMatch(/align-items:\s*center/);
  expect(body).toMatch(/justify-content:\s*center/);
  expect(body).toMatch(/min-height:/);
});

test("icon is 3rem and muted, text is larger than body text and muted", () => {
  const icon = rule(".empty-state .empty-state-icon");
  expect(icon).toMatch(/width:\s*3rem/);
  expect(icon).toMatch(/color:\s*var\(--muted\)/);
  const text = rule(".empty-state .empty-state-text");
  expect(text).toMatch(/color:\s*var\(--muted\)/);
  expect(parseFloat(/font-size:\s*([\d.]+)rem/.exec(text)?.[1] ?? "0")).toBeGreaterThan(1);
});
