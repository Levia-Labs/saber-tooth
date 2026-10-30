import fc from "fast-check";
import { describe, expect, test } from "vitest";
import { jobChip, jobStatusLabel, roundsText } from "../src/lib/jobview";

describe("roundsText", () => {
  test("reads n/m from a round progress text, around any other words", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 9999 }),
        fc.integer({ min: 1, max: 9999 }),
        fc.constantFrom("", "Round ", "round "),
        (n, m, lead) => {
          expect(roundsText(`${lead}round ${n} of ${m}`)).toBe(`${n}/${m}`);
          expect(roundsText(`working, round ${n} of ${m}, nearly`)).toBe(`${n}/${m}`);
        },
      ),
    );
  });

  test("is null for any text without a round, and for no text", () => {
    fc.assert(
      fc.property(
        fc.string().filter((s) => !/round/i.test(s)),
        (s) => {
          expect(roundsText(s)).toBeNull();
        },
      ),
    );
    expect(roundsText(null)).toBeNull();
    expect(roundsText("reading map 3 of 9")).toBeNull();
    expect(roundsText("round x of y")).toBeNull();
  });
});

describe("job status mapping", () => {
  test("each job state maps to a library chip and a word", () => {
    const states = ["running", "queued", "done", "failed", "cancelled"] as const;
    expect(states.map((status) => jobChip({ status }))).toEqual([
      "fixing",
      "queued",
      "ok",
      "error",
      "unscanned",
    ]);
    expect(jobStatusLabel({ status: "running", cancel_requested: true })).toBe("Cancelling");
    expect(jobStatusLabel({ status: "done", cancel_requested: true })).toBe("Done");
  });
});

describe("job status icons", () => {
  test("every state has its own icon and the running one is the spinner", async () => {
    const { jobIcon } = await import("../src/lib/jobview");
    const states = ["running", "queued", "done", "failed", "cancelled"] as const;
    const icons = states.map((status) => jobIcon({ status }));
    expect(icons).toEqual(["spinner", "clock", "ok", "reject", "trash"]);
    expect(new Set(icons).size).toBe(5);
  });
});

describe("jobRounds", () => {
  test("a done job shows no rounds; running, failed and cancelled show how far they got", async () => {
    const { jobRounds } = await import("../src/lib/jobview");
    const progress = "round 3 of 6";
    expect(jobRounds({ status: "done", progress })).toBeNull();
    for (const status of ["running", "failed", "cancelled"] as const) {
      expect(jobRounds({ status, progress })).toBe("3/6");
    }
    expect(jobRounds({ status: "running", progress: null })).toBeNull();
  });
});

describe("jobTag", () => {
  test("queued gets #n in info; running, failed and cancelled get x/y in warning; done none", async () => {
    const { jobTag } = await import("../src/lib/jobview");
    const base = { cancel_requested: false, position: null, progress: null };
    expect(jobTag({ ...base, status: "queued", position: 3 })).toEqual({
      text: "#3",
      tone: "info",
      label: "position 3",
    });
    for (const status of ["running", "failed", "cancelled"] as const) {
      expect(jobTag({ ...base, status, progress: "round 2 of 6" })).toEqual({
        text: "2/6",
        tone: "warning",
        label: "round 2 of 6",
      });
    }
    expect(jobTag({ ...base, status: "done", progress: "round 6 of 6" })).toBeNull();
    expect(jobTag({ ...base, status: "running" })).toBeNull();
    expect(jobTag({ ...base, status: "queued" })).toBeNull();
  });
});
