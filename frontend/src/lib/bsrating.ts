// Client-side orders for BeatSaver, applied among the maps loaded so far. Pure functions.
import type { BsMap } from "../api/beatsaver";
import type { BsOrder, LocalSort } from "./bsfilters";

type Rated = Pick<BsMap, "upvotes" | "rating" | "song" | "name">;
type Tempo = Pick<BsMap, "bpm" | "song" | "name">;

const nameOf = (m: Pick<BsMap, "song" | "name">) => (m.song || m.name).toLowerCase();

/** Descending upvotes, then descending rating, then ascending name. */
export function compareByUpvotes(a: Rated, b: Rated): number {
  return b.upvotes - a.upvotes || b.rating - a.rating || nameOf(a).localeCompare(nameOf(b));
}

/** Descending rating percentage, then descending upvotes, then ascending name. */
export function compareByRating(a: Rated, b: Rated): number {
  return b.rating - a.rating || b.upvotes - a.upvotes || nameOf(a).localeCompare(nameOf(b));
}

/** Sorted copy; ascending flips the value keys, the name tie-break stays A to Z. */
function flipped<T extends Rated>(
  items: readonly T[],
  ascending: boolean,
  compare: (a: T, b: T) => number,
  same: (a: T, b: T) => boolean,
): T[] {
  const sign = ascending ? -1 : 1;
  return [...items].sort((a, b) => (same(a, b) ? compare(a, b) : sign * compare(a, b)));
}

/** Sorted copy by upvotes, then rating; ascending flips both, the name tie-break stays A to Z. */
export function sortByUpvotes<T extends Rated>(items: readonly T[], ascending: boolean): T[] {
  return flipped(
    items,
    ascending,
    compareByUpvotes,
    (a, b) => b.upvotes === a.upvotes && b.rating === a.rating,
  );
}

/** Sorted copy by rating percentage, then upvotes; ascending flips both. */
export function sortByRating<T extends Rated>(items: readonly T[], ascending: boolean): T[] {
  return flipped(
    items,
    ascending,
    compareByRating,
    (a, b) => b.upvotes === a.upvotes && b.rating === a.rating,
  );
}

const known = (bpm: number | null) => bpm !== null && Number.isFinite(bpm) && bpm > 0;

/** Sorted copy by tempo, fastest first; maps without a tempo come last in both directions. */
export function sortByBpm<T extends Tempo>(items: readonly T[], ascending: boolean): T[] {
  const sign = ascending ? 1 : -1;
  return [...items].sort((a, b) => {
    if (known(a.bpm) !== known(b.bpm)) return known(a.bpm) ? -1 : 1;
    const by = known(a.bpm) ? sign * ((a.bpm as number) - (b.bpm as number)) : 0;
    return by || nameOf(a).localeCompare(nameOf(b));
  });
}

/** The loaded maps in the order the active column asks for; the server order otherwise. */
export function sortLoaded(
  items: readonly BsMap[],
  order: BsOrder,
  local: LocalSort | null,
  ascending: boolean,
): BsMap[] {
  if (local === "upvotes") return sortByUpvotes(items, ascending);
  if (local === "bpm") return sortByBpm(items, ascending);
  return order === "Rating" ? sortByRating(items, ascending) : [...items];
}
