import fc from "fast-check";
import { describe, expect, test } from "vitest";
import { STATUS_KEYS } from "../src/api/types";
import {
  apiParams,
  DEFAULT_STATE,
  encodeState,
  filterCounts,
  nextSort,
  parseState,
  SORT_KEYS,
  type LibraryState,
} from "../src/lib/urlstate";

const state = (patch: Partial<LibraryState>): LibraryState => ({ ...DEFAULT_STATE, ...patch });

describe("urlstate", () => {
  test("defaults encode to an empty query", () => {
    expect(encodeState(DEFAULT_STATE).toString()).toBe("");
  });

  test("filters and sort round trip through the URL", () => {
    const s = state({
      q: "aurora",
      status: ["error", "scanning"],
      env: ["Origins", "BigMirrorEnvironment"],
      sort: "bpm",
      order: "desc",
    });
    expect(parseState(encodeState(s).toString())).toEqual(s);
  });

  test("unknown values fall back to defaults", () => {
    const parsed = parseState("?status=bad,ok&sort=nope&order=sideways&env=");
    expect(parsed).toEqual(state({ status: ["ok"] }));
  });

  test("status accepts repeated and comma separated values", () => {
    expect(parseState("status=error,warn&status=ok").status).toEqual(["error", "warn", "ok"]);
  });

  test("api params use q_fields only with a text search and repeat env", () => {
    const plain = apiParams(DEFAULT_STATE, 0, 40);
    expect(plain.get("q_fields")).toBeNull();
    expect(plain.get("limit")).toBe("40");
    const s = state({ q: " moon ", status: ["error", "warn"], env: ["A", "B"] });
    const p = apiParams(s, 80, 40);
    expect(p.get("q")).toBe("moon");
    expect(p.get("q_fields")).toBe("title,mapper");
    expect(p.get("status")).toBe("error,warn");
    expect(p.getAll("env")).toEqual(["A", "B"]);
    expect(p.get("offset")).toBe("80");
  });

  test("sort header clicks flip the order or start at the natural order", () => {
    expect(nextSort(DEFAULT_STATE, "title")).toEqual({ sort: "title", order: "desc" });
    expect(nextSort(DEFAULT_STATE, "bpm")).toEqual({ sort: "bpm", order: "desc" });
    expect(nextSort(DEFAULT_STATE, "environment")).toEqual({ sort: "environment", order: "asc" });
  });

  test("filter counts drive the header badges", () => {
    const s = state({ q: "x", status: ["ok", "warn"], env: [] });
    expect(filterCounts(s)).toEqual({ title: 1, status: 2, env: 0 });
  });

  test("property: parse(encode(state)) is the identity for valid states", () => {
    const arb = fc.record({
      q: fc.string({ maxLength: 60 }).map((t) => t.trim()),
      status: fc.uniqueArray(fc.constantFrom(...STATUS_KEYS)),
      env: fc.uniqueArray(
        fc.string({ minLength: 1, maxLength: 20 }).filter((t) => t.trim() !== ""),
      ),
      sort: fc.constantFrom(...SORT_KEYS),
      order: fc.constantFrom("asc" as const, "desc" as const),
    });
    fc.assert(
      fc.property(arb, (s) => {
        expect(parseState(encodeState(s).toString())).toEqual(s);
      }),
    );
  });

  test("property: parseState never throws and always yields valid keys", () => {
    fc.assert(
      fc.property(fc.string({ maxLength: 200 }), (search) => {
        const s = parseState(search);
        expect(SORT_KEYS).toContain(s.sort);
        expect(s.q.length).toBeLessThanOrEqual(200);
        for (const k of s.status) expect(STATUS_KEYS).toContain(k);
      }),
    );
  });
});
