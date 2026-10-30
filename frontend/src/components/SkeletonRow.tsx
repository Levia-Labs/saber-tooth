/** Placeholder shape per column class: `bar` full, `short` bar, `pill`, `cover`, `check`, `btn` x2/x3. */
const KINDS: Record<string, readonly string[]> = {
  select: ["sk sk-check"],
  cover: ["sk sk-cover"],
  title: ["sk sk-bar"],
  sub: ["sk sk-bar short"],
  "sub-pill": ["sk sk-bar short", "sk sk-pill levels-inline"],
  author: ["sk sk-bar"],
  levels: ["sk sk-pill"],
  status: ["sk sk-pill"],
  tags: ["sk sk-bar"],
  short: ["sk sk-bar short"],
  actions: ["sk sk-btn", "sk sk-btn"],
  actions3: ["sk sk-btn", "sk sk-btn", "sk sk-btn"],
};

/** A column: `name` is the `col-` class; `kind` picks the placeholder shape (default: short bar). */
export type SkeletonCol = string | readonly [name: string, kind: string];

export const LIBRARY_COLS: readonly SkeletonCol[] = [
  "cover",
  "title",
  ["sub", "sub-pill"],
  "author",
  "levels",
  "length",
  "bpm",
  "env",
  "status",
  "actions",
];

/** Placeholder row with the same grid and height as a real row; no layout shift on swap. */
export function SkeletonRow({
  index,
  cols = LIBRARY_COLS,
}: {
  index: number;
  cols?: readonly SkeletonCol[];
}) {
  return (
    <div
      className="lib-row lib-grid skeleton-row"
      role="row"
      aria-rowindex={index + 2}
      aria-hidden="true"
      data-skeleton="true"
    >
      {cols.map((col) => {
        const [name, kind] = typeof col === "string" ? [col, col] : col;
        return (
          <div key={name} className={`col-${name}`} role="cell">
            {(KINDS[kind] ?? KINDS["short"]!).map((cls, i) => (
              <span key={i} className={cls} />
            ))}
          </div>
        );
      })}
    </div>
  );
}
