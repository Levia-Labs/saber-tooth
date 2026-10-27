/** Placeholder row with the BeatSaver grid and height; no layout shift when data arrives. */
export function BsSkeletonRow({ index }: { index: number }) {
  return (
    <div
      className="lib-row lib-grid skeleton-row"
      role="row"
      aria-rowindex={index + 2}
      aria-hidden="true"
      data-skeleton="true"
    >
      <div className="col-select" role="cell">
        <span className="sk sk-check" />
      </div>
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
      <div className="col-rating" role="cell">
        <span className="sk sk-bar short" />
      </div>
      <div className="col-upvotes" role="cell">
        <span className="sk sk-bar short" />
      </div>
      <div className="col-length" role="cell">
        <span className="sk sk-bar short" />
      </div>
      <div className="col-bpm" role="cell">
        <span className="sk sk-bar short" />
      </div>
      <div className="col-tags" role="cell">
        <span className="sk sk-bar" />
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
