import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { ICON_NAMES } from "../src/components/icons";
import { LEVELS } from "../src/lib/levels";
import { FACETS, item, mockFetch, renderApp } from "./helpers";

const css = (name: string) => readFileSync(resolve(__dirname, "../src/styles", name), "utf8");
const rule = (sheet: string, selector: string) => {
  const needle = `\n${selector} {`;
  const start = `\n${sheet}`.indexOf(needle);
  if (start < 0) return "";
  const open = sheet.indexOf("{", start);
  return sheet.slice(open + 1, sheet.indexOf("}", open));
};

describe("left-aligned columns", () => {
  test("header cells are left-aligned rows and the row-only title column stack is scoped", () => {
    const lib = css("library.css");
    const th = rule(lib, ".th");
    expect(th).toMatch(/flex-direction:\s*row/);
    expect(th).toMatch(/justify-content:\s*flex-start/);
    expect(th).toMatch(/text-align:\s*left/);
    expect(lib).toMatch(/\.th-row \{[^}]*justify-content:\s*flex-start/);
    expect(rule(lib, ".lib-grid > div")).toMatch(/text-align:\s*left/);
    const rows = css("rows.css");
    expect(rows).not.toMatch(/(^|\n)\.col-title\s*\{/);
    expect(rule(rows, ".lib-row .col-title")).toMatch(/flex-direction:\s*column/);
  });

  test("no header or row rule centres or pushes content", () => {
    const all = css("library.css") + css("rows.css");
    expect(all).not.toMatch(/margin-left:\s*auto/);
    expect(rule(css("library.css"), ".lib-grid")).not.toMatch(/justify-items:\s*center/);
  });
});

describe("map page layout", () => {
  test("the page is a non-scrolling flex column with a scrolling fixes region", () => {
    const page = css("page.css");
    expect(rule(page, ".map-page")).toMatch(/display:\s*flex/);
    expect(rule(page, ".map-page")).toMatch(/overflow:\s*hidden/);
    expect(rule(page, ".map-page > .fixes-scroll")).toMatch(/min-height:\s*0/);
    expect(rule(page, ".map-page > .fixes-scroll")).toMatch(/overflow:\s*auto/);
    expect(rule(page, ".map-toolbar")).toMatch(/flex-wrap:\s*wrap/);
    expect(rule(css("base.css"), "html,\nbody,\n#root")).toMatch(/overflow:\s*hidden/);
  });

  test("one toolbar row holds every action with icons", async () => {
    mockFetch((url) => {
      if (url.pathname === "/api/maps/facets") return FACETS;
      if (url.pathname === "/api/maps/id0000000001") return item(1);
      if (url.pathname.endsWith("/proposals")) return [];
      return { items: [], total: 0, offset: 0, limit: 40 };
    });
    renderApp("/maps/id0000000001");
    const bar = await screen.findByRole("toolbar", { name: "Fix actions" });
    for (const n of ["Scan", "Approve all", "Apply approved", "Expand all", "Collapse all"]) {
      const b = Array.from(bar.querySelectorAll("button")).find((x) => x.textContent === n);
      expect(b, n).toBeTruthy();
      expect(b?.querySelector("svg")).not.toBeNull();
    }
    expect(ICON_NAMES).toEqual(expect.arrayContaining(["approve-all", "expand", "collapse"]));
  });
});

test("level chip abbreviations", () => {
  expect(LEVELS.map((l) => l.abbr)).toEqual(["Ea", "No", "Ha", "Ex", "Ex+"]);
});
