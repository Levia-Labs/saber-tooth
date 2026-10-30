// The toast for a finished fix: failed, incomplete (errors left), fixed with warnings, nothing to fix, or fixed.
import type { Job } from "../api/types";
import type { AnnounceInput } from "./announcements";
import { fixSummary, readFixReport } from "./fixreport";

/** Toast key shared with the fix's progress toast, so the outcome replaces it. */
export const fixKey = (mapId: string) => `Fix:${mapId}`;

export function fixToast(
  mapId: string,
  name: string,
  job: Job | null,
  error: string | null,
): AnnounceInput {
  const key = fixKey(mapId);
  if (error !== null || !job) {
    return {
      key,
      variant: "danger",
      title: `Fix failed: ${name}`,
      message: "The map could not be fixed. The original is unchanged.",
      details: [error ?? "job failed"],
    };
  }
  const rep = readFixReport(job);
  const link = rep.fixedId
    ? { to: `/maps/${encodeURIComponent(rep.fixedId)}`, label: "Open fixed map" }
    : undefined;
  // Severity follows the fixed copy's library status; counts are the fallback for old results.
  const remaining = Math.max(rep.errorsAfter, rep.unfixedErrors);
  const level =
    rep.status === "error" || rep.status === "warn"
      ? rep.status
      : rep.status === "ok" || rep.status === "crop"
        ? "ok"
        : remaining > 0
          ? "error"
          : rep.warningsAfter > 0
            ? "warn"
            : "ok";
  if (level === "error") {
    const n = Math.max(remaining, 1);
    return {
      key,
      variant: "danger",
      title: `Fix incomplete: ${name}`,
      message: `${fixSummary(rep)}. ${n} ${n === 1 ? "error remains" : "errors remain"}.`,
      details: rep.unfixed,
      ...(link ? { link } : {}),
    };
  }
  if (level === "warn") {
    const n = Math.max(rep.warningsAfter, 1);
    return {
      key,
      variant: "warning",
      title: `Fixed with ${n} ${n === 1 ? "warning" : "warnings"}: ${name}`,
      message: `${fixSummary(rep)}.`,
      details: rep.unfixed,
      ...(link ? { link } : {}),
    };
  }
  if (!rep.folder) {
    return {
      key,
      variant: "info",
      title: `Nothing to fix: ${name}`,
      message: "No changes were needed.",
    };
  }
  return {
    key,
    variant: "success",
    title: `Fixed: ${name}`,
    message: `${fixSummary(rep)}. Written to ${rep.folder}.`,
    ...(rep.unfixed.length > 0 ? { details: rep.unfixed } : {}),
    ...(link ? { link } : {}),
  };
}
