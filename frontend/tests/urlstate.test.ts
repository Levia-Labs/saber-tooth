import fc from "fast-check";
import { describe, expect, test } from "vitest";
import { LEVEL_KEYS, STATUS_KEYS } from "../src/api/types";
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
    expect(p.get("q_fields")).toBe("title");
    expect(p.get("status")).toBe("error,warn");
    expect(p.getAll("env")).toEqual(["A", "B"]);
    expect(p.get("offset")).toBe("80");
  });

  test("mapper and level filters go to the API with their own parameters", () => {
    const s = state({
      q: "ann",
      qField: "mapper",
      mapper: ["A, B", "C"],
      level: ["Easy", "ExpertPlus"],
      levelMode: "all",
    });
    const p = apiParams(s, 0, 40);
    expect(p.get("q_fields")).toBe("mapper");
    expect(p.getAll("mapper")).toEqual(["A, B", "C"]);
    expect(p.getAll("level")).toEqual(["Easy", "ExpertPlus"]);
    expect(p.get("level_mode")).toBe("all");
    expect(apiParams(state({ levelMode: "all" }), 0, 40).get("level_mode")).toBeNull();
    expect(parseState(encodeState(s).toString())).toEqual(s);
  });

  test("levels sorts highest first", () => {
    expect(nextSort(DEFAULT_STATE, "levels")).toEqual({ sort: "levels", order: "desc" });
    expect(nextSort(DEFAULT_STATE, "mapper")).toEqual({ sort: "mapper", order: "asc" });
  });

  test("sort header clicks flip the order or start at the natural order", () => {
    expect(nextSort(DEFAULT_STATE, "title")).toEqual({ sort: "title", order: "desc" });
    expect(nextSort(DEFAULT_STATE, "bpm")).toEqual({ sort: "bpm", order: "desc" });
    expect(nextSort(DEFAULT_STATE, "environment")).toEqual({ sort: "environment", order: "asc" });
  });

  test("filter counts drive the header badges", () => {
    const s = state({ q: "x", status: ["ok", "warn"], env: [] });
    expect(filterCounts(s)).toEqual({ title: 1, author: 0, levels: 0, status: 2, env: 0 });
    const a = state({ q: "x", qField: "mapper", mapper: ["A"], level: ["Easy"] });
    expect(filterCounts(a)).toEqual({ title: 0, author: 2, levels: 1, status: 0, env: 0 });
  });

  test("property: parse(encode(state)) is the identity for valid states", () => {
    const arb = fc.record({
      q: fc.string({ maxLength: 60 }).map((t) => t.trim()),
      qField: fc.constantFrom("title" as const, "mapper" as const),
      mapper: fc.uniqueArray(fc.string({ minLength: 1, maxLength: 20 })),
      level: fc.uniqueArray(fc.constantFrom(...LEVEL_KEYS)),
      levelMode: fc.constantFrom("any" as const, "all" as const),
      status: fc.uniqueArray(fc.constantFrom(...STATUS_KEYS)),
      env: fc.uniqueArray(
        fc.string({ minLength: 1, maxLength: 20 }).filter((t) => t.trim() !== ""),
      ),
      sort: fc.constantFrom(...SORT_KEYS),
      order: fc.constantFrom("asc" as const, "desc" as const),
    });
    fc.assert(
      fc.property(arb, (s) => {
        // The URL keeps no field for an empty search, and no mode without levels.
        const want = {
          ...s,
          qField: s.q ? s.qField : ("title" as const),
          levelMode: s.level.length ? s.levelMode : ("any" as const),
        };
        expect(parseState(encodeState(s).toString())).toEqual(want);
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
