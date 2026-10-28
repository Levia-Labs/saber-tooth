import fc from "fast-check";
import { describe, expect, test } from "vitest";
import {
  AUTO_DISMISS_MS,
  MAX_BANNERS,
  addBanner,
  batchSummary,
  capitalize,
  dismissBanner,
  expireBanners,
  nextExpiry,
  ttl,
  type Banner,
} from "../src/lib/announcements";

const add = (
  list: Banner[],
  title: string,
  variant: "progress" | "success" = "progress",
  now = 0,
) => addBanner(list, { variant, title }, now);

describe("announcements", () => {
  test("same key replaces in place", () => {
    let list = add([], "Fix A");
    list = add(list, "Fix B");
    list = addBanner(list, { key: "Fix A", variant: "danger", title: "Fix A", message: "boom" }, 0);
    expect(list.map((b) => b.key)).toEqual(["Fix A", "Fix B"]);
    expect(list[0]).toMatchObject({ variant: "danger", message: "boom" });
  });

  test("key defaults to the title", () => {
    expect(add([], "Fix A")[0]?.key).toBe("Fix A");
  });

  test("cap drops the oldest", () => {
    let list: Banner[] = [];
    for (let i = 0; i < MAX_BANNERS + 2; i++) list = add(list, `job ${i}`);
    expect(list.map((b) => b.key)).toEqual(["job 2", "job 3", "job 4", "job 5"]);
  });

  test("cap drops the oldest non-danger toast before an older sticky danger one", () => {
    let list = addBanner([], { variant: "danger", title: "bad" }, 0);
    for (let i = 0; i < MAX_BANNERS + 1; i++) list = add(list, `job ${i}`);
    expect(list.map((b) => b.key)).toEqual(["bad", "job 2", "job 3", "job 4"]);
  });

  test("cap drops sticky success before danger, and danger only when all are danger", () => {
    let list = addBanner([], { variant: "danger", title: "d0" }, 0);
    list = addBanner(list, { variant: "success", title: "s", sticky: true }, 0);
    list = addBanner(list, { variant: "warning", title: "w" }, 0);
    list = addBanner(list, { variant: "danger", title: "d1" }, 0);
    list = addBanner(list, { variant: "danger", title: "d2" }, 0);
    expect(list.map((b) => b.key)).toEqual(["d0", "w", "d1", "d2"]);
    list = addBanner(list, { variant: "danger", title: "d3" }, 0);
    list = addBanner(list, { variant: "danger", title: "d4" }, 0);
    expect(list.map((b) => b.key)).toEqual(["d1", "d2", "d3", "d4"]);
  });

  test("property: the cap holds and fewer dangers than the cap are never dropped", () => {
    const variant = fc.constantFrom("progress", "success", "info", "warning", "danger" as const);
    fc.assert(
      fc.property(fc.array(fc.tuple(fc.nat(30), variant), { maxLength: 40 }), (steps) => {
        let list: Banner[] = [];
        for (const [n, v] of steps) {
          const key = `k${n}`;
          const kept = list.filter((b) => b.variant === "danger" && b.key !== key);
          list = addBanner(list, { key, variant: v, title: key }, 0);
          expect(list.length).toBeLessThanOrEqual(MAX_BANNERS);
          if (kept.length < MAX_BANNERS) {
            for (const d of kept) expect(list.some((b) => b.key === d.key)).toBe(true);
          }
        }
      }),
    );
  });

  test("ttl is 5 s for success and info only", () => {
    expect(ttl("success")).toBe(AUTO_DISMISS_MS);
    expect(ttl("info")).toBe(AUTO_DISMISS_MS);
    for (const v of ["progress", "warning", "danger"] as const) expect(ttl(v)).toBeNull();
  });

  test("expiry removes only due banners", () => {
    let list = add([], "a", "success", 0);
    list = add(list, "b", "progress", 0);
    expect(expireBanners(list, AUTO_DISMISS_MS - 1)).toBe(list);
    expect(expireBanners(list, AUTO_DISMISS_MS).map((b) => b.key)).toEqual(["b"]);
    expect(nextExpiry(list)).toBe(AUTO_DISMISS_MS);
    expect(nextExpiry(dismissBanner(list, "a"))).toBeNull();
  });

  test("capitalize", () => {
    expect(capitalize("retrying (1/3)")).toBe("Retrying (1/3)");
    expect(capitalize("")).toBe("");
  });
});

describe("batchSummary", () => {
  const sum = (installed: number, skipped: number, failed: number, reasons: string[] = []) =>
    batchSummary("Download maps", { installed, skipped, failed }, reasons);

  test("success when nothing failed, warning when some failed, danger when all failed", () => {
    expect(sum(1, 0, 0)).toMatchObject({
      key: "Download maps",
      variant: "success",
      message: "Installed 1, skipped 0, failed 0.",
    });
    expect(sum(1, 0, 1, ["k3: Needs Noodle"]).variant).toBe("warning");
    expect(sum(1, 0, 1, ["k3: Needs Noodle"]).message).toBe(
      "Installed 1, skipped 0, failed 1. k3: Needs Noodle",
    );
    expect(sum(0, 0, 2).variant).toBe("danger");
  });

  test("variant follows the counts for any tally", () => {
    fc.assert(
      fc.property(fc.nat(50), fc.nat(50), fc.nat(50), (i, s, f) => {
        const v = sum(i, s, f).variant;
        expect(v).toBe(f === 0 ? "success" : i + s === 0 ? "danger" : "warning");
      }),
    );
  });
});

describe("banner links", () => {
  test("a link on the input is kept on the banner and replaced with its key", () => {
    const link = { to: "/maps/abc", label: "Open map" };
    const first = addBanner([], { key: "g1", variant: "success", title: "Map ready", link }, 0);
    expect(first[0]?.link).toEqual(link);
    const next = addBanner(first, { key: "g1", variant: "danger", title: "Failed" }, 1);
    expect(next).toHaveLength(1);
    expect(next[0]?.link).toBeUndefined();
  });
});
