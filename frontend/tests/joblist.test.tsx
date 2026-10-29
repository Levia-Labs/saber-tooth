import { describe, expect, test } from "vitest";
import { activeCount, normalizeJobLists } from "../src/api/joblist";

const job = (id: string, status: string) => ({
  id,
  kind: "fix",
  status,
  map_id: null,
  title: "T",
  map_exists: false,
  created_at: "2026-10-29T10:00:00+00:00",
  started_at: null,
  updated_at: "2026-10-29T10:00:00+00:00",
  progress: null,
  progress_at: null,
  error: null,
  position: null,
});

describe("normalizeJobLists", () => {
  test("an empty or foreign body is an empty list, never a throw", () => {
    for (const body of [{}, null, "x", [], { running: "nope" }, { queued: [1, null] }]) {
      expect(normalizeJobLists(body)).toEqual({ running: [], queued: [], recent: [] });
    }
  });

  test("keeps well-formed rows", () => {
    const lists = normalizeJobLists({
      running: [job("a", "running")],
      queued: [job("b", "queued")],
      recent: [],
    });
    expect(lists.running.map((j) => j.id)).toEqual(["a"]);
    expect(activeCount(lists)).toBe(2);
  });
});
