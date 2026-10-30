import { useMemo } from "react";
import { Link } from "react-router";
import { usePlaylists } from "../../api/playlists";
import { filterPlaylists, sortPlaylists } from "../../lib/lpfilters";
import { loadLpState } from "../../lib/lpstate";
import { Icon } from "../icons";

/** Earlier and later playlist in the Playlists table's order (its saved sort and filter), with the position. */
export function PlaylistFooter({ id }: { id: string }) {
  const lists = usePlaylists();
  const order = useMemo(() => {
    const state = loadLpState();
    const all = lists.data?.items ?? [];
    const shown = sortPlaylists(filterPlaylists(all, state), state);
    // A playlist the filter hides keeps its place in the unfiltered order.
    return shown.some((p) => p.id === id) ? shown : sortPlaylists(all, state);
  }, [lists.data, id]);
  const at = order.findIndex((p) => p.id === id);
  const prev = order[(at - 1 + order.length) % order.length];
  const next = order[(at + 1) % order.length];
  if (at < 0 || !prev || !next) {
    return <div className="map-footer map-footer-empty" aria-hidden="true" />;
  }
  const to = (target: string) => `/playlists/${encodeURIComponent(target)}`;
  return (
    <nav className="map-footer" aria-label="Neighbouring playlists">
      <Link className="back map-footer-prev" to={to(prev.id)} title={prev.title}>
        <Icon name="back" />
        <span className="map-footer-title">{prev.title}</span>
      </Link>
      <span className="map-footer-count" aria-label={`Playlist ${at + 1} of ${order.length}`}>
        {at + 1} / {order.length}
      </span>
      <Link className="back map-footer-next" to={to(next.id)} title={next.title}>
        <span className="map-footer-title">{next.title}</span>
        <Icon name="forward" />
      </Link>
    </nav>
  );
}
