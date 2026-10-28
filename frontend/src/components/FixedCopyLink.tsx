import { Link } from "react-router";
import type { MapItem } from "../api/types";
import { Alert } from "./Alert";

const COPY_MARK = "[saber-tooth]";

/** Banner on an original map's page linking to the fixed copy Fix wrote; nothing without one. */
export function FixedCopyLink({ item }: { item: MapItem }) {
  if (!item.fixed_copy_id) return null;
  const link = (
    <Link to={`/maps/${encodeURIComponent(item.fixed_copy_id)}`}>
      {item.fixed_copy_folder || item.fixed_copy_id}
    </Link>
  );
  return <Alert variant="success" title="Fixed copy ready" message={link} />;
}

/** Banner on a fixed copy's page linking back to its original. */
export function FixedCopyOf({ item }: { item: MapItem }) {
  if (!item.original_id || !item.folder.includes(COPY_MARK)) return null;
  const link = (
    <Link to={`/maps/${encodeURIComponent(item.original_id)}`}>
      {item.original_folder || item.original_id}
    </Link>
  );
  return <Alert variant="info" title="Fixed copy of" message={link} />;
}
