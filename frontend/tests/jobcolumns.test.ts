import { describe, expect, test } from "vitest";
import { availableWidth, BREAKPOINTS, tableMinWidth } from "../src/lib/columns";
import { headerFit } from "../src/lib/columnfit";
import { JOB_COL, JOB_COLUMNS } from "../src/lib/jobcolumns";

/** The narrowest effective viewport each tier applies at (VR divides the window by its scale). */
const NARROWEST = { wide: 1280, mid: 1100, compact: 720 } as const;

describe("job columns", () => {
  test.each(BREAKPOINTS)("%s: the tracks fit the table at the tier's narrowest width", (bp) => {
    expect(tableMinWidth(bp, {}, JOB_COLUMNS)).toBeLessThanOrEqual(availableWidth(NARROWEST[bp]));
  });

  test.each(BREAKPOINTS)("%s: every default holds its header label and icons", (bp) => {
    for (const key of JOB_COLUMNS.tracks[bp]) {
      expect(JOB_COLUMNS.defaults[bp][key] ?? 0, `${bp} ${key}`).toBeGreaterThanOrEqual(
        headerFit(key, JOB_COLUMNS),
      );
    }
  });

  test("there is no Queue # or Rounds column; Status carries them", () => {
    for (const bp of BREAKPOINTS) {
      expect(JOB_COLUMNS.tracks[bp]).toEqual([
        JOB_COL.icon,
        JOB_COL.title,
        JOB_COL.length,
        JOB_COL.operation,
        JOB_COL.status,
        JOB_COL.actions,
      ]);
    }
  });
});
