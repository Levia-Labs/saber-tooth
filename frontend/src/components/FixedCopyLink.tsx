import { Link } from "react-router";
import type { MapItem } from "../api/types";
import { Alert } from "./Alert";

/** Link from an original map to the fixed copy Fix wrote for it; nothing without one. */
export function FixedCopyLink({ item, banner = false }: { item: MapItem; banner?: boolean }) {
  if (!item.fixed_copy_id) return null;
  const link = (
    <Link to={`/maps/${encodeURIComponent(item.fixed_copy_id)}`}>
      {item.fixed_copy_folder || item.fixed_copy_id}
    </Link>
  );
  if (banner) return <Alert variant="success" title="Fixed copy ready" message={link} />;
  return <div className="fixed-copy">Fixed copy: {link}</div>;
}
