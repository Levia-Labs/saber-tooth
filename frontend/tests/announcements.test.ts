import { describe, expect, test } from "vitest";
import {
  AUTO_DISMISS_MS,
  MAX_BANNERS,
  addBanner,
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
