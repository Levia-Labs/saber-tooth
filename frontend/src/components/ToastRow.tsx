import type { Banner } from "../lib/announcements";
import type { AlertVariant } from "../lib/alerts";
import { Icon, type IconName } from "./icons";
import { useQuantizedWidth } from "./useQuantizedWidth";

const ICON: Record<AlertVariant, IconName> = {
  danger: "error",
  warning: "warning",
  info: "info",
  success: "ok",
};

interface Props {
  banner: Banner & { onOpen: () => void };
  onClose: () => void;
}

/**
 * A job toast in one row: spinner or outcome icon, title, rounds "x/y" when known, and a close
 * button. The body is one button that opens the Jobs page; the close button only closes.
 */
export function ToastRow({ banner: b, onClose }: Props) {
  const ref = useQuantizedWidth<HTMLDivElement>([b.title, b.message, b.rounds, b.variant]);
  const progress = b.variant === "progress";
  const variant: AlertVariant = progress ? "info" : (b.variant as AlertVariant);
  const urgent = variant === "danger" || variant === "warning";
  return (
    <div
      ref={ref}
      className={`alert alert-${variant} toast toast-row`}
      role={urgent ? "alert" : "status"}
      aria-live={urgent ? "assertive" : "polite"}
    >
      <button type="button" className="toast-open" onClick={b.onOpen}>
        <Icon
          name={progress ? "spinner" : ICON[variant]}
          className={progress ? "alert-icon alert-spin" : "alert-icon"}
        />
        <span className="alert-title">{b.title}</span>
        {progress && b.rounds && <span className="toast-rounds">{b.rounds}</span>}
        {!progress && b.message && <span className="toast-message">{b.message}</span>}
      </button>
      <button type="button" className="alert-dismiss" aria-label="Dismiss" onClick={onClose}>
        <Icon name="reject" />
      </button>
    </div>
  );
}
