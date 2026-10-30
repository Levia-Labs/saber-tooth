import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test } from "vitest";

const read = (rel: string) =>
  readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf-8").replace(
    /\/\*[\s\S]*?\*\//g,
    "",
  );
const pill = read("../src/styles/pill.css");
const block = pill.slice(pill.indexOf("@media (max-width: 1299.98px)"));

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

test("the bar tabs share the full width equally, with centered icons and a full-button indicator", () => {
  const tab =
    /:root:not\(\[data-ui="vr"\]\) \.section-tabs \.pill \{([^}]*)\}/.exec(block)?.[1] ?? "";
  expect(tab).toMatch(/flex:\s*1 1 0(%|px)?;/);
  expect(tab).not.toMatch(/max-width/);
  expect(tab).toMatch(/justify-content:\s*center/);
  expect(tab).toMatch(/align-items:\s*center/);
  expect(tab).toMatch(/gap:\s*0/);
  expect(tab).toMatch(/margin:\s*0/);
  const bar = /\.mode-switch\.section-tabs \{([^}]*)\}/.exec(block)?.[1] ?? "";
  expect(bar).not.toMatch(/(?<![a-z-])padding(-inline)?:/);
  expect(bar).toMatch(/padding-left:\s*env\(safe-area-inset-left/);
  expect(bar).toMatch(/padding-right:\s*env\(safe-area-inset-right/);
  expect(bar).toMatch(/gap:\s*0/);
  expect(block).toMatch(
    /\.section-tabs \.pill\[aria-current="page"\] \{[^}]*box-shadow:[^}]*inset 0 -3px/,
  );
  expect(tab).toMatch(/position:\s*relative/);
  const count = /\.section-tabs \.pill \.tab-count \{([^}]*)\}/.exec(block)?.[1] ?? "";
  expect(count).toMatch(/position:\s*absolute/);
  expect(count).toMatch(/left:\s*calc\(50% \+/);
});
