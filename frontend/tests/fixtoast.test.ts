import { describe, expect, test } from "vitest";
import type { Job } from "../src/api/types";
import { fixToast } from "../src/lib/fixToast";

const job = (result: Record<string, unknown>): Job =>
  ({ id: "j", kind: "fix", status: "done", error: null, result }) as Job;
const base = {
  folder: "F [saber-tooth]",
  fixed_id: "id1",
  applied: 3,
  errors: 0,
  before: {},
  after: {},
};

describe("fixToast classification", () => {
  test("errors remaining is an error toast with the count", () => {
    const t = fixToast("m", "Song", job({ ...base, errors: 2 }), null);
    expect(t.variant).toBe("danger");
    expect(t.title).toBe("Fix incomplete: Song");
    expect(t.message).toContain("2 errors remain");
  });

  test("an unfixed error finding also counts as an error", () => {
    const u = [{ difficulty: "Hard", severity: "error", message: "bad", reason: "r" }];
    expect(fixToast("m", "Song", job({ ...base, unfixed: u }), null).variant).toBe("danger");
  });

  test("zero errors with an unfixed warning is a warning toast, listed with its difficulty", () => {
    const u = [{ difficulty: "Normal", severity: "warning", message: "no notes for 16.0 beats" }];
    const t = fixToast("m", "DAMIDAMI", job({ ...base, unfixed: u }), null);
    expect(t.variant).toBe("warning");
    expect(t.title).toBe("Fixed with 1 warning: DAMIDAMI");
    expect(t.message).not.toMatch(/errors? remain/);
    expect(t.details).toEqual(["Normal: no notes for 16.0 beats"]);
  });

  test("warnings left after the rescan make a warning toast", () => {
    const after = { Easy: { errors: {}, warnings: { a: 2, b: 1 } } };
    const t = fixToast("m", "Song", job({ ...base, after }), null);
    expect(t.variant).toBe("warning");
    expect(t.title).toBe("Fixed with 3 warnings: Song");
  });

  test("nothing remaining is a success toast", () => {
    const t = fixToast("m", "Song", job(base), null);
    expect(t.variant).toBe("success");
    expect(t.title).toBe("Fixed: Song");
  });
});

describe("fixToast follows the fixed copy's status", () => {
  const note = (difficulty: string, message: string) => ({
    difficulty,
    severity: "warn",
    message,
    reason: "no verified fix",
  });

  test("Goodbye: four identical unfixed notes under status ok are one success with a count", () => {
    const u = Array.from({ length: 4 }, () =>
      note("ExpertPlus", "centre note blocks view of the next note"),
    );
    const t = fixToast("m", "Goodbye", job({ ...base, status: "ok", unfixed: u }), null);
    expect(t.variant).toBe("success");
    expect(t.title).toBe("Fixed: Goodbye");
    expect(t.details).toEqual([
      "ExpertPlus: centre note blocks view of the next note (no verified fix) ×4",
    ]);
  });

  test("Bury The Light: a stored ok status wins over unfixed notes and keeps the link", () => {
    const u = [
      note("ExpertPlus", "hand travels 11.2 cells/s"),
      note("ExpertPlus", "hand travels 11.2 cells/s"),
    ];
    const t = fixToast("m", "Bury The Light", job({ ...base, status: "crop", unfixed: u }), null);
    expect(t.variant).toBe("success");
    expect(t.link?.label).toBe("Open fixed map");
  });

  test("a stored warn status is a warning toast; a stored error status is an error toast", () => {
    expect(fixToast("m", "S", job({ ...base, status: "warn" }), null).variant).toBe("warning");
    const e = fixToast("m", "S", job({ ...base, status: "error" }), null);
    expect(e.variant).toBe("danger");
    expect(e.title).toBe("Fix incomplete: S");
  });
});
