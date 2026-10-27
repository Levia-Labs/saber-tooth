// Client-side Rating order for BeatSaver: upvotes, then rating, then name. Pure functions.
import type { BsMap } from "../api/beatsaver";

type Rated = Pick<BsMap, "upvotes" | "rating" | "song" | "name">;

const nameOf = (m: Rated) => (m.song || m.name).toLowerCase();

/** Descending upvotes, then descending rating, then ascending name. */
export function compareByUpvotes(a: Rated, b: Rated): number {
  return b.upvotes - a.upvotes || b.rating - a.rating || nameOf(a).localeCompare(nameOf(b));
}

/** Sorted copy; ascending flips the upvote and rating keys, the name tie-break stays A to Z. */
export function sortByUpvotes<T extends Rated>(items: readonly T[], ascending: boolean): T[] {
  const sign = ascending ? -1 : 1;
  const cmp = (a: T, b: T) => {
    const c = compareByUpvotes(a, b);
    return b.upvotes !== a.upvotes || b.rating !== a.rating ? sign * c : c;
  };
  return [...items].sort(cmp);
}
