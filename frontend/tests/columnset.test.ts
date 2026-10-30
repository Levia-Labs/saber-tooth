import fc from "fast-check";
import { describe, expect, test } from "vitest";
import type { Breakpoint, ColumnKey } from "../src/lib/columns";
import { defineColumns } from "../src/lib/columnset";

const KEYS: ColumnKey[] = [
  "cover",
  "title",
  "author",
  "levels",
  "length",
  "bpm",
  "status",
  "actions",
];
const BPS: Breakpoint[] = ["wide", "mid", "compact"];

const trackList = fc.uniqueArray(fc.constantFrom(...KEYS), { minLength: 1 });
const widthMap = fc.dictionary(fc.constantFrom(...KEYS), fc.integer({ min: 1, max: 600 }));
const tierMap = fc.record(
  { wide: widthMap, mid: widthMap, compact: widthMap },
  { requiredKeys: [] },
);

const spec = fc.record({
  tracks: fc.oneof(trackList, fc.record({ wide: trackList, mid: trackList, compact: trackList })),
  widths: widthMap,
  tier: tierMap,
});

describe("defineColumns", () => {
  test("every tier's tracks and widths match the descriptor", () => {
    fc.assert(
      fc.property(spec, ({ tracks, widths, tier }) => {
        const set = defineColumns({ tracks, widths, tier, storePrefix: "p.", legacyPrefixes: [] });
        for (const bp of BPS) {
          const expected = Array.isArray(tracks) ? tracks : tracks[bp];
          expect(set.tracks[bp]).toEqual(expected);
          expect(new Set(set.tracks[bp]).size).toBe(set.tracks[bp].length);
          const merged: Record<string, number> = { ...widths, ...tier[bp] };
          const want = Object.fromEntries(
            expected.filter((k) => k in merged).map((k) => [k, merged[k]]),
          );
          expect(set.defaults[bp]).toEqual(want);
          expect(
            Object.keys(set.defaults[bp]).every((k) => expected.includes(k as ColumnKey)),
          ).toBe(true);
        }
      }),
    );
  });
});
