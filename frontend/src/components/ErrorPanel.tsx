import { Component, type ErrorInfo, type ReactNode } from "react";
import { Link } from "react-router";
import { errorMessage } from "../api/client";
import { libraryHref } from "../lib/hooks";
import { Alert } from "./Alert";

interface PanelProps {
  error: unknown;
  onRetry: () => void;
}

/** What went wrong in plain words, the technical message folded away, and the two ways out. */
export function ErrorPanel({ error, onRetry }: PanelProps) {
  return (
    <section className="page error-panel">
      <Alert
        variant="danger"
        pageHeading
        title="Something went wrong"
        message="This page hit a problem and could not be shown."
        details={[errorMessage(error)]}
        actions={
          <>
            <button type="button" className="btn primary" onClick={onRetry}>
              Try again
            </button>
            <Link className="btn plain" to={libraryHref()}>
              Back to library
            </Link>
          </>
        }
      />
    </section>
  );
}

interface BoundaryProps {
  children: ReactNode;
  /** Changing this value clears a caught error, e.g. when the route changes. */
  resetKey?: string;
}

interface BoundaryState {
  error: unknown;
  failed: boolean;
}

/** Catches render errors below it so one broken page never blanks the app shell. */
export class PageBoundary extends Component<BoundaryProps, BoundaryState> {
  override state: BoundaryState = { error: null, failed: false };

  static getDerivedStateFromError(error: unknown): BoundaryState {
    return { error, failed: true };
  }

  override componentDidCatch(error: unknown, info: ErrorInfo): void {
    console.error("Page render failed:", error, info.componentStack);
  }

  override componentDidUpdate(prev: BoundaryProps): void {
    if (this.state.failed && prev.resetKey !== this.props.resetKey) this.reset();
  }

  reset = (): void => this.setState({ error: null, failed: false });

  override render(): ReactNode {
    if (this.state.failed) return <ErrorPanel error={this.state.error} onRetry={this.reset} />;
    return this.props.children;
  }
}
