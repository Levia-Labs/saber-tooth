import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "vitest";

const read = (rel: string) =>
  readFileSync(resolve(__dirname, rel), "utf-8").replace(/\/\*[\s\S]*?\*\//g, "");
const pill = read("../src/styles/pill.css");
const block = pill.slice(pill.indexOf("@media (max-width: 1299.98px)"));
const pillTabs = readFileSync(resolve(__dirname, "../src/components/PillTabs.tsx"), "utf-8");

test("the bottom bar is the PillTabs group: same classes, no separate bar or square buttons", () => {
  expect(pillTabs).toContain('"mode-switch"');
  expect(pillTabs).toContain('className="pill"');
  const bar = /\.mode-switch\.section-tabs \{([^}]*)\}/.exec(block)?.[1] ?? "";
  // It keeps the pill container look: no override of border, radius, background or padding.
  expect(bar).not.toMatch(/border|background:|padding|border-radius/);
  const tab = /\.section-tabs \.pill \{([^}]*)\}/.exec(block)?.[1] ?? "";
  expect(tab).not.toMatch(/border|background|flex:/);
});

test("it floats: fixed, centered, off the edge by the margin and safe area, below the dialogs", () => {
  const bar = /\.mode-switch\.section-tabs \{([^}]*)\}/.exec(block)?.[1] ?? "";
  expect(bar).toMatch(/position:\s*fixed/);
  expect(bar).toMatch(/left:\s*50%/);
  expect(bar).toMatch(/transform:\s*translateX\(-50%\)/);
  expect(bar).toMatch(/bottom:\s*calc\(var\(--bottom-nav-margin\) \+ env\(safe-area-inset-bottom/);
  const z = Number(/z-index:\s*(\d+)/.exec(bar)?.[1]);
  expect(z).toBeGreaterThan(3); // over the sticky list header
  expect(z).toBeLessThan(40); // under the sheets, dialogs and popovers
});

test("icons are centered in the pill and the Jobs count sits on the icon", () => {
  const tab = /\.section-tabs \.pill \{([^}]*)\}/.exec(block)?.[1] ?? "";
  expect(tab).toMatch(/justify-content:\s*center/);
  expect(tab).toMatch(/position:\s*relative/);
  const count = /\.section-tabs \.pill \.tab-count \{([^}]*)\}/.exec(block)?.[1] ?? "";
  expect(count).toMatch(/position:\s*absolute/);
  expect(count).toMatch(/left:\s*calc\(50% \+/);
});

test("scroll containers end with the bottom space on mobile only, and toasts clear the bar", () => {
  expect(block).toMatch(/--bottom-nav-space:\s*calc\(/);
  expect(block).toMatch(
    /:is\(\.lib-scroll, \.page:not\(\.map-page\), \.about-page, \.map-scroll, \.fixes-scroll\) \{[^}]*padding-bottom:[^;]*--bottom-nav-space/,
  );
  expect(block).toMatch(/\.map-page \{[^}]*padding-bottom:\s*var\(--bottom-nav-space\)/);
  expect(block).toMatch(/\.toast-stack \{[^}]*--bottom-nav-space/);
  expect(block).toMatch(/:has\(\.map-page\) \.toast-stack \{[^}]*--map-footer-h/);
  // Outside the mobile query nothing reserves the space.
  expect(pill.slice(0, pill.indexOf("@media (max-width: 1299.98px)"))).not.toContain(
    "--bottom-nav-space",
  );
});
