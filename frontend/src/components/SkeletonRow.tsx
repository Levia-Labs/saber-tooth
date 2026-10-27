/** Placeholder row with the same grid and height as a library row; no layout shift on swap. */
export function SkeletonRow({ index }: { index: number }) {
  return (
    <div
      className="lib-row lib-grid skeleton-row"
      role="row"
      aria-rowindex={index + 2}
      aria-hidden="true"
      data-skeleton="true"
    >
      <div className="col-cover" role="cell">
        <span className="sk sk-cover" />
      </div>
      <div className="col-title" role="cell">
        <span className="sk sk-bar" />
      </div>
      <div className="col-sub" role="cell">
        <span className="sk sk-bar short" />
        <span className="sk sk-pill levels-inline" />
      </div>
      <div className="col-author" role="cell">
        <span className="sk sk-bar" />
      </div>
      <div className="col-levels" role="cell">
        <span className="sk sk-pill" />
      </div>
      <div className="col-length" role="cell">
        <span className="sk sk-bar short" />
      </div>
      <div className="col-bpm" role="cell">
        <span className="sk sk-bar short" />
      </div>
      <div className="col-env" role="cell">
        <span className="sk sk-bar short" />
      </div>
      <div className="col-status" role="cell">
        <span className="sk sk-pill" />
      </div>
      <div className="col-actions" role="cell">
        <span className="sk sk-btn" />
        <span className="sk sk-btn" />
      </div>
    </div>
  );
}
