import { screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { bsMap } from "./bshelpers";
import { mockFetch, renderApp } from "./helpers";

function api() {
  mockFetch((url) => {
    const p = url.pathname;
    if (p === "/api/beatsaver/search") return { items: [bsMap(1)], cursor: null };
    if (p === "/api/beatsaver/config") return { playlists_enabled: false };
    if (p === "/api/beatsaver/presets") return [];
    return { items: [], cursor: null };
  });
}

function follows(a: Element, b: Element) {
  return Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
}

describe("BeatSaver title row", () => {
  test("maps: section tabs, saved searches, More filters and Maps/Playlists tabs share one row", async () => {
    api();
    renderApp("/beatsaver");
    const section = await screen.findByRole("navigation", { name: "Section" });
    const row = section.closest(".lib-bar") as HTMLElement;
    const saved = await within(row).findByRole("group", { name: "Saved filters" });
    const more = within(row).getByRole("button", { name: /More filters/ });
    const tabs = within(row).getByRole("navigation", { name: "BeatSaver sections" });
    expect(follows(section, saved)).toBe(true);
    expect(follows(saved, more)).toBe(true);
    expect(follows(more, tabs)).toBe(true);
    expect(document.querySelectorAll(".bs-toolbar")).toHaveLength(1);
    expect(row.contains(document.querySelector(".bs-toolbar"))).toBe(true);
  });

  test("playlists: section tabs, More filters and Maps/Playlists tabs share one row", async () => {
    api();
    renderApp("/beatsaver/playlists");
    const section = await screen.findByRole("navigation", { name: "Section" });
    const row = section.closest(".lib-bar") as HTMLElement;
    const more = await within(row).findByRole("button", { name: /More filters/ });
    const tabs = within(row).getByRole("navigation", { name: "BeatSaver sections" });
    expect(follows(section, more)).toBe(true);
    expect(follows(more, tabs)).toBe(true);
    expect(row.contains(document.querySelector(".bs-toolbar"))).toBe(true);
  });

  test("keeps the hidden h1 as the focus target", async () => {
    api();
    renderApp("/beatsaver");
    await screen.findByRole("navigation", { name: "Section" });
    const h1 = screen.getAllByRole("heading", { level: 1 });
    expect(h1).toHaveLength(1);
    expect(h1[0]).toHaveAttribute("data-page-heading");
  });
});
