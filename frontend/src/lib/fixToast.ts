// The toast for a finished fix: failed, incomplete, nothing to fix, or fixed.
import type { Job } from "../api/types";
import type { AnnounceInput } from "./announcements";
import { fixSummary, readFixReport } from "./fixreport";

/** Toast key shared with the fix's progress toast, so the outcome replaces it. */
export const fixKey = (name: string) => `Fix ${name}`;

export function fixToast(name: string, job: Job | null, error: string | null): AnnounceInput {
  const key = fixKey(name);
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
  if (rep.errorsAfter > 0 || rep.unfixed.length > 0) {
    return {
      key,
      variant: "danger",
      title: `Fix incomplete: ${name}`,
      message: `${fixSummary(rep)}. ${rep.errorsAfter} errors remain.`,
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
    title: `Fixed: written to ${rep.folder}`,
    message: `${fixSummary(rep)}.`,
    ...(link ? { link } : {}),
  };
}
