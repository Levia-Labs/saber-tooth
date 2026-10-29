import fc from "fast-check";
import { describe, expect, test } from "vitest";
import { columnVars, gridTemplate, tableMinWidth, TRACKS } from "../src/lib/columns";
import { scaleMediaText, scaledPx, scaleOf, unscaledPx } from "../src/vr/scale";

const scale = fc.double({ min: 1, max: 3, noNaN: true });

describe("scaleOf", () => {
  test("is the root size over 16 px and never below 1", () => {
    expect(scaleOf(32)).toBe(2);
    expect(scaleOf(24)).toBe(1.5);
    expect(scaleOf(16)).toBe(1);
    expect(scaleOf(12)).toBe(1);
    expect(scaleOf(Number.NaN)).toBe(1);
  });
});

describe("scaleMediaText", () => {
  test("multiplies every px length", () => {
    expect(scaleMediaText("(max-width: 1099px)", 2)).toBe("(max-width: 2198px)");
    expect(scaleMediaText("(min-width: 720px) and (max-width: 1279px)", 1.5)).toBe(
      "(min-width: 1080px) and (max-width: 1918.5px)",
    );
    expect(scaleMediaText("(prefers-reduced-motion: reduce)", 2)).toBe(
      "(prefers-reduced-motion: reduce)",
    );
  });

  test("scale 1 is the identity and scaling is monotonic in the length", () => {
    fc.assert(
      fc.property(fc.nat(4000), fc.nat(4000), scale, (a, b, s) => {
        const text = (n: number) => `(max-width: ${n}px)`;
        expect(scaleMediaText(text(a), 1)).toBe(text(a));
        const num = (t: string) => Number(/([\d.]+)px/.exec(t)![1]);
        const [lo, hi] = a <= b ? [a, b] : [b, a];
        expect(num(scaleMediaText(text(lo), s))).toBeLessThanOrEqual(
          num(scaleMediaText(text(hi), s)),
        );
      }),
    );
  });

  test("a desktop tier starts at the effective width: width over scale equals the desktop width", () => {
    fc.assert(
      fc.property(fc.integer({ min: 300, max: 2000 }), scale, (tier, s) => {
        const px = Number(/([\d.]+)px/.exec(scaleMediaText(`(max-width: ${tier}px)`, s))![1]);
        expect(Math.abs(px / s - tier)).toBeLessThan(0.01 / s + 1e-6);
      }),
    );
  });
});

describe("scaled column widths", () => {
  const widths = { title: 200, length: 88, bpm: 80, status: 96, actions: 140, cover: 64 };

  test("scale 1 keeps the desktop strings", () => {
    expect(gridTemplate("compact", widths)).toBe(gridTemplate("compact", widths, undefined, 1));
    expect(gridTemplate("compact", widths)).toBe("64px minmax(200px, 1fr) 88px 80px 96px 140px");
  });

  test("a wider scale grows every track and the minimum width in proportion", () => {
    fc.assert(
      fc.property(scale, (s) => {
        const one = tableMinWidth("compact", widths);
        const big = tableMinWidth("compact", widths, undefined, s);
        expect(big).toBeGreaterThanOrEqual(one - 1e-6);
        expect(Math.abs(big - one * s)).toBeLessThan(0.01);
        const cells = gridTemplate("compact", widths, undefined, s).split(" ").length;
        expect(cells).toBe(gridTemplate("compact", widths).split(" ").length);
      }),
    );
  });

  test("columnVars carries the scale for every tier", () => {
    const all = { wide: widths, mid: widths, compact: widths };
    const vars = columnVars(all, undefined, 2);
    expect(vars["--cols-compact"]).toBe("128px minmax(400px, 1fr) 176px 160px 192px 280px");
    expect(Object.keys(TRACKS)).toHaveLength(3);
  });

  test("a rendered drag width converts back to the desktop width", () => {
    fc.assert(
      fc.property(fc.integer({ min: 40, max: 600 }), scale, (w, s) => {
        expect(Math.abs(unscaledPx(scaledPx(w, s), s) - w)).toBeLessThan(0.01 / s + 1e-6);
      }),
    );
  });
});
