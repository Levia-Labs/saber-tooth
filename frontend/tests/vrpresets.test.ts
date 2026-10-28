import fc from "fast-check";
import { describe, expect, test } from "vitest";
import { apiParams, DEFAULT_STATE } from "../src/lib/urlstate";
import {
  VR_PRESETS,
  VR_SORTS,
  encodeVrView,
  isFixedCopy,
  parseVrView,
  togglePreset,
  vrState,
  type VrView,
} from "../src/vr/presets";

const view = (presets: VrView["presets"], sort: VrView["sort"] = "title"): VrView => ({
  presets,
  sort,
});

describe("vrState", () => {
  test("no preset is the plain library query", () => {
    expect(vrState(view([]))).toEqual({ ...DEFAULT_STATE, sort: "title", order: "asc" });
  });

  test.each([
    [["needs-fix"], ["error", "warn"], []],
    [["missing-levels"], ["incomplete"], []],
    [["unscanned"], ["unscanned"], []],
    [["expert-plus"], [], ["ExpertPlus"]],
    [["unscanned", "needs-fix"], ["error", "warn", "unscanned"], []],
    [["needs-fix", "expert-plus"], ["error", "warn"], ["ExpertPlus"]],
    [["fixed"], [], []],
  ] as const)("%j builds status %j and level %j", (presets, status, level) => {
    const state = vrState(view([...presets]));
    expect(state.status).toEqual(status);
    expect(state.level).toEqual(level);
  });

  test.each([
    ["title", "title", "asc"],
    ["errors", "errors", "desc"],
    ["recent", "scanned_at", "desc"],
    ["length", "duration", "desc"],
  ] as const)("sort %s asks the API for %s %s", (key, sort, order) => {
    const params = apiParams(vrState(view([], key)), 0, 40);
    expect(params.get("sort")).toBe(sort);
    expect(params.get("order")).toBe(order);
  });

  test("a query never carries a text search", () => {
    for (const p of VR_PRESETS) expect(vrState(view([p.key])).q).toBe("");
  });
});

describe("parseVrView and encodeVrView", () => {
  test("round trip", () => {
    const v = view(["needs-fix", "expert-plus"], "errors");
    expect(encodeVrView(v).toString()).toBe("p=needs-fix%2Cexpert-plus&sort=errors");
    expect(parseVrView(encodeVrView(v).toString())).toEqual(v);
  });

  test("the defaults leave the address clean", () => {
    expect(encodeVrView(view([])).toString()).toBe("");
  });

  test("unknown presets and sorts are ignored, known ones come out in the fixed order", () => {
    expect(parseVrView("p=expert-plus,bogus,needs-fix,needs-fix&sort=nope")).toEqual(
      view(["needs-fix", "expert-plus"], "title"),
    );
    expect(parseVrView("")).toEqual(view([]));
  });

  test("arbitrary addresses parse to a valid view", () => {
    fc.assert(
      fc.property(fc.string(), (search) => {
        const v = parseVrView(search);
        expect(VR_SORTS.map((s) => s.key)).toContain(v.sort);
        expect(new Set(v.presets).size).toBe(v.presets.length);
        expect(v.presets.every((k) => VR_PRESETS.some((p) => p.key === k))).toBe(true);
        expect(parseVrView(encodeVrView(v).toString())).toEqual(v);
      }),
    );
  });
});

describe("togglePreset and isFixedCopy", () => {
  test("toggles one preset on and off and keeps the sort", () => {
    const on = togglePreset(view([], "length"), "fixed");
    expect(on).toEqual(view(["fixed"], "length"));
    expect(togglePreset(on, "fixed")).toEqual(view([], "length"));
  });

  test("a fixed copy is a map with an original", () => {
    expect(isFixedCopy({ original_id: "abc" })).toBe(true);
    expect(isFixedCopy({ original_id: null })).toBe(false);
    expect(isFixedCopy({})).toBe(false);
  });
});
