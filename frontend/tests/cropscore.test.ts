import { describe, expect, test } from "vitest";
import { partPercent, scoreColor, scoreStep } from "../src/lib/cropauto";

describe("score colour steps", () => {
  test.each([
    [0, 1],
    [0.099, 1],
    [0.1, 2],
    [0.5, 6],
    [0.999, 10],
    [1, 10],
    [-0.1, 1],
    [1.2, 10],
    [Number.NaN, 1],
  ])("fraction %s is step %s", (fraction, step) => {
    expect(scoreStep(fraction)).toBe(step);
  });

  test("the colour names the step's custom property", () => {
    expect(scoreColor(0.5)).toBe("var(--crop-step-6)");
  });

  test("a part's percentage is rounded and zero without a maximum", () => {
    const part = { key: "k", label: "L", points: 11, max_points: 15 };
    expect(partPercent(part)).toBe(73);
    expect(partPercent({ ...part, max_points: 0 })).toBe(0);
  });
});
