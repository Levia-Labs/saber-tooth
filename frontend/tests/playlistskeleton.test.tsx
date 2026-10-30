import { screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { FIRST_SKELETONS } from "../src/components/LibraryTable";
import { item, mockFetch, renderApp } from "./helpers";

const PLAYLIST = {
  id: "p1",
  title: "Chill",
  author: "me",
  description: "",
  folder: "",
  sync: false,
  sync_url: "http://localhost/api/playlists/p1/bplist",
  exported: "",
  updated_at: "t",
  songs_count: 1,
  missing_count: 0,
  cover_url: null,
  songs: [
    {
      map_id: item(1).id,
      hash: "A".repeat(40),
      key: null,
      song_name: "Song 1",
      mapper: "M",
      missing: false,
      cover_url: null,
      map: item(1),
    },
  ],
};

test("the playlist page shows header and song-table skeletons, then the content", async () => {
  let release: (value: unknown) => void = () => {};
  const pending = new Promise((resolve) => (release = resolve));
  mockFetch((url) => {
    if (url.pathname === "/api/playlists/p1") return pending;
    if (url.pathname === "/api/playlists/config") return { export_enabled: true, live: {} };
    if (url.pathname === `/api/maps/${item(1).id}`) return item(1);
    if (url.pathname === "/api/maps") return { items: [item(1)], total: 1, offset: 0, limit: 12 };
    return {};
  });
  const { container } = renderApp("/playlists/p1");
  const region = await screen.findByRole("region", { name: "Loading playlist" });
  expect(region).toHaveAttribute("aria-busy", "true");
  expect(region.textContent).not.toMatch(/Loading/);
  expect(container.querySelector(".maphead .sk.cover")).not.toBeNull();
  expect(container.querySelectorAll(".skeleton-row")).toHaveLength(FIRST_SKELETONS);
  expect(screen.getByRole("table", { name: "Songs in the playlist" })).toBeInTheDocument();
  release(PLAYLIST);
  expect(await screen.findByRole("button", { name: "Chill" })).toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Loading playlist" })).toBeNull();
  expect(container.querySelectorAll(".skeleton-row")).toHaveLength(0);
});
