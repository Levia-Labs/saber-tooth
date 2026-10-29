import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { MapPage } from "../src/api/types";
import { FACETS, mockFetch, renderApp } from "./helpers";

const css = (name: string) => readFileSync(resolve(__dirname, "../src/styles", name), "utf8");
const rule = (sheet: string, selector: string) => {
  const start = `\n${sheet}`.indexOf(`\n${selector} {`);
  if (start < 0) return "";
  const open = sheet.indexOf("{", start);
  return sheet.slice(open + 1, sheet.indexOf("}", open));
};

const page = JSON.parse(
  readFileSync(resolve(__dirname, "fixtures/maps-page.json"), "utf8"),
) as MapPage;

describe("library list with the real API payload", () => {
  test("renders rows from a recorded /api/maps page", async () => {
    mockFetch((url) => (url.pathname === "/api/maps/facets" ? FACETS : page));
    renderApp("/?sort=title&order=asc");
    expect(
      await screen.findByRole("link", { name: "347 Midnight Demons [saber-tooth]" }),
    ).toBeTruthy();
    expect(page.total).toBeGreaterThan(40);
  }, 20_000);

  test("outcomes are toasts, so nothing inline can squeeze the list to nothing", () => {
    const lib = css("library.css");
    expect(lib).not.toContain(".lib-alerts");
    expect(rule(lib, ".lib-scroll")).toMatch(/min-height:\s*12rem/);
  });
});

describe("wordmark", () => {
  test("is one baseline-aligned flex unit centred with the logo", async () => {
    mockFetch((url) => (url.pathname === "/api/maps/facets" ? FACETS : page));
    renderApp("/");
    const base = css("base.css");
    expect(rule(base, ".wordmark")).toMatch(/display:\s*inline-flex/);
    expect(rule(base, ".wordmark")).toMatch(/align-items:\s*baseline/);
    expect(rule(base, ".wordmark")).toMatch(/line-height:\s*1/);
    expect(rule(base, ".brand")).toMatch(/align-items:\s*center/);
    const mark = (await screen.findByLabelText("Saber Tooth, library")).querySelector(".wordmark");
    expect([...(mark?.children ?? [])].map((c) => c.textContent)).toEqual(["Saber", " ", "Tooth"]);
  });
});
