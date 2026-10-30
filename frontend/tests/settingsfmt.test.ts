import { describe, expect, test } from "vitest";
import { clampJobs, formatBytes, percent } from "../src/lib/settingsfmt";

describe("formatBytes", () => {
  test.each([
    [0, "0 MB"],
    [512 * 1024 ** 2, "512 MB"],
    [1024 ** 3, "1.0 GB"],
    [12 * 1024 ** 3, "12 GB"],
    [1.5 * 1024 ** 3, "1.5 GB"],
  ])("%d is %s", (bytes, text) => expect(formatBytes(bytes)).toBe(text));

  test("an unknown or invalid size is an en dash", () => {
    expect(formatBytes(null)).toBe("–");
    expect(formatBytes(Number.NaN)).toBe("–");
    expect(formatBytes(-5)).toBe("–");
  });
});

describe("percent", () => {
  test("is whole and clamped to 0..100", () => {
    expect(percent(1, 4)).toBe(25);
    expect(percent(5, 4)).toBe(100);
    expect(percent(-1, 4)).toBe(0);
  });
  test("a zero or unknown total is 0", () => {
    expect(percent(1, 0)).toBe(0);
    expect(percent(1, null)).toBe(0);
    expect(percent(null, 4)).toBe(0);
  });
});

describe("clampJobs", () => {
  test("keeps the value between 1 and the maximum", () => {
    expect(clampJobs(0, 4)).toBe(1);
    expect(clampJobs(9, 4)).toBe(4);
    expect(clampJobs(3, 4)).toBe(3);
    expect(clampJobs(2.6, 4)).toBe(3);
    expect(clampJobs(Number.NaN, 4)).toBe(1);
    expect(clampJobs(2, 0)).toBe(1);
  });
});
