import type { Breakpoint, ColumnKey, ColumnSet } from "./columns";

type Tiers<T> = Record<Breakpoint, T>;

interface ColumnSetSpec extends Omit<ColumnSet, "tracks" | "defaults"> {
  /** One list shared by every tier, or one list per tier. */
  tracks: readonly ColumnKey[] | Tiers<readonly ColumnKey[]>;
  /** Default widths shared by every tier; only a tier's own tracks are kept. */
  widths: Record<string, number>;
  /** Per-tier widths that replace the shared ones. */
  tier?: Partial<Tiers<Record<string, number>>>;
}

/** Build a column set from a track list and a base width map plus per-tier overrides. */
export function defineColumns({ tracks, widths, tier = {}, ...rest }: ColumnSetSpec): ColumnSet {
  const perTier = (bp: Breakpoint) =>
    Array.isArray(tracks) ? tracks : (tracks as Tiers<readonly ColumnKey[]>)[bp];
  const out = { tracks: {}, defaults: {}, ...rest } as ColumnSet;
  for (const bp of ["wide", "mid", "compact"] as const) {
    const keys = perTier(bp);
    const merged = { ...widths, ...tier[bp] };
    out.tracks[bp] = keys;
    out.defaults[bp] = Object.fromEntries(
      keys.filter((k) => k in merged).map((k) => [k, merged[k]]),
    );
  }
  return out;
}
