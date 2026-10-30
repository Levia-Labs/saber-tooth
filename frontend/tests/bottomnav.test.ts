import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "vitest";

const read = (rel: string) =>
  readFileSync(resolve(__dirname, rel), "utf-8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/\s+/g, " ");
const pill = read("../src/styles/pill.css");
const start = pill.indexOf("@media (max-width: 1299.98px)");
const block = pill.slice(start);
const pillTabs = readFileSync(resolve(__dirname, "../src/components/PillTabs.tsx"), "utf-8");
const bar = /\.mode-switch\.section-tabs \{([^}]*)\}/.exec(block)?.[1] ?? "";

test("the bottom bar is the PillTabs group: same classes, no separate bar or square buttons", () => {
  expect(pillTabs).toContain('"mode-switch"');
  expect(pillTabs).toContain('className="pill"');
  expect(bar).not.toMatch(/border|background:|padding|border-radius/);
  // The pill is not restyled: its only rule here positions the count.
  const own = /\.section-tabs \.pill \{([^}]*)\}/.exec(block)?.[1] ?? "";
  expect(own.replace(/\s+/g, "")).toBe("position:relative;");
  expect(block).not.toMatch(/\.section-tabs \.label-collapsible/);
});

test("the pill and the buttons share the control size tokens", () => {
  const base = pill.slice(0, start);
  expect(base).toMatch(/min-height:\s*calc\(var\(--control-h\) - 2px\)/);
  expect(base).toMatch(/\.mode-switch \.pill \{[^}]*padding:\s*0 0\.9rem/);
  expect(read("../src/styles/barslot.css")).toMatch(/min-height:\s*var\(--control-h\)/);
  expect(read("../src/styles/tokens.css")).toMatch(/--control-h:\s*42px/);
});

test("it floats: fixed, centered, off the edge by the margin and safe area, below the dialogs", () => {
  expect(bar).toMatch(/position:\s*fixed/);
  expect(bar).toMatch(/left:\s*0/);
  expect(bar).toMatch(/right:\s*0/);
  expect(bar).toMatch(/width:\s*fit-content/);
  expect(bar).toMatch(/margin:\s*0 auto/);
  expect(bar).toMatch(/bottom:\s*calc\(var\(--bottom-nav-margin\) \+ env\(safe-area-inset-bottom/);
  const z = Number(/z-index:\s*(\d+)/.exec(bar)?.[1]);
  expect(z).toBeGreaterThan(3); // over the sticky list header
  expect(z).toBeLessThan(40); // under the sheets, dialogs and popovers
});

test("the Jobs count sits on the icon once the label has collapsed", () => {
  const count =
    /\.section-tabs \.pill:has\(> \.label-collapsible\[data-collapsed\]\) \.tab-count \{([^}]*)\}/.exec(
      block,
    )?.[1];
  expect(count).toMatch(/position:\s*absolute/);
  expect(count).toMatch(/left:\s*calc\(50% \+/);
});

test("the end space is the bar height plus the gap below and the same gap above, plus safe area", () => {
  const space = /--bottom-nav-space:\s*calc\(([\s\S]*?)\);\s*\}/.exec(block)?.[1] ?? "";
  const norm = space.replace(/\s+/g, " ").trim();
  expect(norm).toBe(
    "var(--control-h) + var(--bottom-nav-margin) * 2 + env(safe-area-inset-bottom, 0px)",
  );
  // The bar sits the margin above the bottom edge: gap + bar + gap is what the content must clear.
  expect(bar).toMatch(/bottom:\s*calc\(var\(--bottom-nav-margin\) \+ env/);
});

test("each page ends in the space once, on mobile only: one padding per scroll container", () => {
  expect(block).toMatch(
    /:is\(\.lib-scroll, \.page:not\(\.map-page\)\) \{[^}]*padding-bottom:\s*var\(--bottom-nav-space\)/,
  );
  expect(block).toMatch(/\.map-page \{[^}]*padding-bottom:\s*var\(--bottom-nav-space\)/);
  // The wrappers that used to stack their own bottom padding add nothing.
  expect(block).toMatch(/main:has\(\.section-tabs\) \{[^}]*padding-bottom:\s*0/);
  expect(block).toMatch(/:is\(\.about, \.settings\) \{[^}]*padding-bottom:\s*0/);
  expect(block).not.toMatch(/\.about-page[^{]*\{[^}]*padding-bottom/);
  expect(block).not.toMatch(/\.map-scroll|\.fixes-scroll/);
  // Everything that uses the space is inside the mobile query.
  expect(pill.slice(0, start)).not.toContain("--bottom-nav-space");
  expect(block).toMatch(/\.toast-stack \{[^}]*--bottom-nav-space/);
  expect(block).toMatch(/:has\(\.map-page\) \.toast-stack \{[^}]*--map-footer-h/);
});
