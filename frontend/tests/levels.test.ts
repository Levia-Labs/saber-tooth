import { describe, expect, test } from "vitest";
import { LEVELS, levelColor, ringText } from "../src/lib/levels";

describe("levelColor", () => {
  test("is the colour LevelChips draws a present level in", () => {
    for (const l of LEVELS) expect(levelColor(l.key)).toBe(ringText(l.bg));
  });

  test("is undefined for an unknown level", () => {
    expect(levelColor("Nope")).toBeUndefined();
  });
});
