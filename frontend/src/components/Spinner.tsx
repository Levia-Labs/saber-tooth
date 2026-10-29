import { Icon } from "./icons";

/**
 * The app's animated progress indicator: the turning ring used in job toasts. The label is the
 * accessible name only; nothing is shown as text. Reduced motion slows the turn (alerts.css).
 */
export function Spinner({ label }: { label: string }) {
  return (
    <span role="status" aria-label={label} className="spinner">
      <Icon name="spinner" className="alert-spin" />
    </span>
  );
}
