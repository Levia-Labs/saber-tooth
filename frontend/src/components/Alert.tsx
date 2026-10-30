import type { ReactNode } from "react";
import type { AlertActionKind, AlertSpec, AlertVariant } from "../lib/alerts";
import { Icon, type IconName } from "./icons";
import { useQuantizedWidth } from "./useQuantizedWidth";

const ICON: Record<AlertVariant, IconName> = {
  danger: "error",
  warning: "warning",
  info: "info",
  success: "ok",
};

interface AlertProps {
  variant: AlertVariant;
  title: string;
  message?: ReactNode;
  /** Folded-away extras: raw error text, ids, per-map results. */
  details?: string[];
  actions?: ReactNode;
  onDismiss?: () => void;
  className?: string;
  /** Render the title as the page's h1 and focus target, for full-page alerts. */
  pageHeading?: boolean;
  /** Running job: a spinning spinner replaces the icon. */
  progress?: boolean;
  /** Toast: the width snaps up to a multiple of 50 px. */
  quantized?: boolean;
  /** Changes when the content does, so a quantized width is measured again. */
  fitKey?: string;
}

/** One status message: icon, title, plain-language text, optional details, actions and dismiss. */
export function Alert({
  variant,
  title,
  message,
  details,
  actions,
  onDismiss,
  className,
  pageHeading = false,
  progress = false,
  quantized = false,
  fitKey = "",
}: AlertProps) {
  const ref = useQuantizedWidth<HTMLDivElement>([quantized, fitKey]);
  const urgent = variant === "danger" || variant === "warning";
  const cls = ["alert", `alert-${variant}`, className ?? ""].filter(Boolean).join(" ");
  return (
    <div
      {...(quantized ? { ref } : {})}
      className={cls}
      role={urgent ? "alert" : "status"}
      aria-live={urgent ? "assertive" : "polite"}
    >
      <Icon
        name={progress ? "spinner" : ICON[variant]}
        className={progress ? "alert-icon alert-spin" : "alert-icon"}
      />
      <div className="alert-body">
        {pageHeading ? (
          <h1 className="alert-title" tabIndex={-1} data-page-heading>
            {title}
          </h1>
        ) : (
          <p className="alert-title">{title}</p>
        )}
        {message ? <p className="alert-message">{message}</p> : null}
        {details && details.length > 0 && (
          <details className="alert-details">
            <summary>Details</summary>
            {details.map((line) => (
              <pre key={line}>{line}</pre>
            ))}
          </details>
        )}
        {actions && <div className="alert-actions">{actions}</div>}
      </div>
      {onDismiss && (
        <button type="button" className="alert-dismiss" aria-label="Dismiss" onClick={onDismiss}>
          <Icon name="reject" />
        </button>
      )}
    </div>
  );
}

interface SpecProps {
  spec: AlertSpec | null;
  onRetry?: (() => void) | undefined;
  onReview?: (() => void) | undefined;
  onDismiss?: (() => void) | undefined;
  className?: string;
}

/** Renders a mapped alert; its action shows only when the page supplies the handler. */
export function SpecAlert({ spec, onRetry, onReview, onDismiss, className }: SpecProps) {
  if (!spec) return null;
  const handlers: Record<AlertActionKind, (() => void) | undefined> = {
    retry: onRetry,
    review: onReview,
  };
  const handler = spec.action ? handlers[spec.action.kind] : undefined;
  return (
    <Alert
      variant={spec.variant}
      title={spec.title}
      message={spec.message}
      {...(spec.details ? { details: spec.details } : {})}
      {...(onDismiss ? { onDismiss } : {})}
      {...(className ? { className } : {})}
      actions={
        spec.action && handler ? (
          <button type="button" className="btn plain" onClick={handler}>
            {spec.action.label}
          </button>
        ) : undefined
      }
    />
  );
}
