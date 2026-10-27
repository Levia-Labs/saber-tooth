// Turns jobs and errors into alert content, so pages never format message strings themselves.
import { ApiError } from "../api/client";
import type { Job, JobKind } from "../api/types";

export type AlertVariant = "danger" | "warning" | "info" | "success";
export type AlertActionKind = "retry" | "review";

export interface AlertSpec {
  variant: AlertVariant;
  /** Short, sentence case, no trailing colon. */
  title: string;
  /** What happened and what to do next, in plain words. */
  message: string;
  /** Raw error text, ids or per-map results; folded away by default. */
  details?: string[];
  action?: { kind: AlertActionKind; label: string };
}

const FAILED_TITLE: Record<JobKind, string> = {
  scan: "Scan failed",
  apply: "Apply failed",
  fix: "Fix failed",
  generate: "Generation failed",
  learn: "Learning failed",
};

const DONE_TITLE: Record<JobKind, string> = {
  scan: "Scan finished",
  apply: "Applied",
  fix: "Fixed",
  generate: "Map generated",
  learn: "Lightshows learned",
};

const RETRY = { kind: "retry", label: "Try again" } as const;
const GENERIC = "Something went wrong. Try again; the details show the exact reason.";

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

interface Reason {
  variant: AlertVariant;
  message: string;
}

/** Plain-words reading of a raw error message, or null when it is not recognised. */
function plainReason(raw: string): Reason | null {
  const text = raw.toLowerCase();
  if (text.includes("database is locked") || text.includes("busy")) {
    return { variant: "danger", message: "The database is busy. Wait a moment and try again." };
  }
  if (text.includes("timed out")) {
    return {
      variant: "warning",
      message:
        "The job ran longer than 30 minutes and was stopped. Check the library, then try again.",
    };
  }
  if (text.includes("cancel")) {
    return {
      variant: "info",
      message: "The job was cancelled. Start it again when you are ready.",
    };
  }
  if (
    text.includes("failed to fetch") ||
    text.includes("networkerror") ||
    text.includes("load failed")
  ) {
    return {
      variant: "danger",
      message: "The server could not be reached. Check that saber-tooth is running and try again.",
    };
  }
  if (text.includes("no such file") || text.includes("not found")) {
    return {
      variant: "danger",
      message:
        "A file or folder could not be found. Check the map folder still exists, then try again.",
    };
  }
  if (text.includes("permission") || text.includes("read-only")) {
    return {
      variant: "danger",
      message: "The folder could not be written to. Check its permissions, then try again.",
    };
  }
  return null;
}

function idList(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((v) => String(v));
  if (typeof value === "string" || typeof value === "number") return [String(value)];
  return [];
}

function count(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (Array.isArray(value)) return value.length;
  return null;
}

function failure(kind: JobKind, raw: string, result: Record<string, unknown>): AlertSpec {
  const conflict = idList(result["conflict"]);
  if (conflict.length > 0) {
    return {
      variant: "danger",
      title: FAILED_TITLE[kind],
      message:
        "Two approved fixes change the same notes. Review the highlighted fixes and apply again.",
      details: [`Conflicting fixes: ${conflict.join(", ")}`, raw],
      action: { kind: "review", label: "Review fixes" },
    };
  }
  const plain = plainReason(raw);
  if (plain && plain.variant !== "danger") {
    const title = plain.variant === "warning" ? "Job timed out" : "Job cancelled";
    return { variant: plain.variant, title, message: plain.message, details: [raw], action: RETRY };
  }
  return {
    variant: "danger",
    title: FAILED_TITLE[kind],
    message: plain?.message ?? GENERIC,
    details: [raw],
    action: RETRY,
  };
}

function success(job: Job, result: Record<string, unknown>): AlertSpec {
  const folder = result["folder"];
  const where = typeof folder === "string" ? `Written to ${folder}.` : "";
  const review = idList(result["needs_review"]);
  if (review.length > 0) {
    return {
      variant: "warning",
      title: `${plural(review.length, "fix needs", "fixes need")} another look`,
      message: `${where} Review ${review.length === 1 ? "it" : "them"} and apply again.`.trim(),
      details: [`Fixes to review: ${review.join(", ")}`],
      action: { kind: "review", label: "Review" },
    };
  }
  switch (job.kind) {
    case "scan": {
      const n = count(result["proposals"] ?? result["proposed"] ?? result["fixes"]);
      const message =
        n === null ? "Review the proposed fixes below." : `${plural(n, "fix", "fixes")} proposed.`;
      return { variant: "success", title: DONE_TITLE.scan, message };
    }
    case "apply":
      return {
        variant: "success",
        title: DONE_TITLE.apply,
        message: where || "The approved fixes were applied.",
      };
    case "fix":
      return { variant: "success", title: DONE_TITLE.fix, message: where || "The map was fixed." };
    case "generate":
      return {
        variant: "success",
        title: DONE_TITLE.generate,
        message: "Review the proposed map below.",
      };
    case "learn":
      return {
        variant: "success",
        title: DONE_TITLE.learn,
        message: "The new lightshows are ready to use.",
      };
  }
}

/** Alert for a finished job or a failed run; null while there is nothing to report. */
export function toAlert(job: Job | null, error: string | null = null): AlertSpec | null {
  if (!job && !error) return null;
  const result = job?.result ?? {};
  const raw = error ?? job?.error ?? null;
  if (raw !== null || job?.status === "failed") {
    return failure(job?.kind ?? "apply", raw ?? "job failed", result);
  }
  return job ? success(job, result) : null;
}

/** Alert for a failed request; `what` names what could not be done, e.g. "Could not load the map". */
export function errorToAlert(err: unknown, what: string): AlertSpec {
  const raw = err instanceof Error ? err.message : typeof err === "string" ? err : "unknown error";
  const details = [raw];
  if (err instanceof ApiError && err.status === 429) {
    return {
      variant: "warning",
      title: "Too many requests",
      message: "The server asked for a pause. Wait a few seconds and try again.",
      details,
      action: RETRY,
    };
  }
  if (err instanceof ApiError && err.status === 408) {
    return {
      variant: "warning",
      title: `${what}: the server is slow to answer`,
      message: "A long job may be running. Wait a moment and try again.",
      details,
      action: RETRY,
    };
  }
  if (err instanceof ApiError && err.status === 404) {
    return {
      variant: "danger",
      title: what,
      message: "It no longer exists. Go back to the library and pick another.",
      details,
    };
  }
  const plain = plainReason(raw);
  const server = err instanceof ApiError && err.status >= 500;
  const fallback = server ? "The server hit a problem. Try again in a moment." : GENERIC;
  return {
    variant: "danger",
    title: what,
    message: plain?.message ?? fallback,
    details,
    action: RETRY,
  };
}
