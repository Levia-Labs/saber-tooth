import { expect, test } from "vitest";
import { CARD_MAX_PX } from "../src/lib/breakpoint";
import {
  availableWidth,
  defaultWidths,
  LIBRARY_COLUMNS,
  tableMinWidth,
  type ColumnSet,
} from "../src/lib/columns";
import { BS_COLUMNS } from "../src/lib/bscolumns";
import { JOB_COLUMNS } from "../src/lib/jobcolumns";
import { LP_COLUMNS } from "../src/lib/lpcolumns";
import { PL_COLUMNS } from "../src/lib/plcolumns";

const sets: Record<string, ColumnSet> = {
  library: LIBRARY_COLUMNS,
  beatsaver: BS_COLUMNS,
  jobs: JOB_COLUMNS,
  local: LP_COLUMNS,
  playlists: PL_COLUMNS,
};

/** The narrowest compact column set any list needs. */
const widest = Math.max(
  ...Object.values(sets).map((set) => tableMinWidth("compact", defaultWidths("compact", set), set)),
);

/** The smallest viewport whose available width holds the widest compact column set. */
function viewportThatFits(): number {
  let v = 300;
  while (availableWidth(v) < widest) v++;
  return v;
}

test("the lists turn into cards where even the compact columns do not fit", () => {
  const fits = viewportThatFits();
  // Tables from `fits` up; the first width above the card query must be one of them, and the card
  // query must not reach far above it.
  expect(fits).toBeLessThanOrEqual(Math.ceil(CARD_MAX_PX));
  expect(Math.ceil(CARD_MAX_PX) - fits).toBeLessThanOrEqual(40);
});

test("every list fits its compact columns at the first width above the card query", () => {
  const v = Math.ceil(CARD_MAX_PX + 0.02);
  for (const [name, set] of Object.entries(sets)) {
    const need = tableMinWidth("compact", defaultWidths("compact", set), set);
    expect(availableWidth(v) + 40, name).toBeGreaterThanOrEqual(need);
  }
});
