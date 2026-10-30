import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test } from "vitest";
import type { Playlist } from "../src/api/playlists";
import { bsMap } from "./bshelpers";
import { item, mockFetch, renderApp } from "./helpers";
import { bsPlaylist } from "./plhelpers";

const ref = (n: number) => ({ id: item(n).id, title: `Song ${n}`, folder: `F${n}` });

const pl = (id: string, title: string, songs = 1): Playlist =>
  ({
    id,
    title,
    author: "me",
    description: "",
    folder: "",
    sync: false,
    sync_url: "",
    exported: "",
    updated_at: "t",
    songs_count: songs,
    missing_count: 0,
    cover_url: null,
    songs: [],
  }) as unknown as Playlist;

const LISTS = [pl("a", "Alpha"), pl("b", "Bravo"), pl("c", "Charlie")];

function api() {
  return mockFetch((url) => {
    const p = url.pathname;
    if (p.endsWith("/neighbors")) return { index: 2, total: 3, prev: ref(1), next: ref(3) };
    if (p === "/api/maps/id0000000002") return item(2);
    if (p.endsWith("/proposals")) return [];
    if (p === "/api/playlists") return { items: LISTS };
    if (p === "/api/playlists/config") return { export_enabled: true, live: {} };
    if (p.startsWith("/api/playlists/")) {
      const found = LISTS.find((l) => p === `/api/playlists/${l.id}`);
      return found ?? {};
    }
    if (p === "/api/jobs") return { running: [], queued: [], recent: [] };
    if (p === "/api/beatsaver/presets") return [];
    if (p === "/api/beatsaver/config") return { playlists_enabled: false };
    if (p === "/api/beatsaver/playlists/p1") {
      return {
        playlist: bsPlaylist("p1", { name: "Gentle electronic", owner: "Alice" }),
        items: [bsMap(1)],
        scanned: 1,
        matched: 1,
        cursor: null,
      };
    }
    return { items: [], total: 0, offset: 0, limit: 40 };
  });
}

beforeEach(() => sessionStorage.clear());
afterEach(() => sessionStorage.clear());

describe("map page back link and header", () => {
  test.each([
    ["", "/", "Library"],
    ["?from=library", "/", "Library"],
    ["?from=jobs&back=status%3Dfailed", "/jobs?status=failed", "Jobs"],
    ["?from=playlist:p1", "/playlists/p1", "Playlists"],
    ["?from=bs-playlist:p1&back=q%3Dx", "/beatsaver/playlists/p1?q=x", "BeatSaver"],
    ["?from=bogus", "/", "Library"],
  ])("%s returns to %s with the %s tab active", async (query, href, tab) => {
    api();
    renderApp(`/maps/id0000000002${query}`);
    const back = await screen.findByRole("link", { name: "Back to list" });
    expect(back).toHaveAttribute("href", href);
    expect(screen.queryByRole("link", { name: "Library" })?.className ?? "").not.toBe("back");
    const tabs = screen.getByRole("navigation", { name: "Section" });
    expect(within(tabs).getByRole("link", { name: new RegExp(tab) })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("banner")).toBeInTheDocument();
  });

  test("keeps the masthead and the tab row and switching tabs keeps the origin", async () => {
    api();
    const { router } = renderApp("/maps/id0000000002?from=jobs");
    await screen.findByRole("heading", { name: "Song 2" });
    expect(screen.getByRole("link", { name: /Saber Tooth/ })).toBeInTheDocument();
    await userEvent.click(await screen.findByRole("tab", { name: /Crop/ }));
    await waitFor(() => expect(router.state.location.search).toContain("tab=crop"));
    expect(router.state.location.search).toContain("from=jobs");
  });

  test("the footer links keep the origin", async () => {
    api();
    renderApp("/maps/id0000000002?from=playlist:a");
    const prev = await screen.findByRole("link", { name: /Song 1/ });
    expect(prev).toHaveAttribute("href", "/maps/id0000000001?from=playlist%3Aa");
    expect(screen.getByRole("link", { name: /Song 3/ })).toHaveAttribute(
      "href",
      "/maps/id0000000003?from=playlist%3Aa",
    );
  });
});

describe("list links carry the origin", () => {
  test("a Jobs row opens the map with from=jobs and its filters in back", async () => {
    mockFetch((url) =>
      url.pathname === "/api/jobs"
        ? {
            running: [],
            queued: [],
            recent: [
              {
                id: "r1",
                kind: "Scan",
                title: "Acid Rain",
                status: "done",
                map_id: "m1",
                map_exists: true,
                created_at: 1,
                started_at: 1,
                finished_at: 2,
                progress: null,
                error: null,
                position: null,
              },
            ],
          }
        : {},
    );
    renderApp("/jobs?status=done");
    const link = await screen.findByRole("link", { name: "Acid Rain" });
    expect(link).toHaveAttribute("href", "/maps/m1?from=jobs&back=status%3Ddone");
  });
});

describe("playlist page", () => {
  test("Back to list returns to Playlists and the tab row stays", async () => {
    api();
    renderApp("/playlists/b");
    expect(await screen.findByRole("link", { name: "Back to list" })).toHaveAttribute(
      "href",
      "/playlists",
    );
    expect(screen.getByRole("navigation", { name: "Section" })).toBeInTheDocument();
  });

  test("the footer names the neighbours and the position in the list order", async () => {
    api();
    renderApp("/playlists/b");
    const nav = await screen.findByRole("navigation", { name: "Neighbouring playlists" });
    expect(within(nav).getByRole("link", { name: /Alpha/ })).toHaveAttribute(
      "href",
      "/playlists/a",
    );
    expect(within(nav).getByRole("link", { name: /Charlie/ })).toHaveAttribute(
      "href",
      "/playlists/c",
    );
    expect(within(nav).getByText("2 / 3")).toBeInTheDocument();
  });

  test("the footer wraps and follows the saved sort", async () => {
    sessionStorage.setItem(
      "saber-tooth.playlists-state",
      JSON.stringify({ sort: "title", ascending: false }),
    );
    api();
    renderApp("/playlists/c");
    const nav = await screen.findByRole("navigation", { name: "Neighbouring playlists" });
    expect(within(nav).getByText("1 / 3")).toBeInTheDocument();
    expect(within(nav).getByRole("link", { name: /Alpha/ })).toHaveAttribute(
      "href",
      "/playlists/a",
    );
    expect(within(nav).getByRole("link", { name: /Bravo/ })).toHaveAttribute(
      "href",
      "/playlists/b",
    );
  });

  test("a new playlist has no footer", async () => {
    api();
    renderApp("/playlists/new");
    await screen.findByRole("heading", { level: 1 });
    expect(screen.queryByRole("navigation", { name: "Neighbouring playlists" })).toBeNull();
  });
});

describe("BeatSaver playlist header", () => {
  test("shows the tab row without the playlist name; the name stays in the content", async () => {
    api();
    const { container } = renderApp("/beatsaver/playlists/p1");
    const name = await screen.findByRole("heading", { name: "Gentle electronic" });
    expect(container.querySelector(".lib-bar")?.textContent).not.toContain("Gentle electronic");
    expect(container.querySelector(".lib-bar")?.contains(name)).toBe(false);
  });
});
