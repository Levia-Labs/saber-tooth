import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, test } from "vitest";
import {
  CARD_QUERY,
  COMPACT_QUERY,
  DESKTOP_QUERY,
  MID_QUERY,
  MOBILE_MAX_PX,
  MOBILE_QUERY,
  TINY_QUERY,
  mediaFor,
} from "../src/lib/breakpoint";
import { scaleMediaText } from "../src/vr/scale";

const dir = resolve(__dirname, "../src/styles") + "/";
const sheets = readdirSync(dir)
  .filter((f) => f.endsWith(".css"))
  .map((f) => ({
    name: f,
    text: readFileSync(dir + f, "utf-8").replace(/\/\*[\s\S]*?\*\//g, ""),
  }));

/** Every `@media` prelude with a px width in a sheet. */
const widthQueries = (text: string) =>
  [...text.matchAll(/@media\s+([^{]*\bwidth:[^{]*)\{/g)].map((m) => m[1]!.trim());

/** The width queries that are not the mobile view: content tiers and tiny phones. */
const REMAINING: Record<string, string[]> = {
  "settings.css": ["(max-width: 1099px)"],
  "about.css": [
    "(max-width: 1399px)",
    "(max-width: 1099px)",
    "(max-width: 719px)",
    "(max-width: 419px)",
  ],
};

describe("the shared breakpoint", () => {
  test("the mobile query is below 1300 px and the desktop query starts there", () => {
    expect(MOBILE_MAX_PX).toBe(1299.98);
    expect(MOBILE_QUERY).toBe("(max-width: 1299.98px)");
    expect(DESKTOP_QUERY).toBe("(min-width: 1300px)");
    expect(Math.ceil(MOBILE_MAX_PX)).toBe(1300);
  });

  test("the tiny-phone query stays below the mobile one", () => {
    expect(Number(/(\d+)px/.exec(TINY_QUERY)![1])).toBeLessThan(MOBILE_MAX_PX);
  });

  test("outside VR the queries are as written; in VR mobile and cards never match", () => {
    for (const q of [MOBILE_QUERY, CARD_QUERY, MID_QUERY, COMPACT_QUERY, DESKTOP_QUERY]) {
      expect(mediaFor(q, false)).toBe(q);
    }
    expect(mediaFor(MOBILE_QUERY, true)).toBe("not all");
    expect(mediaFor(CARD_QUERY, true)).toBe("not all");
    expect(mediaFor(MID_QUERY, true)).toBe(MID_QUERY);
    expect(mediaFor(COMPACT_QUERY, true)).toBe(COMPACT_QUERY);
    expect(mediaFor(DESKTOP_QUERY, true)).toBe("(min-width: 1100px)");
    expect(mediaFor("(hover: none)", true)).toBe("(hover: none)");
  });

  test("VR scales the query by the UI scale", () => {
    expect(scaleMediaText(MOBILE_QUERY, 2)).toBe("(max-width: 2599.96px)");
  });

  test("every width media query in the stylesheets is the shared one or a listed remainder", () => {
    for (const { name, text } of sheets) {
      const allowed = new Set([
        MOBILE_QUERY,
        CARD_QUERY,
        DESKTOP_QUERY,
        MID_QUERY,
        COMPACT_QUERY,
        ...(REMAINING[name] ?? []),
      ]);
      for (const q of widthQueries(text)) {
        expect(allowed.has(q), `${name}: @media ${q}`).toBe(true);
      }
    }
  });

  test("the former mobile tiers are gone from every sheet but the listed remainders", () => {
    const old = /\((max|min)-width:\s*(719|640|1099|1100|1279)(px)/;
    for (const { name, text } of sheets) {
      const found = widthQueries(text).filter((q) => old.test(q) && !REMAINING[name]?.includes(q));
      expect(found, name).toEqual([]);
    }
  });

  test("the mobile query holds the bottom bar and the sheet; the card query the card rows", () => {
    const by = (name: string) => sheets.find((s) => s.name === name)!.text;
    expect(by("pill.css")).toContain(`@media ${MOBILE_QUERY}`);
    for (const f of ["rows.css", "alerts.css", "jobs.css", "beatsaver.css"]) {
      expect(by(f), f).toContain(`@media ${CARD_QUERY}`);
    }
  });

  test("no width media query hides a label: only the bottom bar does, by design", () => {
    for (const { name, text } of sheets) {
      for (const m of text.matchAll(/@medias+([^{]*width[^{]*){((?:[^{}]|{[^{}]*})*)}/g)) {
        const body = m[2]!;
        if (!body.includes("label-collapsible")) continue;
        const rules = body.split("}").filter((r) => r.includes("label-collapsible"));
        for (const r of rules) {
          expect(r, `${name}: ${m[1]}`).toMatch(/section-tabs/);
        }
      }
    }
  });
});
