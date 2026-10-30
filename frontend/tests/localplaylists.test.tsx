import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { Playlist } from "../src/api/playlists";
import { filterPlaylists, LP_DEFAULT, sortPlaylists } from "../src/lib/lpfilters";
import { item, mockFetch, renderApp } from "./helpers";

function playlist(id: string, patch: Partial<Playlist> = {}): Playlist {
  return {
    id,
    title: `List ${id}`,
    author: "",
    description: "",
    folder: "",
    sync: false,
    sync_url: `http://localhost/api/playlists/${id}/bplist`,
    exported: "",
    updated_at: "t",
    songs_count: 2,
    missing_count: 0,
    cover_url: null,
    ...patch,
  };
}

const LISTS = [
  playlist("b", {
    title: "Beta",
    songs_count: 5,
    missing_count: 1,
    folder: "saber-tooth",
    sync: true,
  }),
  playlist("a", { title: "Alpha", songs_count: 9 }),
];

function serve(created: unknown[] = []) {
  return mockFetch((url, init) => {
    const { pathname } = url;
    if (pathname === "/api/playlists" && init?.method === "POST") {
      created.push(JSON.parse(String(init.body)));
      return { ...playlist("n"), title: "Mine" };
    }
    if (pathname === "/api/playlists") return { items: LISTS };
    if (pathname === "/api/playlists/config") return { export_enabled: true, live: {} };
    if (pathname === "/api/maps") return { items: [item(1)], total: 1, offset: 0, limit: 12 };
    if (pathname === "/api/playlists/n/export") return { path: "x", relative: "Mine.bplist" };
    if (pathname === "/api/jobs") return { running: [], queued: [], recent: [] };
    return {};
  });
}

const names = () =>
  screen
    .getAllByRole("row")
    .slice(1)
    .map((r) => within(r).getAllByRole("cell")[1]?.textContent);

describe("local playlists", () => {
  test("pure sort and filter", () => {
    expect(sortPlaylists(LISTS, LP_DEFAULT).map((p) => p.id)).toEqual(["a", "b"]);
    expect(sortPlaylists(LISTS, { ...LP_DEFAULT, sort: "songs", ascending: false })[0]?.id).toBe(
      "a",
    );
    expect(filterPlaylists(LISTS, { ...LP_DEFAULT, sync: "on" }).map((p) => p.id)).toEqual(["b"]);
    expect(filterPlaylists(LISTS, { ...LP_DEFAULT, missing: true }).map((p) => p.id)).toEqual([
      "b",
    ]);
    expect(filterPlaylists(LISTS, { ...LP_DEFAULT, q: "alp" }).map((p) => p.id)).toEqual(["a"]);
  });

  test("the table lists playlists in library style with the Playlists tab", async () => {
    serve();
    renderApp("/playlists");
    await screen.findByText("Alpha");
    const heads = screen.getAllByRole("columnheader").map((h) => h.textContent);
    expect(heads).toEqual(["Icon", "Title", "Songs", "Folder", "Sync", "Actions"]);
    expect(names()).toEqual(["Alpha", "Beta"]);
    expect(screen.getByText("1 missing")).toBeTruthy();
    const tabs = screen.getByRole("navigation", { name: "Section" });
    expect(within(tabs).getByText("Playlists")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Sort by Songs" }));
    expect(names()).toEqual(["Alpha", "Beta"]);
    fireEvent.click(screen.getByRole("button", { name: "Sort by Title" }));
    expect(names()).toEqual(["Alpha", "Beta"]);
    fireEvent.click(screen.getByRole("button", { name: "Sort by Title" }));
    expect(names()).toEqual(["Beta", "Alpha"]);
  });

  test("the VR route mounts the same page", async () => {
    serve();
    renderApp("/vr/playlists");
    await screen.findByText("Alpha");
  });

  test("New playlist and a row open the playlist page", async () => {
    serve();
    const { router } = renderApp("/playlists");
    await screen.findByText("Alpha");
    fireEvent.click(screen.getByRole("link", { name: "New playlist" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/playlists/new"));
    await router.navigate("/playlists");
    fireEvent.click(await screen.findByRole("link", { name: "Alpha" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/playlists/a"));
  });

  test("delete asks first", async () => {
    const { calls } = serve();
    renderApp("/playlists");
    await screen.findByText("Alpha");
    fireEvent.click(screen.getByRole("button", { name: "Delete Alpha" }));
    fireEvent.click(await screen.findByRole("button", { name: "Delete playlist" }));
    await waitFor(() => expect(calls.some((u) => u.pathname === "/api/playlists/a")).toBe(true));
  });
});
