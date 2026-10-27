// Status metadata: labels, icons and which statuses mean a job is in flight.
import type { MapItem, StatusKey } from "../api/types";
import type { IconName } from "../components/icons";
import { plural } from "./format";

export const STATUS_META: Record<StatusKey, { label: string; icon: IconName }> = {
  error: { label: "Errors", icon: "error" },
  warn: { label: "Warnings", icon: "warning" },
  ok: { label: "Good", icon: "ok" },
  unscanned: { label: "Not scanned", icon: "unscanned" },
  unreadable: { label: "Unreadable", icon: "unreadable" },
  scanning: { label: "Scanning", icon: "sweep" },
  applying: { label: "Applying", icon: "sweep" },
  queued: { label: "Queued", icon: "sweep" },
};

/** Filter list order in the status popover. */
export const STATUS_ORDER: readonly StatusKey[] = [
  "error",
  "warn",
  "ok",
  "unscanned",
  "unreadable",
  "scanning",
  "applying",
  "queued",
];

const RUNNING: readonly StatusKey[] = ["scanning", "applying", "queued"];

export function isRunning(status: StatusKey): boolean {
  return RUNNING.includes(status);
}

type StatusFields = Pick<MapItem, "status" | "errors" | "warnings"> &
  Partial<Pick<MapItem, "parse_error">>;

/** The only text a chip shows: a count; null means icon only (also when unscanned). */
export function statusText(item: StatusFields): string | null {
  switch (item.status) {
    case "error":
      return String(item.errors);
    case "warn":
      return String(item.warnings);
    default:
      return null;
  }
}

/** Full meaning of a chip, used for its aria-label and tooltip. */
export function statusLabel(item: StatusFields): string {
  switch (item.status) {
    case "error":
      return plural(item.errors, "error");
    case "warn":
      return plural(item.warnings, "warning");
    case "ok":
      return "All good";
    case "scanning":
      return "Scanning";
    case "applying":
      return "Applying";
    case "queued":
      return "Queued";
    case "unreadable":
      return item.parse_error ? `Unreadable: ${item.parse_error}` : "Unreadable";
    default:
      return "Not scanned";
  }
}

export function mapName(item: Pick<MapItem, "title" | "folder">): string {
  return item.title || item.folder;
}
