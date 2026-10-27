import { screen, waitFor } from "@testing-library/react";
import { expect, test } from "vitest";
import { bsMap } from "./bshelpers";
import { mockFetch, renderApp } from "./helpers";

const PLAYLIST = {
  id: "52354",
  name: "Rock",
  owner: "someone",
  cover_url: "https://cdn.beatsaver.com/playlist/52354.png",
  map_count: 302,
};

test("playlist page renders the playlist and loads more with the dotted cursor", async () => {
  const { calls } = mockFetch((url) => {
    const p = url.pathname;
    if (p === "/api/beatsaver/playlists/52354") {
      const more = url.searchParams.get("cursor") === "0.40";
      return {
        playlist: PLAYLIST,
        items: more ? [bsMap(41)] : [bsMap(1), bsMap(2)],
        cursor: more ? null : "0.40",
        scanned: 40,
        matched: more ? 1 : 2,
      };
    }
    if (p === "/api/beatsaver/config") return { playlists_enabled: false };
    if (p === "/api/beatsaver/presets") return [];
    return {};
  });
  renderApp("/beatsaver/playlists/52354");
  expect(await screen.findByRole("heading", { name: "Rock" })).toBeInTheDocument();
  expect(await screen.findByText("Song 1")).toBeInTheDocument();
  expect(await screen.findByText("Song 41")).toBeInTheDocument();
  await waitFor(() =>
    expect(calls.some((u) => u.searchParams.get("cursor") === "0.40")).toBe(true),
  );
});
