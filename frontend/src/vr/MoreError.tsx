/** Shown after a failed load-more: one Try again, no automatic retry. */
export function MoreError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="vr-more-error" role="alert">
      <p className="vr-help">Could not load more maps.</p>
      <button type="button" className="btn vr-big" onClick={onRetry}>
        Try again
      </button>
    </div>
  );
}
