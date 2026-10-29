import userEvent from "@testing-library/user-event";
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

  test("the masthead has no section nav and no About link; About is the last tab", async () => {
    api();
    renderApp("/");
    const nav = await screen.findByRole("navigation", { name: "Section" });
    const header = screen.getByRole("banner");
    expect(within(header).queryByRole("navigation")).toBeNull();
    expect(within(header).queryByRole("link", { name: "About" })).toBeNull();
    expect(within(header).getAllByRole("link")).toHaveLength(1);
    const brand = within(header).getByRole("link", { name: /Saber Tooth/ });
    expect(brand).toHaveAttribute("href", "/");
    expect(brand.querySelector("svg, img")).not.toBeNull();
    expect(brand).toHaveTextContent("Saber Tooth");
    const links = within(nav).getAllByRole("link");
    expect(links.at(-1)).toHaveAccessibleName("About");
    expect(links.at(-1)).toHaveAttribute("href", "/about");
    expect(links.slice(0, 3).map((l) => l.textContent?.replace(/d+$/, ""))).toEqual([
      "Library",
      "BeatSaver",
      "Jobs",
    ]);
  });

  test("every tab shows its icon before the label, from the in-house set", async () => {
    api();
    renderApp("/");
    const nav = await screen.findByRole("navigation", { name: "Section" });
    for (const link of within(nav).getAllByRole("link")) {
      const icon = link.querySelector("svg.ic");
      expect(icon, link.textContent ?? "").not.toBeNull();
      expect(link.firstElementChild).toBe(icon);
    }
  });

  test("the About page keeps the tab bar with About current and one h1", async () => {
    api();
    renderApp("/about");
    const nav = await screen.findByRole("navigation", { name: "Section" });
    expect(within(nav).getByRole("link", { name: "About" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(nav).getByRole("link", { name: "Library" })).not.toHaveAttribute("aria-current");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});

describe("BeatSaver Maps | Playlists tabs", () => {
  test("reuse the section tab style, show icons, follow the route and move focus with arrows", async () => {
    api();
    renderApp("/beatsaver");
    const nav = await screen.findByRole("navigation", { name: "BeatSaver sections" });
    expect(nav).toHaveClass("mode-switch");
    const maps = within(nav).getByRole("link", { name: "Maps" });
    const lists = within(nav).getByRole("link", { name: "Playlists" });
    expect(maps).toHaveClass("pill");
    expect(maps).toHaveAttribute("aria-current", "page");
    expect(lists).not.toHaveAttribute("aria-current");
    for (const link of [maps, lists]) expect(link.firstElementChild).toHaveClass("ic");
    maps.focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(lists).toHaveFocus();
    await userEvent.keyboard("{ArrowLeft}");
    expect(maps).toHaveFocus();
  });
});
