import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { VrBsPlaylists } from "../src/vr/VrBsPlaylists";
import { VrBeatSaverPage } from "../src/vr/VrBeatSaverPage";
import { VrLibraryPage } from "../src/vr/VrLibraryPage";
import { bsMap, page } from "./bshelpers";
import { item, mockFetch } from "./helpers";
import { renderVr, stubObserver } from "./vrhelpers";

const bad = () =>
  new Response(JSON.stringify({ error: "nope" }), {
    status: 400,
    headers: { "Content-Type": "application/json" },
  });
const settle = () => new Promise((resolve) => setTimeout(resolve, 60));

const PLAYLIST = {
  id: "p1",
  name: "Best of 2024",
  owner: "Alice",
  cover_url: null,
  map_count: 12,
  mapper_count: 5,
  duration: 3600,
  upvotes: 10,
  downvotes: 0,
  rating: 0.9,
  min_nps: 1,
  max_nps: 4,
  created_at: "2024-01-01T00:00:00Z",
  curated: false,
};

describe("a failed load-more in the VR lists", () => {
  test("the library asks once, shows the error, and Try again asks once more", async () => {
    stubObserver(true);
    let failing = true;
    const { calls } = mockFetch((url) => {
      if (url.pathname !== "/api/maps") return {};
      const offset = Number(url.searchParams.get("offset") ?? "0");
      if (offset > 0 && failing) return bad();
      return {
        items: [item(1), item(2), item(3)].slice(offset, offset + 2),
        total: 3,
        offset,
        limit: 2,
      };
    });
    const user = userEvent.setup();
    renderVr("/vr", "/vr", <VrLibraryPage />);
    await screen.findByText("Could not load more maps.");
    await settle();
    const more = () => calls.filter((u) => u.searchParams.get("offset") === "2");
    expect(more()).toHaveLength(1);
    failing = false;
    await user.click(screen.getByRole("button", { name: "Try again" }));
    await screen.findByRole("heading", { name: "Song 3" });
    await settle();
    expect(more()).toHaveLength(2);
    expect(screen.queryByText("Could not load more maps.")).toBeNull();
  });

  test("the BeatSaver maps ask once, show the error, and Try again asks once more", async () => {
    stubObserver(true);
    let failing = true;
    const { calls } = mockFetch((url) => {
      if (url.pathname === "/api/beatsaver/search") {
        if (url.searchParams.get("cursor") === "c1") {
          return failing ? bad() : page([bsMap(3)]);
        }
        return page([bsMap(1), bsMap(2)], { cursor: "c1" });
      }
      return url.pathname === "/api/beatsaver/presets" ? [] : {};
    });
    const user = userEvent.setup();
    renderVr("/vr/beatsaver", "/vr/beatsaver", <VrBeatSaverPage />);
    await screen.findByText("Could not load more maps.");
    await settle();
    const more = () => calls.filter((u) => u.searchParams.get("cursor") === "c1");
    expect(more()).toHaveLength(1);
    failing = false;
    await user.click(screen.getByRole("button", { name: "Try again" }));
    await screen.findByRole("heading", { name: "Song 3" });
    await settle();
    expect(more()).toHaveLength(2);
  });

  test("the playlists ask once, show the error, and Try again asks once more", async () => {
    stubObserver(true);
    let failing = true;
    const { calls } = mockFetch((url) => {
      if (url.pathname !== "/api/beatsaver/playlists/search") return {};
      if (url.searchParams.get("cursor") === "c1") {
        return failing
          ? bad()
          : { items: [{ ...PLAYLIST, id: "p2", name: "Second" }], cursor: null };
      }
      return { items: [PLAYLIST], cursor: "c1" };
    });
    const user = userEvent.setup();
    renderVr("/vr/beatsaver", "/vr/beatsaver", <VrBsPlaylists />);
    await screen.findByText("Could not load more maps.");
    await settle();
    const more = () => calls.filter((u) => u.searchParams.get("cursor") === "c1");
    expect(more()).toHaveLength(1);
    failing = false;
    await user.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Second" })).toBeInTheDocument(),
    );
    await settle();
    expect(more()).toHaveLength(2);
  });
});
