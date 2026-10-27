import fc from "fast-check";
import { describe, expect, test } from "vitest";
import { formatEnvironment } from "../src/lib/environment";

describe("formatEnvironment", () => {
  test.each([
    ["BigMirrorEnvironment", "Big Mirror"],
    ["KDAEnvironment", "KDA"],
    ["DefaultEnvironment", "Default"],
    ["TimbalandEnvironment", "Timbaland"],
    ["GagaEnvironment", "Gaga"],
    ["Origins", "Origins"],
    ["GlassDesertEnvironment", "Glass Desert"],
    ["Environment", "Environment"],
    ["", ""],
  ])("%s -> %s", (raw, label) => {
    expect(formatEnvironment(raw)).toBe(label);
  });

  test("property: never throws, never has stray spaces", () => {
    fc.assert(
      fc.property(fc.string({ maxLength: 40 }), (raw) => {
        const out = formatEnvironment(raw);
        expect(out).toBe(out.trim());
        expect(out).not.toMatch(/\s{2}/);
      }),
    );
  });
});
