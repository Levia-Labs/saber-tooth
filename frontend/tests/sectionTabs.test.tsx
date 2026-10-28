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
    if (p === "/api/library") return { items: [], total: 0 };
    return {};
  });
}

describe("section tabs and masthead", () => {
  test("library page: tabs in the page bar, Library current, one h1", async () => {
    api();
    renderApp("/");
    const nav = await screen.findByRole("navigation", { name: "Section" });
    expect(nav.closest("header")).toBeNull();
    expect(within(nav).getByRole("link", { name: "Library" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(nav).getByRole("link", { name: "BeatSaver" })).not.toHaveAttribute(
      "aria-current",
    );
    const h1 = screen.getAllByRole("heading", { level: 1 });
    expect(h1).toHaveLength(1);
    expect(h1[0]).toHaveTextContent("Library");
    expect(h1[0]).toHaveAttribute("data-page-heading");
    expect(h1[0]).toHaveAttribute("tabindex", "-1");
  });

  test("beatsaver page: BeatSaver current, one h1", async () => {
    api();
    renderApp("/beatsaver");
    const nav = await screen.findByRole("navigation", { name: "Section" });
    expect(within(nav).getByRole("link", { name: "BeatSaver" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(nav).getByRole("link", { name: "Library" })).not.toHaveAttribute("aria-current");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  test("playlists page keeps the tabs", async () => {
    api();
    renderApp("/beatsaver/playlists");
    const nav = await screen.findByRole("navigation", { name: "Section" });
    expect(within(nav).getByRole("link", { name: "BeatSaver" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  test("masthead has no section nav and holds the About link", async () => {
    api();
    renderApp("/");
    await screen.findByRole("navigation", { name: "Section" });
    const header = screen.getByRole("banner");
    expect(within(header).queryByRole("navigation")).toBeNull();
    expect(within(header).getByRole("link", { name: "About" })).toHaveAttribute("href", "/about");
    expect(within(header).getAllByRole("link")).toHaveLength(2);
  });
});
