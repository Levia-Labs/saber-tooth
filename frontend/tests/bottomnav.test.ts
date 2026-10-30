import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test } from "vitest";

const read = (rel: string) =>
  readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf-8").replace(
    /\/\*[\s\S]*?\*\//g,
    "",
  );
const pill = read("../src/styles/pill.css");
const block = pill.slice(pill.indexOf("@media (max-width: 719px)"));

test("on mobile the section tabs are a fixed, full-width bottom bar with safe-area padding", () => {
  expect(block).toMatch(
    /:root:not\(\[data-ui="vr"\]\) \.mode-switch\.section-tabs \{[^}]*position:\s*fixed/,
  );
  const bar = /\.mode-switch\.section-tabs \{([^}]*)\}/.exec(block)?.[1] ?? "";
  expect(bar).toMatch(/left:\s*0/);
  expect(bar).toMatch(/right:\s*0/);
  expect(bar).toMatch(/bottom:\s*0/);
  expect(bar).toMatch(/env\(safe-area-inset-bottom/);
});

test("the tabs are equal-width targets of at least 48 px, and content and toasts clear the bar", () => {
  expect(block).toMatch(/\.section-tabs \.pill \{[^}]*flex:\s*1/);
  expect(block).toMatch(/\.section-tabs \.pill \{[^}]*min-height:\s*(4[89]|[5-9]\d)px/);
  expect(block).toMatch(/main:has\(\.section-tabs\)[^{]*\{[^}]*padding-bottom:[^;]*--bottom-nav-h/);
  expect(block).toMatch(/\.toast-stack[^{]*\{[^}]*--bottom-nav-h/);
});
