/** Shown on a map whose latest scan ran without audio analysis (empty-gap was not checked). */
export const NOT_ANALYSED_TIP = "Audio analysis was unavailable; rescan pending";

export function NotAnalysed({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <p className="not-analysed" role="status" title={NOT_ANALYSED_TIP}>
      Not analysed
    </p>
  );
}
