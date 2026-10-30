import { Link } from "react-router";
import { Icon } from "./icons";

/** The "Back to list" link on map and playlist pages; `to` comes from `backHref`. */
export function BackLink({ to }: { to: string }) {
  return (
    <Link className="back" to={to}>
      <Icon name="back" />
      Back to list
    </Link>
  );
}
