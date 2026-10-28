import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { bsMap } from "./bshelpers";
import { mockFetch, renderApp } from "./helpers";

const css = (name: string) => readFileSync(resolve(__dirname, "../src/styles", name), "utf8");
const rule = (sheet: string, selector: string) => {
  const start = `\n${sheet}`.indexOf(`\n${selector} {`);
  if (start < 0) return "";
  const open = sheet.indexOf("{", start);
  return sheet.slice(open + 1, sheet.indexOf("}", open));
};

function api() {
  mockFetch((url) => {
    const p = url.pathname;
    if (p === "/api/beatsaver/search") return { items: [bsMap(1)], cursor: null };
    if (p === "/api/beatsaver/config") return { playlists_enabled: false };
    if (p === "/api/beatsaver/presets") return [];
    if (p === "/api/maps/facets") return { mappers: [], tags: [], environments: [] };
    return { items: [], total: 0, offset: 0, limit: 40, cursor: null };
  });
}

const follows = (a: Element, b: Element) =>
  Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);

describe("section tabs row alignment", () => {
  test("the row, its title group and the right slot centre their items", () => {
    expect(rule(css("library.css"), ".lib-bar")).toMatch(/align-items:\s*center/);
    expect(rule(css("library.css"), ".lib-title")).toMatch(/align-items:\s*center/);
    const slot = css("barslot.css");
    expect(rule(slot, ".bar-slot")).toMatch(/align-items:\s*center/);
    expect(rule(slot, ".bar-slot .bs-toolbar")).toMatch(/margin-bottom:\s*0/);
    expect(rule(slot, ".lib-bar .btn,\n.lib-bar .btn.icon")).toMatch(/min-height:\s*42px/);
  });

  test("BeatSaver: tabs, website button and right group share the row", async () => {
    api();
    renderApp("/beatsaver");
    const section = await screen.findByRole("navigation", { name: "Section" });
    const row = section.closest(".lib-bar") as HTMLElement;
    const site = within(row).getByRole("link", { name: "Open BeatSaver website" });
    const more = await within(row).findByRole("button", { name: /More filters/ });
    expect(follows(section, site)).toBe(true);
    expect(follows(site, more)).toBe(true);
    expect(row.querySelector(".bar-slot")?.contains(more)).toBe(true);
  });

  test("Library: Generate map and Learn lightshows sit in the row after the count", async () => {
    api();
    renderApp("/");
    const section = await screen.findByRole("navigation", { name: "Section" });
    const row = section.closest(".lib-bar") as HTMLElement;
    const count = row.querySelector(".count") as HTMLElement;
    const generate = await within(row).findByRole("link", { name: "Generate map" });
    const learn = within(row).getByRole("button", { name: "Learn lightshows" });
    expect(follows(section, count)).toBe(true);
    expect(follows(count, generate)).toBe(true);
    expect(follows(generate, learn)).toBe(true);
    expect(document.querySelectorAll(".lib-tools")).toHaveLength(1);
    expect(row.querySelector(".bar-slot")?.contains(generate)).toBe(true);
  });
});
