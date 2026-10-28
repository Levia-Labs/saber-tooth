import { Link } from "react-router";
import { useNeighbors } from "../api/queries";
import { storedLibrarySearch } from "../lib/hooks";
import { Icon } from "./icons";

/** Previous and next map of the library's current list with the position, at the page bottom. */
export function MapFooter({ id }: { id: string }) {
  const neighbors = useNeighbors(id, storedLibrarySearch());
  if (!neighbors.data?.prev || !neighbors.data.next) return null;
  const { prev, next, index, total } = neighbors.data;
  const to = (target: string) => `/maps/${encodeURIComponent(target)}`;
  return (
    <nav className="map-footer" aria-label="Neighbouring maps">
      <Link className="back map-footer-prev" to={to(prev.id)} title={prev.title}>
        <Icon name="back" />
        <span className="map-footer-title">{prev.title}</span>
      </Link>
      <span className="map-footer-count" aria-label={`Map ${index} of ${total}`}>
        {index} / {total}
      </span>
      <Link className="back map-footer-next" to={to(next.id)} title={next.title}>
        <span className="map-footer-title">{next.title}</span>
        <Icon name="forward" />
      </Link>
    </nav>
  );
}
