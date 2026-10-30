import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import { mediaFor } from "../src/lib/breakpoint";
import { useBreakpoint } from "../src/lib/useColumns";
import { useRowEstimate } from "../src/components/LibraryTable";
import { scaleMediaText, scaleOf } from "../src/vr/scale";

const real = window.matchMedia;
afterEach(() => {
  window.matchMedia = real;
});

/** The VR root font of vr.css, `clamp(16px, 8px + 1.25vw, 48px)`, over the desktop 16 px. */
const vrScale = (width: number) => scaleOf(Math.min(48, Math.max(16, 8 + 0.0125 * width)));

/** Evaluate width queries as scale.ts does at this window width, in VR or not. */
function window_(width: number, vr: boolean) {
  const scale = vr ? vrScale(width) : 1;
  window.matchMedia = ((query: string) => {
    const text = scaleMediaText(mediaFor(query, vr), scale);
    const max = /\(max-width:\s*([\d.]+)px\)/.exec(text);
    const min = /\(min-width:\s*([\d.]+)px\)/.exec(text);
    const matches =
      text === "not all"
        ? false
        : max
          ? width <= Number(max[1])
          : min
            ? width >= Number(min[1])
            : false;
    return { ...real(query), media: query, matches };
  }) as typeof window.matchMedia;
}

describe("the layout by window width", () => {
  test.each([
    [1000, "compact", 180],
    [1299, "compact", 180],
    [1400, "wide", 72],
  ])("non-VR at %i px: %s tier, row estimate %i", (width, tier, rows) => {
    window_(width, false);
    expect(renderHook(() => useBreakpoint()).result.current).toBe(tier);
    expect(renderHook(() => useRowEstimate()).result.current).toBe(rows);
  });

  test.each([
    [1440, "compact"],
    [2560, "compact"],
    [3600, "mid"],
    [4200, "wide"],
  ])("VR at %i px keeps table rows (never the 180 px card) in the %s tier", (width, tier) => {
    window_(width, true);
    expect(renderHook(() => useBreakpoint()).result.current).toBe(tier);
    const rows = renderHook(() => useRowEstimate()).result.current;
    expect(rows).not.toBe(180);
    expect(rows).toBe(tier === "compact" ? 92 : 72);
  });
});
