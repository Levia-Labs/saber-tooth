// Status metadata: labels, icons and which statuses mean a job is in flight.
import type { MapItem, StatusKey } from "../api/types";
import type { IconName } from "../components/icons";
import { mapHref } from "./backlink";
import { plural } from "./format";

export const STATUS_META: Record<StatusKey, { label: string; icon: IconName }> = {
  error: { label: "Errors", icon: "error" },
  warn: { label: "Warnings", icon: "warning" },
  crop: { label: "Qualified for crop", icon: "scissors" },
  ok: { label: "Good", icon: "ok" },
  incomplete: { label: "Not scanned, missing levels", icon: "unscanned" },
  unscanned: { label: "Not scanned", icon: "unscanned" },
  unreadable: { label: "Unreadable", icon: "unreadable" },
  scanning: { label: "Scanning", icon: "sweep" },
  applying: { label: "Applying", icon: "sweep" },
  fixing: { label: "Fixing", icon: "sweep" },
  queued: { label: "Queued", icon: "sweep" },
};

/** Filter list order in the status popover. */
export const STATUS_ORDER: readonly StatusKey[] = [
  "error",
  "warn",
  "crop",
  "ok",
  "incomplete",
  "unscanned",
  "unreadable",
  "scanning",
  "applying",
  "fixing",
  "queued",
];

const RUNNING: readonly StatusKey[] = ["scanning", "applying", "fixing", "queued"];

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
    case "crop":
      return STATUS_META.crop.label;
    case "scanning":
      return "Scanning";
    case "applying":
      return "Applying";
    case "fixing":
      return "Fixing";
    case "queued":
      return "Queued";
    case "unreadable":
      return item.parse_error ? `Unreadable: ${item.parse_error}` : "Unreadable";
    case "incomplete":
      return STATUS_META.incomplete.label;
    default:
      return "Not scanned";
  }
}

/** Map page tab a status opens: findings show on Status, a crop candidate on Crop. */
function statusTab(status: StatusKey): "status" | "crop" | undefined {
  if (status === "error" || status === "warn") return "status";
  return status === "crop" ? "crop" : undefined;
}

/** Map page address a status chip in the library opens. */
export function statusHref(id: string, item: StatusFields): string {
  return mapHref(id, { tab: statusTab(item.status), from: "library" });
}

/** Accessible name of a status chip that links to the map page. */
export function statusLinkLabel(item: StatusFields): string {
  if (item.status === "crop") return "Open crop";
  const tab = statusTab(item.status);
  return `${tab ? "Open status" : "Open map"}: ${statusLabel(item)}`;
}

export function mapName(item: Pick<MapItem, "title" | "folder">): string {
  return item.title || item.folder;
}

/** A fixed copy that was scanned with zero findings: nothing left to fix, scan or apply. */
export function isCleanCopy(item: Pick<MapItem, "status"> & Partial<Pick<MapItem, "original_id">>) {
  return Boolean(item.original_id) && item.status === "ok";
}

/** What waits on the map page: fixes to review and approved fixes not yet applied. */
export function reviewNeeds(item: Pick<MapItem, "pending" | "approved">): {
  count: number;
  text: string;
} {
  const parts: string[] = [];
  if (item.pending > 0) {
    parts.push(`${item.pending} ${item.pending === 1 ? "fix" : "fixes"} waiting for review`);
  }
  if (item.approved > 0) {
    const fixes = item.approved === 1 ? "fix" : "fixes";
    parts.push(`${item.approved} approved ${fixes} not applied`);
  }
  return { count: item.pending + item.approved, text: parts.join(", ") };
}
