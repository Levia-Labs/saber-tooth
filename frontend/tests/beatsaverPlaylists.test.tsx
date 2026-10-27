import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import type { BsPlaylist } from "../src/api/beatsaver";
import { bsMap } from "./bshelpers";
import { mockFetch, renderApp } from "./helpers";

const PLAYLISTS: BsPlaylist[] = [
  { id: "p1", name: "Gentle electronic", owner: "Alice", cover_url: null, map_count: 12 },
  { id: "p2", name: "Rock set", owner: "Bob", cover_url: null, map_count: 1, curated: true },
];

function api(extra?: { maps?: (url: URL) => unknown }) {
  const posts: { path: string; body: unknown }[] = [];
  const stub = mockFetch((url, init) => {
    const path = url.pathname;
    if (init?.method === "POST") posts.push({ path, body: JSON.parse(String(init.body)) });
    if (path === "/api/beatsaver/playlists/search") {
      const q = url.searchParams.get("q");
      return {
        items: q ? PLAYLISTS.filter((p) => p.name.toLowerCase().includes(q)) : PLAYLISTS,
        cursor: null,
      };
    }
    if (path.startsWith("/api/beatsaver/playlists/")) {
      return (
        extra?.maps?.(url) ?? {
          playlist: PLAYLISTS[0],
          items: [bsMap(1), bsMap(2, { installed: true }), bsMap(3)],
          cursor: null,
          scanned: 12,
          matched: 3,
        }
      );
    }
    if (path === "/api/beatsaver/config") return { playlists_enabled: false };
    if (path === "/api/beatsaver/presets") return [];
    if (path === "/api/beatsaver/download") return { job: "j1" };
    if (path.startsWith("/api/jobs/")) {
      return { id: "j1", kind: "download", status: "done", error: null, result: { results: [] } };
    }
    return {};
  });
  return { ...stub, posts };
}

describe("BeatSaver playlists tab", () => {
  test("lists playlists, searches them and links each to its page", async () => {
    const { calls } = api();
    renderApp("/beatsaver/playlists");
    const link = await screen.findByRole("link", { name: "Gentle electronic" });
    expect(link).toHaveAttribute("href", "/beatsaver/playlists/p1");
    expect(screen.getByText(/Bob/)).toHaveTextContent("1 map");
    await userEvent.type(screen.getByLabelText("Search playlists"), "rock");
    await waitFor(() =>
      expect(screen.queryByRole("link", { name: "Gentle electronic" })).toBeNull(),
    );
    expect(await screen.findByRole("link", { name: "Rock set" })).toBeInTheDocument();
    expect(
      calls.some(
        (u) => u.pathname.endsWith("/playlists/search") && u.searchParams.get("q") === "rock",
      ),
    ).toBe(true);
  });

  test("opening a playlist shows its maps with the local filters sent to the API", async () => {
    const { calls } = api();
    const { router } = renderApp("/beatsaver/playlists");
    await userEvent.click(await screen.findByRole("link", { name: "Gentle electronic" }));
    await screen.findByText("Song 1");
    expect(router.state.location.pathname).toBe("/beatsaver/playlists/p1");
    expect(screen.getByRole("heading", { name: "Gentle electronic" })).toBeInTheDocument();
    await router.navigate("/beatsaver/playlists/p1?diffs=Easy,Normal,Hard&nps_min=1&nps_max=2");
    await waitFor(() => {
      const last = calls.filter((u) => u.pathname === "/api/beatsaver/playlists/p1").at(-1)!;
      expect(last.searchParams.get("diffs")).toBe("Easy,Normal,Hard");
      expect(last.searchParams.get("nps_min")).toBe("1");
      expect(last.searchParams.get("nps_max")).toBe("2");
    });
  });

  test("Download all matching confirms new versus installed maps, then downloads the new ones", async () => {
    const { posts } = api();
    renderApp("/beatsaver/playlists/p1");
    await screen.findByText("Song 1");
    await userEvent.click(screen.getByRole("button", { name: "Download all matching" }));
    const dialog = await screen.findByRole("dialog", { name: "Download maps" });
    expect(within(dialog).getByText(/2 new maps will be downloaded/)).toBeInTheDocument();
    expect(within(dialog).getByText(/1 map already installed will be skipped/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Download 2 new" }));
    await waitFor(() =>
      expect(posts).toContainEqual({
        path: "/api/beatsaver/download",
        body: { ids: ["k1", "k3"] },
      }),
    );
  });

  test("Download all matching loads the remaining pages first", async () => {
    const { calls } = api({
      maps: (url) =>
        url.searchParams.get("cursor")
          ? { playlist: PLAYLISTS[0], items: [bsMap(4)], cursor: null, scanned: 5, matched: 1 }
          : { playlist: PLAYLISTS[0], items: [bsMap(1)], cursor: "2", scanned: 5, matched: 1 },
    });
    renderApp("/beatsaver/playlists/p1");
    await screen.findByText("Song 1");
    await userEvent.click(screen.getByRole("button", { name: "Download all matching" }));
    const dialog = await screen.findByRole("dialog", { name: "Download maps" });
    expect(within(dialog).getByText(/2 new maps will be downloaded/)).toBeInTheDocument();
    expect(calls.filter((u) => u.searchParams.get("cursor") === "2").length).toBeGreaterThan(0);
  });
});
