import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, test } from "vitest";

const read = (rel: string) =>
  readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf-8").replace(
    /\/\*[\s\S]*?\*\//g,
    "",
  );

interface Rule {
  selector: string;
  body: string;
}

/** Leaf rules; at-rule wrappers are skipped and their inner rules kept. */
function rules(text: string): Rule[] {
  return [...text.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter((m) => !m[1]!.trim().startsWith("@"))
    .map((m) => ({ selector: m[1]!.trim(), body: m[2]! }));
}

const vrRules = [
  ...rules(read("../src/styles/vr.css")),
  ...rules(read("../src/styles/vrmode.css")),
].filter((r) => r.selector.includes('[data-ui="vr"]'));
const COLOUR =
  /(^|[;\s])(background[\w-]*|color|border[\w-]*-color|filter|backdrop-filter|opacity|box-shadow|fill|stroke)\s*:/;

describe("VR changes sizes only, never colour or brightness", () => {
  test("no VR rule sets a colour, background, filter, opacity or shadow property", () => {
    const bad = vrRules.filter((r) => COLOUR.test(r.body)).map((r) => r.selector);
    expect(bad).toEqual([]);
  });

  test("no VR rule redeclares a colour token of the desktop :root", () => {
    const tokens = read("../src/styles/tokens.css").match(/--[\w-]+(?=:\s*#)/g) ?? [];
    expect(tokens.length).toBeGreaterThan(5);
    const redeclared = vrRules.flatMap((r) => tokens.filter((t) => r.body.includes(`${t}:`)));
    expect(redeclared).toEqual([]);
  });
});

describe("one VR height for every control", () => {
  const sized = vrRules.filter((r) => /min-height:\s*var\(--vr-target\)/.test(r.body));
  const all = sized.map((r) => r.selector).join(" ");

  test.each([
    "button",
    "a.btn",
    ".btn",
    "select",
    "summary",
    '[role="radio"]',
    '[role="tab"]',
    ".order-toggle",
    ".kebab-item",
    ".vr-target",
  ])("%s takes the target height", (sel) => {
    expect(all).toContain(sel);
  });

  test("icon-only and text buttons share the height; the shared rule is more specific than the desktop ones", () => {
    const shared = sized.find((r) => r.selector.includes(":not(.checkbox"));
    expect(shared?.selector).toMatch(/^:root\[data-ui="vr"\]/);
    const square = vrRules.find(
      (r) => r.selector.includes(".btn:is(.icon, .tap)") && /height/.test(r.body),
    );
    expect(square?.body).toMatch(/width:\s*var\(--vr-target\)/);
    expect(square?.body).toMatch(/height:\s*var\(--vr-target\)/);
  });

  test("tabs are the button height at desktop and in VR", () => {
    const pill = rules(read("../src/styles/pill.css")).find(
      (r) => r.selector === ".mode-switch .pill",
    );
    const button = rules(read("../src/styles/barslot.css")).find((r) =>
      r.selector.startsWith(".lib-bar .btn,"),
    );
    const px = (r?: Rule, p = "min-height") =>
      Number(new RegExp(`${p}:\\s*(\\d+)px`).exec(r?.body ?? "")?.[1]);
    expect(px(pill) + 2).toBe(px(button));
    const vrPill = vrRules.find((r) => r.selector.endsWith(".mode-switch .pill"));
    expect(vrPill?.body).toMatch(/min-height:\s*calc\(var\(--vr-target\) - 2px\)/);
  });
});

describe("VR icon-only buttons reuse the mobile label mechanism", () => {
  test("the VR rule hides .label-hide-mobile like the mobile breakpoint does", () => {
    const mobile = rules(read("../src/styles/overlays.css")).find(
      (r) => r.selector === ".label-hide-mobile",
    );
    const vr = vrRules.find((r) => r.selector === '[data-ui="vr"] .label-hide-mobile');
    expect(vr?.body.replace(/\s+/g, "")).toBe(mobile?.body.replace(/\s+/g, ""));
  });
});

describe("filter popover scale", () => {
  test("the portal content takes the VR scale in width and height", () => {
    const rule = vrRules.find((r) => r.selector === '[data-ui="vr"] .popover');
    expect(rule?.body).toMatch(/width:[^;]*var\(--ui-scale\)/);
    expect(rule?.body).toMatch(/max-height:[^;]*var\(--ui-scale\)/);
  });
});
