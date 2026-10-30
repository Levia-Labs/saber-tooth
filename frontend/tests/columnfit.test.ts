import fc from "fast-check";
import { describe, expect, test } from "vitest";
import { BS_COLUMNS } from "../src/lib/bscolumns";
import {
  availableWidth,
  BREAKPOINTS,
  clampWidth,
  isResizable,
  LIBRARY_COLUMNS,
  LIMITS,
  tableMinWidth,
  type ColumnKey,
  type ColumnSet,
} from "../src/lib/columns";
import { contentMin, headerFit, NARROW_KEYS } from "../src/lib/columnfit";
import { JOB_COLUMNS } from "../src/lib/jobcolumns";
import { PL_COLUMNS } from "../src/lib/plcolumns";
import { LP_COLUMNS } from "../src/lib/lpcolumns";

const SETS: [string, ColumnSet][] = [
  ["library", LIBRARY_COLUMNS],
  ["beatsaver", BS_COLUMNS],
  ["playlists", PL_COLUMNS],
  ["local playlists", LP_COLUMNS],
];
/** The narrowest viewport each tier applies at; below 720 px rows are cards with no header. */
const NARROWEST = { wide: 1280, mid: 1100, compact: 720 } as const;

describe.each(SETS)("%s columns", (_name, set) => {
  test.each(BREAKPOINTS)("%s: every default is at least the width its header needs", (bp) => {
    for (const key of set.tracks[bp]) {
      expect(set.defaults[bp][key] ?? 0, `${bp} ${key}`).toBeGreaterThanOrEqual(
        headerFit(key, set),
      );
    }
  });

  test.each(BREAKPOINTS)("%s: the tracks fit at the narrowest viewport of the tier", (bp) => {
    expect(tableMinWidth(bp, {}, set)).toBeLessThanOrEqual(availableWidth(NARROWEST[bp]));
  });

  test("a dragged width never goes below the header fit", () => {
    fc.assert(
      fc.property(fc.constantFrom(...BREAKPOINTS), fc.integer({ min: -50, max: 900 }), (bp, px) => {
        for (const key of set.tracks[bp] as readonly ColumnKey[]) {
          if (!isResizable(key) || key === "status") continue;
          const floor = Math.min(headerFit(key, set), LIMITS[key]!.max);
          expect(clampWidth(key, px)).toBeGreaterThanOrEqual(floor);
        }
      }),
    );
  });
});

describe.each([...SETS, ["jobs", JOB_COLUMNS] as [string, ColumnSet]])(
  "%s compact tier",
  (_name, set) => {
    test("every narrow column is exactly its content minimum, so Title gets the rest", () => {
      const narrow = set.tracks.compact.filter((k) => NARROW_KEYS.includes(k));
      expect(narrow.length).toBeGreaterThan(0);
      for (const key of narrow) {
        expect(set.defaults.compact[key], key).toBe(contentMin(key, set));
      }
      const sum = narrow.reduce((n, k) => n + (set.defaults.compact[k] ?? 0), 0);
      expect(sum).toBe(narrow.reduce((n, k) => n + contentMin(k, set), 0));
    });
  },
);
