import fc from "fast-check";
import { describe, expect, test } from "vitest";
import { formatClock, parseClock } from "../src/lib/clock";

describe("parseClock", () => {
  test("reads m:ss and mm:ss as seconds", () => {
    expect(parseClock("3:30")).toBe(210);
    expect(parseClock("03:30")).toBe(210);
    expect(parseClock(" 0:05 ")).toBe(5);
    expect(parseClock("12:00")).toBe(720);
  });

  test("empty text means no bound", () => {
    expect(parseClock("")).toBeNull();
    expect(parseClock("  ")).toBeNull();
  });

  test.each(["1:7x", "1:60", "-1:00", "1:7", "90", "1:", ":30", "1:30:00", "a:bc"])(
    "%j is invalid",
    (text) => {
      expect(parseClock(text)).toBeUndefined();
    },
  );

  test("formats whole seconds as mm:ss and round-trips", () => {
    expect(formatClock(210)).toBe("03:30");
    expect(formatClock(null)).toBe("");
    expect(formatClock(-5)).toBe("");
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 59_999 }), (s) => parseClock(formatClock(s)) === s),
    );
  });
});
