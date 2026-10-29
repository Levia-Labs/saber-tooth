import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, test } from "vitest";

const read = (rel: string) => readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf-8");
const css = read("../src/styles/vr.css");
const bare = css.replace(/\/\*[\s\S]*?\*\//g, "");

interface Rule {
  selectors: string[];
  body: string;
}

/** Split a selector list on the commas outside parentheses, so `:where(a, b)` stays whole. */
function splitList(text: string): string[] {
  const out: string[] = [];
  let depth = 0;
  let current = "";
  for (const ch of text) {
    if (ch === "(") depth++;
    if (ch === ")") depth--;
    if (ch === "," && depth === 0) {
      out.push(current.trim());
      current = "";
    } else {
      current += ch;
    }
  }
  out.push(current.trim());
  return out.filter(Boolean);
}

/** Leaf rules only: `@container` wrappers are skipped, their inner rules are kept. */
function rules(): Rule[] {
  return [...bare.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .filter((m) => !m[1]!.trim().startsWith("@"))
    .map((m) => ({ selectors: splitList(m[1]!), body: m[2]! }));
}

const px = (name: string) => Number(new RegExp(`${name}:\\s*(\\d+)px`).exec(bare)?.[1]);

describe("vr.css", () => {
  test("sets the design sizes at 2x: 32 px text, 88 px targets, 32 px gaps", () => {
    expect(px("--vr-text")).toBeGreaterThanOrEqual(32);
    expect(px("--vr-target")).toBeGreaterThanOrEqual(88);
    expect(px("--vr-gap")).toBeGreaterThanOrEqual(32);
  });

  test("rem-sized regular pages scale 2x and the column is centered", () => {
    const root = rules().find((r) => r.selectors.includes(':root[data-ui="vr"]'));
    expect(root?.body).toMatch(/font-size:\s*32px/);
    const main = rules().find((r) => r.selectors.includes('[data-ui="vr"] main'));
    expect(main?.body).toMatch(/margin-inline:\s*auto/);
  });

  test("every rule is scoped under [data-ui=vr]", () => {
    const loose = rules()
      .flatMap((r) => r.selectors)
      .filter((s) => !s.startsWith('[data-ui="vr"]') && !s.startsWith(':root[data-ui="vr"]'));
    expect(loose).toEqual([]);
  });

  test("buttons, links styled as buttons, selects and inputs get 88 px targets", () => {
    const rule = rules().find((r) => /min-height:\s*var\(--vr-target\)/.test(r.body));
    expect(rule).toBeDefined();
    const text = rule!.selectors.join(" ");
    for (const needle of ["button", ".btn", "select", "input", '[role="radio"]', ".vr-target"]) {
      expect(text).toContain(needle);
    }
    expect(rule!.body).toMatch(/min-width:\s*var\(--vr-target\)/);
  });

  test("base text is the 32 px token and no literal font size is smaller", () => {
    const body = rules().find((r) => r.selectors.some((s) => s.endsWith(" body")));
    expect(body?.body).toMatch(/font-size:\s*var\(--vr-text\)/);
    const literals = [...bare.matchAll(/font-size:\s*(\d+(?:\.\d+)?)px/g)].map((m) => Number(m[1]));
    expect(literals.every((n) => n >= 22)).toBe(true);
  });

  test("gaps use the 32 px token and no literal gap is smaller", () => {
    expect(rules().some((r) => /gap:\s*var\(--vr-gap\)/.test(r.body))).toBe(true);
    const literals = [...bare.matchAll(/(?<![-\w])gap:\s*(\d+(?:\.\d+)?)px/g)].map((m) =>
      Number(m[1]),
    );
    expect(literals.every((n) => n >= 16)).toBe(true);
  });

  test("the focus ring is always visible and only the programmatic focus targets drop it", () => {
    const ring = rules().find((r) => r.selectors.some((s) => s.endsWith(":focus")));
    expect(ring?.body).toMatch(/outline:\s*4px solid/);
    const dropped = rules()
      .filter((r) => /outline:\s*none/.test(r.body))
      .flatMap((r) => r.selectors);
    expect(dropped.every((s) => /(main|h1):focus$/.test(s))).toBe(true);
  });

  test("hover tooltips are hidden", () => {
    const rule = rules().find((r) => r.selectors.some((s) => s.endsWith(".tooltip")));
    expect(rule?.body).toMatch(/display:\s*none/);
  });

  test("table rows and header are the desktop heights doubled", () => {
    expect(px("--row-h")).toBe(144);
    expect(px("--head-h")).toBe(88);
  });

  test("high contrast tokens: white ink on a dark panel", () => {
    expect(bare).toMatch(/--ink:\s*#ffffff/);
    expect(bare).toMatch(/--panel:\s*#1c1738/);
  });

  test("main.tsx imports vr.css last so it wins over the desktop rules", () => {
    const imports = [...read("../src/main.tsx").matchAll(/import "\.\/styles\/([\w-]+\.css)";/g)];
    expect(imports.at(-1)?.[1]).toBe("vr.css");
  });
});

describe("toast stack", () => {
  const alerts = read("../src/styles/alerts.css");
  const block = (sel: string) =>
    alerts.match(new RegExp(`(?:^|\\n)${sel.replace(/[.]/g, "\\.")} \\{([^}]*)\\}`))?.[1] ?? "";

  test("is centered and each toast fits its content up to a cap", () => {
    expect(block(".toast-stack")).toMatch(/margin:\s*0 auto/);
    expect(block(".toast-stack")).toMatch(/align-items:\s*center/);
    expect(block(".toast-stack .toast")).toMatch(/width:\s*fit-content/);
    expect(block(".toast-stack .toast")).toMatch(/max-width:/);
  });

  test("keeps a 16 px side gutter on a phone", () => {
    expect(alerts).toMatch(/max-width: 640px\)[^@]*width:\s*calc\(100% - 2rem\)/);
  });

  test("the VR stack centers its toasts too", () => {
    expect(bare).toMatch(/\.toast-stack \{[^}]*align-items:\s*center/);
  });
});
