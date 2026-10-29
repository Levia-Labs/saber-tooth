import fc from "fast-check";
import { describe, expect, test } from "vitest";
import { roundsText } from "../src/lib/jobrounds";
import { jobChip, jobStatusLabel } from "../src/lib/jobstatus";

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
