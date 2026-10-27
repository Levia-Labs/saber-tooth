import { Link } from "react-router";
import type { MapItem } from "../api/types";

/** Link from an original map to the fixed copy Fix wrote for it; nothing without one. */
export function FixedCopyLink({ item }: { item: MapItem }) {
  if (!item.fixed_copy_id) return null;
  return (
    <div className="fixed-copy">
      Fixed copy:{" "}
      <Link to={`/maps/${encodeURIComponent(item.fixed_copy_id)}`}>
        {item.fixed_copy_folder || item.fixed_copy_id}
      </Link>
    </div>
  );
}
