import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { CropTimes } from "../src/components/ChartHandles";
import { mmss, parseMmss, timeLabels } from "../src/lib/cropauto";

describe("time labels", () => {
  test("mm:ss rounds to whole seconds and parses back", () => {
    expect(mmss(0)).toBe("0:00");
    expect(mmss(64.4)).toBe("1:04");
    expect(mmss(599.6)).toBe("10:00");
    expect(parseMmss("2:30")).toBe(150);
    expect(parseMmss("02:30")).toBe(150);
    expect(parseMmss("2:60")).toBeNull();
    expect(parseMmss("230")).toBeNull();
  });

  test("a wide selection has start, length and end labels in that order", () => {
    render(<CropTimes selection={{ start_s: 60, end_s: 180 }} duration={300} />);
    const labels = screen.getAllByText(/^\d+:\d\d$/).map((n) => n.textContent);
    expect(labels).toEqual(["1:00", "2:00", "3:00"]);
  });

  test("a narrow selection collapses to the length alone", () => {
    render(<CropTimes selection={{ start_s: 100, end_s: 130 }} duration={300} />);
    expect(screen.getAllByText(/^\d+:\d\d$/).map((n) => n.textContent)).toEqual(["0:30"]);
  });

  test("the labels flank the bounds and the length sits at the middle", () => {
    const t = timeLabels(60, 180, 300);
    expect(t.narrow).toBe(false);
    expect([t.left, t.right]).toEqual([20, 60]);
  });
});
