/** Loading placeholders shaped like the final layout, so nothing shifts when data arrives. */
function Loading() {
  return <span className="sr-only">Loading</span>;
}

/** Map page header: cover, title, mapper line, chips and the tempo row. */
export function MapHeadSkeleton() {
  return (
    <div className="maphead" aria-busy="true" data-skeleton="true">
      <span className="sk cover cover-big" />
      <div className="mapmeta" aria-hidden="true">
        <span className="sk sk-title" />
        <span className="sk sk-bar short" />
        <div className="metarow">
          <span className="sk sk-pill" />
          <span className="sk sk-pill" />
          <span className="sk sk-bar short sk-tempo" />
        </div>
      </div>
      <Loading />
    </div>
  );
}

/** Toolbar buttons plus collapsed proposal-card rows, same height as real collapsed cards. */
export function FixesSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div aria-busy="true" data-skeleton="true">
      <div className="map-toolbar" aria-hidden="true">
        <span className="sk sk-tool" />
        <span className="sk sk-tool" />
        <span className="sk sk-tool wide" />
        <span className="spacer" />
        <span className="sk sk-tool" />
        <span className="sk sk-tool" />
      </div>
      <div className="fixes-scroll" aria-hidden="true">
        {Array.from({ length: count }, (_, i) => (
          <article key={i} className="card card-skeleton">
            <header className="card-sum">
              <span className="sk sk-bar card-sk-label" />
              <span className="spacer" />
              <span className="sk sk-btn" />
              <span className="sk sk-btn" />
            </header>
          </article>
        ))}
      </div>
      <Loading />
    </div>
  );
}

/** Generic page fallback while a route chunk loads. */
export function PageSkeleton() {
  return (
    <div className="page" aria-busy="true" data-skeleton="true">
      <span className="sk sk-title" aria-hidden="true" />
      <span className="sk sk-bar" aria-hidden="true" />
      <Loading />
    </div>
  );
}
