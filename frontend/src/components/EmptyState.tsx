import type { ReactNode } from "react";
import { Icon, type IconName } from "./icons";
import { Spinner } from "./Spinner";

interface Props {
  icon?: IconName;
  text?: string;
  /** Secondary line under the text. */
  hint?: string;
  action?: ReactNode;
  /** While data is still on its way: an animated spinner with this accessible name replaces icon and text. */
  pending?: string;
  /** `error`: the children (an alert) fill the area instead of icon and text. */
  tone?: "error";
  children?: ReactNode;
}

/**
 * The message shown in place of an empty table or list: centred in the body area, a muted icon
 * above larger muted text, and an optional action button below.
 */
export function EmptyState(props: Props) {
  if (props.tone === "error") {
    return (
      <div className="empty-state empty-state-error" data-empty-state="true">
        {props.children}
        {props.action}
      </div>
    );
  }
  if (props.pending) {
    return (
      <div className="empty-state" data-empty-state="true">
        <Spinner label={props.pending} />
      </div>
    );
  }
  return (
    <div className="empty-state" data-empty-state="true">
      {props.icon && <Icon name={props.icon} className="empty-state-icon" />}
      <p className="empty-state-text">{props.text}</p>
      {props.hint && <p className="empty-state-hint">{props.hint}</p>}
      {props.action}
    </div>
  );
}
