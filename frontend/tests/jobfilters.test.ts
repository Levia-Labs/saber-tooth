import fc from "fast-check";
import { describe, expect, test } from "vitest";
import type { JobView } from "../src/api/types";
import { KIND_ORDER } from "../src/lib/jobkinds";
import {
  DEFAULT_JOBS_STATE,
  encodeJobsState,
  filterJobs,
  JOB_STATES,
  jobLengthMs,
  jobsFilterCount,
  parseJobsState,
  sortJobs,
  type JobsState,
} from "../src/lib/jobfilters";

const T = "2026-10-29T10:00:00Z";
const j = (id: string, patch: Partial<JobView> = {}): JobView => ({
  id,
  kind: "fix",
  status: "queued",
  map_id: null,
  title: `Song ${id}`,
  map_exists: false,
  created_at: T,
  started_at: null,
  updated_at: T,
  progress: null,
  progress_at: null,
  error: null,
  position: null,
  cancel_requested: false,
  ...patch,
});
const ids = (rows: JobView[]) => rows.map((r) => r.id);

const rows = [
  j("done-old", { status: "done", updated_at: "2026-10-29T09:00:00Z" }),
  j("q2", { position: 2 }),
  j("done-new", { status: "failed", updated_at: "2026-10-29T09:30:00Z" }),
  j("run", { status: "running", started_at: T }),
  j("q1", { position: 1, kind: "scan", title: "Alpha" }),
];

describe("sortJobs", () => {
  test("default is running, queued by position, then most recent finished", () => {
    expect(ids(sortJobs(rows, DEFAULT_JOBS_STATE, 0))).toEqual([
      "run",
      "q1",
      "q2",
      "done-new",
      "done-old",
    ]);
  });

  test("descending flips the order", () => {
    const state = { ...DEFAULT_JOBS_STATE, ascending: false };
    expect(ids(sortJobs(rows, state, 0))[0]).toBe("done-old");
  });

  test("title sort is alphabetical", () => {
    const state: JobsState = { ...DEFAULT_JOBS_STATE, sort: "title" };
    expect(ids(sortJobs(rows, state, 0))[0]).toBe("q1");
  });

  test("length sort keeps queued rows last in either direction", () => {
    const long = j("long", { status: "done", started_at: T, updated_at: "2026-10-29T11:00:00Z" });
    const short = j("short", { status: "done", started_at: T, updated_at: "2026-10-29T10:01:00Z" });
    const set = [j("q", { position: 1 }), short, long];
    const asc = sortJobs(set, { ...DEFAULT_JOBS_STATE, sort: "length" }, 0);
    expect(ids(asc)).toEqual(["short", "long", "q"]);
    const desc = sortJobs(set, { ...DEFAULT_JOBS_STATE, sort: "length", ascending: false }, 0);
    expect(ids(desc)).toEqual(["long", "short", "q"]);
  });
});

describe("filterJobs", () => {
  test("filters by status, kind and title text", () => {
    const base = DEFAULT_JOBS_STATE;
    expect(ids(filterJobs(rows, { ...base, status: ["running"] }))).toEqual(["run"]);
    expect(ids(filterJobs(rows, { ...base, kind: ["scan"] }))).toEqual(["q1"]);
    expect(ids(filterJobs(rows, { ...base, q: "ALPH" }))).toEqual(["q1"]);
    expect(jobsFilterCount({ ...base, status: ["running", "done"], q: "x" })).toEqual({
      status: 2,
      kind: 0,
      title: 1,
    });
  });
});

describe("jobLengthMs", () => {
  test("running counts to now, finished to its last update, queued is empty", () => {
    const now = Date.parse(T) + 5000;
    expect(jobLengthMs(j("a", { status: "running", started_at: T }), now)).toBe(5000);
    expect(
      jobLengthMs(
        j("b", { status: "done", started_at: T, updated_at: "2026-10-29T10:01:00Z" }),
        now,
      ),
    ).toBe(60_000);
    expect(jobLengthMs(j("c"), now)).toBeNull();
  });
});

const stateArb = fc.record({
  status: fc.uniqueArray(fc.constantFrom(...JOB_STATES)),
  kind: fc.uniqueArray(fc.constantFrom(...KIND_ORDER)),
  q: fc.string({ maxLength: 40 }).map((s) => s.trim()),
  sort: fc.constantFrom("status", "title", "length", "created"),
  ascending: fc.boolean(),
});

describe("URL state", () => {
  test("round-trips any valid state", () => {
    fc.assert(
      fc.property(stateArb, (s) => {
        const state = s as JobsState;
        const back = parseJobsState(encodeJobsState(state).toString());
        expect(back.status).toEqual(JOB_STATES.filter((x) => state.status.includes(x)));
        expect(back.kind).toEqual(KIND_ORDER.filter((x) => state.kind.includes(x)));
        expect(back.q).toBe(state.q);
        expect(back.sort).toBe(state.sort);
        expect(back.ascending).toBe(state.ascending);
      }),
    );
  });

  test("any query string parses to whitelisted values", () => {
    fc.assert(
      fc.property(fc.string(), fc.string(), fc.string(), (a, b, c) => {
        const q = new URLSearchParams({ status: a, kind: b, sort: c, dir: a });
        const s = parseJobsState(q.toString());
        expect(s.status.every((x) => JOB_STATES.includes(x))).toBe(true);
        expect(s.kind.every((x) => KIND_ORDER.includes(x))).toBe(true);
        expect(["status", "title", "length", "created"]).toContain(s.sort);
      }),
    );
  });

  test("defaults encode to an empty query", () => {
    expect(encodeJobsState(DEFAULT_JOBS_STATE).toString()).toBe("");
  });
});
