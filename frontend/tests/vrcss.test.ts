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

const rem = (name: string) => Number(new RegExp(`${name}:\\s*([\\d.]+)rem`).exec(bare)?.[1]);

describe("vr.css", () => {
  test("sets the design sizes in rem: 1 rem text, 2.75 rem targets, 1 rem gaps", () => {
    expect(rem("--vr-text")).toBeGreaterThanOrEqual(1);
    expect(rem("--vr-target")).toBeGreaterThanOrEqual(2.75);
    expect(rem("--vr-gap")).toBeGreaterThanOrEqual(1);
  });

  test("the root size is fluid: the desktop 16 px at the least, 2x at 1920 px wide", () => {
    const root = rules().find((r) => r.selectors.includes(':root[data-ui="vr"]'));
    const m = /font-size:\s*clamp\((\d+)px,\s*(\d+)px \+ ([\d.]+)vw,\s*(\d+)px\)/.exec(
      root?.body ?? "",
    );
    expect(m).not.toBeNull();
    const [min, base, vw, max] = m!.slice(1).map(Number) as [number, number, number, number];
    const at = (w: number) => Math.min(max, Math.max(min, base + (vw / 100) * w));
    expect(min).toBe(16);
    expect(at(1920)).toBe(32);
    expect(at(1280)).toBeLessThan(at(1920));
    expect(at(800)).toBeGreaterThanOrEqual(16);
    const main = rules().find((r) => r.selectors.includes('[data-ui="vr"] main'));
    expect(main?.body).toMatch(/margin-inline:\s*auto/);
  });

  test("every rule is scoped under [data-ui=vr]", () => {
    const loose = rules()
      .flatMap((r) => r.selectors)
      .filter((s) => !s.startsWith('[data-ui="vr"]') && !s.startsWith(':root[data-ui="vr"]'));
    expect(loose).toEqual([]);
  });

  test("buttons, links styled as buttons, selects and inputs get 2.75 rem targets", () => {
    const rule = rules().find((r) => /min-height:\s*var\(--vr-target\)/.test(r.body));
    expect(rule).toBeDefined();
    const text = rule!.selectors.join(" ");
    for (const needle of ["button", ".btn", "select", "input", '[role="radio"]', ".vr-target"]) {
      expect(text).toContain(needle);
    }
    expect(rule!.body).toMatch(/min-width:\s*var\(--vr-target\)/);
  });

  test("base text is the 1 rem token and no literal font size is a px size", () => {
    const body = rules().find((r) => r.selectors.some((s) => s.endsWith(" body")));
    expect(body?.body).toMatch(/font-size:\s*var\(--vr-text\)/);
    const literals = [...bare.matchAll(/font-size:\s*(\d+(?:\.\d+)?)px/g)].map((m) => Number(m[1]));
    expect(literals).toEqual([]);
  });

  test("gaps use the 1 rem token and no literal px gap is under 16 px", () => {
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

  test("table rows and header are the desktop heights times --ui-scale, per width tier", () => {
    expect(bare).toMatch(/--row-h:\s*calc\(72px \* var\(--ui-scale\)\)/);
    expect(bare).toMatch(/--head-h:\s*calc\(44px \* var\(--ui-scale\)\)/);
    expect(bare).toMatch(/max-width: 1099px\)[^@]*--row-h:\s*calc\(92px \* var\(--ui-scale\)\)/);
    expect(bare).toMatch(/max-width: 719px\)[^@]*--row-h:\s*calc\(232px \* var\(--ui-scale\)\)/);
  });

  test("header buttons are not forced to the target width", () => {
    const rule = rules().find((r) =>
      r.selectors.some((s) => s.includes(".lib-head :where(button")),
    );
    expect(rule?.body).toMatch(/min-width:\s*0/);
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
