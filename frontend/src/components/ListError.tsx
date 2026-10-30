import { errorMessage } from "../api/client";
import { errorToAlert } from "../lib/alerts";
import { BS_TIPS } from "../lib/bstips";
import { SpecAlert } from "./Alert";
import { EmptyState } from "./EmptyState";
import { Icon } from "./icons";
import { Tip } from "./Tip";

interface Props {
  error: unknown;
  onRetry: () => void;
  /** `first`: the first page failed and the list is replaced; `more`: a later page failed. */
  scope: "first" | "more";
  /** Headline, e.g. "Could not reach BeatSaver". */
  what: string;
  /** Render a structured alert instead of the inline error line with a button. */
  alert?: boolean;
}

/** Load failure of an infinite list: the first-page error state or the "load more" footer. */
export function ListError({ error, onRetry, scope, what, alert }: Props) {
  if (scope === "first") {
    return (
      <EmptyState
        tone="error"
        action={
          alert ? undefined : (
            <Tip text={BS_TIPS.retry}>
              <button type="button" className="btn plain" onClick={onRetry}>
                <Icon name="reset" />
                <span className="label-collapsible">Try again</span>
              </button>
            </Tip>
          )
        }
      >
        {alert ? (
          <SpecAlert spec={errorToAlert(error, what)} onRetry={onRetry} />
        ) : (
          <p className="err">
            {what}: {errorMessage(error)}
          </p>
        )}
      </EmptyState>
    );
  }
  return (
    <div className="lib-more">
      {alert ? (
        <SpecAlert spec={errorToAlert(error, what)} onRetry={onRetry} />
      ) : (
        <>
          <p className="err">
            {what}: {errorMessage(error)}
          </p>
          <button type="button" className="btn plain" onClick={onRetry}>
            <Icon name="expand" />
            <span className="label-collapsible">Load more</span>
          </button>
        </>
      )}
    </div>
  );
}
