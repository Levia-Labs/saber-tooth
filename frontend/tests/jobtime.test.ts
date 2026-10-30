import { describe, expect, test } from "vitest";
import { duration, staleMinutes } from "../src/lib/jobview";

const at = (iso: string) => Date.parse(iso);

describe("duration", () => {
  test("seconds, minutes and hours", () => {
    expect(duration("2026-10-29T10:00:00Z", at("2026-10-29T10:00:45Z"))).toBe("45 s");
    expect(duration("2026-10-29T10:00:00Z", at("2026-10-29T10:03:12Z"))).toBe("3 min 12 s");
    expect(duration("2026-10-29T10:00:00Z", at("2026-10-29T11:04:30Z"))).toBe("1 h 4 min");
  });
  test("bad or future input never shows a negative time", () => {
    expect(duration("nope", at("2026-10-29T10:00:00Z"))).toBe("0 s");
    expect(duration("2026-10-29T10:05:00Z", at("2026-10-29T10:00:00Z"))).toBe("0 s");
  });
});

describe("staleMinutes", () => {
  const base = {
    id: "a",
    kind: "fix" as const,
    status: "running" as const,
    map_id: null,
    title: "T",
    map_exists: false,
    created_at: "2026-10-29T10:00:00Z",
    started_at: "2026-10-29T10:00:00Z",
    updated_at: "2026-10-29T10:00:00Z",
    progress: null,
    progress_at: null,
    error: null,
    position: null,
    cancel_requested: false,
  };
  test("counts from the last progress, else from the start", () => {
    expect(staleMinutes(base, at("2026-10-29T10:09:59Z"))).toBeNull();
    expect(staleMinutes(base, at("2026-10-29T10:12:00Z"))).toBe(12);
    const moved = { ...base, progress: "round 2 of 6", progress_at: "2026-10-29T10:11:00Z" };
    expect(staleMinutes(moved, at("2026-10-29T10:12:00Z"))).toBeNull();
  });
  test("only running jobs go stale", () => {
    expect(staleMinutes({ ...base, status: "queued" }, at("2026-10-29T11:00:00Z"))).toBeNull();
  });
});
