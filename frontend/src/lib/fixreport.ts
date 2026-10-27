// Reads the structured report of a finished fix job (docs/api.md, POST /api/maps/{id}/fix).
import type { Job } from "../api/types";

type Counts = Record<string, Record<string, Record<string, number>>>;

export interface FixReport {
  folder: string | null;
  fixedId: string | null;
  applied: number;
  errorsBefore: number;
  errorsAfter: number;
  difficultiesAdded: number;
  unfixed: string[];
}

const num = (v: unknown): number => (typeof v === "number" && Number.isFinite(v) ? v : 0);

function errorTotal(counts: unknown, rule?: string): number {
  let sum = 0;
  for (const diff of Object.values((counts ?? {}) as Counts)) {
    for (const [name, n] of Object.entries(diff?.["errors"] ?? {})) {
      if (rule === undefined || name === rule) sum += num(n);
    }
  }
  return sum;
}

function unfixedLine(u: Record<string, unknown>): string {
  const where = typeof u["difficulty"] === "string" ? `${u["difficulty"]}: ` : "";
  const what = String(u["message"] ?? u["rule"] ?? "finding");
  const why = typeof u["reason"] === "string" && u["reason"] ? ` (${u["reason"]})` : "";
  return `${where}${what}${why}`;
}

export function readFixReport(job: Job): FixReport {
  const r = job.result ?? {};
  const unfixed = Array.isArray(r["unfixed"]) ? (r["unfixed"] as Record<string, unknown>[]) : [];
  const after = r["after"] ?? r["before"];
  return {
    folder: typeof r["folder"] === "string" ? r["folder"] : null,
    fixedId: typeof r["fixed_id"] === "string" ? r["fixed_id"] : null,
    applied: num(r["applied"]),
    errorsBefore: errorTotal(r["before"]),
    errorsAfter: r["errors"] === undefined ? errorTotal(after) : num(r["errors"]),
    difficultiesAdded: errorTotal(r["before"], "missing-difficulty"),
    unfixed: unfixed.map(unfixedLine),
  };
}

export function fixSummary(rep: FixReport): string {
  const n = (v: number, one: string, many: string) => `${v} ${v === 1 ? one : many}`;
  return [
    `Errors ${rep.errorsBefore} -> ${rep.errorsAfter}`,
    `${n(rep.difficultiesAdded, "difficulty", "difficulties")} added`,
    `${n(rep.applied, "fix", "fixes")} applied`,
  ].join(", ");
}
