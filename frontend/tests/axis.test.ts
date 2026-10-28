import fc from "fast-check";
import { describe, expect, test } from "vitest";
import { npsTicks, tickLabel, timeTicks, yFrac } from "../src/lib/axis";

describe("time axis", () => {
  test("labels are mm:ss", () => {
    expect(tickLabel(0)).toBe("00:00");
    expect(tickLabel(65)).toBe("01:05");
    expect(tickLabel(600)).toBe("10:00");
  });

  test("a 140 s song gets round ticks", () => {
    expect(timeTicks(140)).toEqual([0, 30, 60, 90, 120]);
  });

  test("ticks start at zero, ascend, stay inside the song and stay few", () => {
    fc.assert(
      fc.property(fc.double({ min: 1, max: 20000, noNaN: true }), (d) => {
        const t = timeTicks(d);
        expect(t[0]).toBe(0);
        expect(t.length).toBeLessThanOrEqual(9);
        expect(t.at(-1) as number).toBeLessThanOrEqual(d);
        expect([...t].sort((a, b) => a - b)).toEqual(t);
      }),
    );
  });

  test("no ticks without a duration", () => {
    expect(timeTicks(0)).toEqual([]);
  });
});

describe("notes-per-second axis", () => {
  test("rounds the peak up to a round tick", () => {
    expect(npsTicks(6)).toEqual({ ticks: [0, 2, 4, 6], top: 6 });
    expect(npsTicks(6.3).top).toBe(8);
    expect(npsTicks(0)).toEqual({ ticks: [0, 1], top: 1 });
  });

  test("ticks run from 0 to a top that covers the peak", () => {
    fc.assert(
      fc.property(fc.double({ min: 0, max: 500, noNaN: true }), (peak) => {
        const { ticks, top } = npsTicks(peak);
        expect(ticks[0]).toBe(0);
        expect(ticks.at(-1)).toBe(top);
        expect(top).toBeGreaterThanOrEqual(peak);
        expect(ticks.length).toBeLessThanOrEqual(6);
      }),
    );
  });
});

describe("y position", () => {
  test("yFrac maps 0 to the bottom padding and the top tick to the top padding", () => {
    expect(yFrac(0, 8)).toBeCloseTo(0.05);
    expect(yFrac(8, 8)).toBeCloseTo(0.95);
  });
});
