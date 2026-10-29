import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { screen, waitFor } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { TIMELINE } from "./crophelpers";
import { item, mockFetch, renderApp } from "./helpers";

const css = (name: string) => readFileSync(resolve(__dirname, "../src/styles", name), "utf8");
const rule = (sheet: string, selector: string) => {
  const start = `\n${sheet}`.indexOf(`\n${selector} {`);
  if (start < 0) return "";
  const open = sheet.indexOf("{", start);
  return sheet.slice(open + 1, sheet.indexOf("}", open));
};

const ref = (n: number) => ({
  id: `id${String(n).padStart(10, "0")}`,
  title: `Song ${n}`,
  folder: "f",
});

function api(neighbors: () => unknown) {
  mockFetch((url) => {
    if (url.pathname.endsWith("/neighbors")) return neighbors();
    if (url.pathname === "/api/maps/id0000000002") return item(2);
    if (url.pathname.endsWith("/timeline")) return TIMELINE;
    if (url.pathname.endsWith("/proposals")) return [];
    return { items: [], total: 0, offset: 0, limit: 40 };
  });
}
const ok = () => ({ index: 2, total: 5, prev: ref(1), next: ref(3) });

describe("pinned map footer: CSS", () => {
  const sheet = css("mapfooter.css");
  test("the footer does not flex and has a fixed height", () => {
    const r = rule(sheet, ".map-page > .map-footer");
    expect(r).toMatch(/flex:\s*none/);
    expect(r).toMatch(/height:\s*var\(--map-footer-h\)/);
    expect(r).toMatch(/margin:\s*0/);
    expect(sheet).toMatch(/--map-footer-h:\s*3\.25rem/);
  });
  test("the scrolling region shrinks and scrolls, the page does not", () => {
    const r = rule(css("page.css"), ".map-page > .map-scroll");
    expect(r).toMatch(/flex:\s*1 1 auto/);
    expect(r).toMatch(/min-height:\s*0/);
    expect(r).toMatch(/overflow:\s*auto/);
    expect(rule(css("page.css"), ".map-page")).toMatch(/padding-bottom:\s*0/);
  });
  test("columns are 1fr auto 1fr with a fixed centre and ellipsised titles, also on phones", () => {
    expect(rule(sheet, ".map-footer")).toMatch(
      /grid-template-columns:\s*minmax\(0,\s*1fr\)\s+auto\s+minmax\(0,\s*1fr\)/,
    );
    expect(rule(sheet, ".map-footer")).toMatch(/overflow:\s*hidden/);
    expect(rule(sheet, ".map-footer-count")).toMatch(/min-width:\s*5rem/);
    const t = rule(sheet, ".map-footer-title");
    expect(t).toMatch(/text-overflow:\s*ellipsis/);
    expect(t).toMatch(/white-space:\s*nowrap/);
    expect(sheet).not.toMatch(/@media/);
  });
  test("VR keeps 64 px targets and a taller fixed footer", () => {
    expect(sheet).toMatch(/\[data-ui="vr"\] \{[^}]*--map-footer-h:\s*calc\(var\(--vr-target\)/);
  });
  test("toasts sit above the footer on the map page, VR included", () => {
    expect(sheet).toMatch(/:root:has\(\.map-page\) \.toast-stack \{[^}]*var\(--map-footer-h\)/);
    expect(sheet).toMatch(
      /\[data-ui="vr"\]:has\(\.map-page\) \.toast-stack \{[^}]*var\(--map-footer-h\)/,
    );
    expect(css("page.css")).toMatch(/@import "\.\/mapfooter\.css"/);
  });
});

describe("pinned map footer: DOM", () => {
  for (const [tab, query] of [
    ["status", ""],
    ["crop", "?tab=crop"],
    ["delete", "?tab=delete"],
  ] as const) {
    test(`the footer is the last child of .map-page on the ${tab} tab`, async () => {
      api(ok);
      renderApp(`/maps/id0000000002${query}`);
      await screen.findByText("2 / 5");
      const page = document.querySelector(".map-page") as HTMLElement;
      expect(page.lastElementChild).toHaveClass("map-footer");
      expect(page.querySelector(":scope > .map-scroll")).not.toBeNull();
      expect(page.querySelector(".map-scroll .map-footer")).toBeNull();
    });
  }

  test("while loading the same footer class renders as an empty placeholder", async () => {
    api(() => new Promise(() => {}));
    renderApp("/maps/id0000000002");
    await screen.findByRole("heading", { level: 1 });
    const page = document.querySelector(".map-page") as HTMLElement;
    expect(page.lastElementChild).toHaveClass("map-footer", "map-footer-empty");
    expect(page.lastElementChild?.textContent).toBe("");
  });

  test("the loaded footer is not marked empty", async () => {
    api(ok);
    renderApp("/maps/id0000000002");
    await screen.findByText("2 / 5");
    await waitFor(() => expect(document.querySelector(".map-footer-empty")).toBeNull());
  });
});
