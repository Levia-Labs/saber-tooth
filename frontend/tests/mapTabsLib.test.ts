import fc from "fast-check";
import { describe, expect, test } from "vitest";
import { MAP_TABS, parseTab, tabForKey, tabsFor, type MapTab } from "../src/lib/mapTabs";

const ALL = tabsFor(true);

describe("parseTab", () => {
  test("names the tab or falls back to status", () => {
    expect(parseTab("crop", ALL)).toBe("crop");
    expect(parseTab("delete", ALL)).toBe("delete");
    expect(parseTab(null, ALL)).toBe("status");
    expect(parseTab("crop", tabsFor(false))).toBe("status");
  });

  test("any string yields a tab on offer", () => {
    fc.assert(
      fc.property(fc.string(), fc.boolean(), (raw, canCrop) => {
        const offer = tabsFor(canCrop);
        expect(offer).toContain(parseTab(raw, offer));
      }),
    );
  });
});

describe("tabForKey", () => {
  test("moves with arrows, wrapping, and with Home and End", () => {
    expect(tabForKey("ArrowRight", "status", ALL)).toBe("crop");
    expect(tabForKey("ArrowRight", "delete", ALL)).toBe("status");
    expect(tabForKey("ArrowLeft", "status", ALL)).toBe("delete");
    expect(tabForKey("Home", "delete", ALL)).toBe("status");
    expect(tabForKey("End", "status", ALL)).toBe("delete");
    expect(tabForKey("a", "status", ALL)).toBeNull();
  });

  test("skips Crop when it is not offered", () => {
    expect(tabForKey("ArrowRight", "status", tabsFor(false))).toBe("delete");
  });

  test("a key never leaves the tabs on offer", () => {
    fc.assert(
      fc.property(
        fc.string(),
        fc.constantFrom(...MAP_TABS.map((t) => t.key)),
        fc.boolean(),
        (key, current: MapTab, canCrop) => {
          const offer = tabsFor(canCrop);
          const next = tabForKey(key, current, offer);
          if (next !== null) expect(offer).toContain(next);
        },
      ),
    );
  });
});
