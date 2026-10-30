import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { Playlist, PlaylistSong } from "../src/api/playlists";
import { LABELS } from "../src/lib/columns";
import { item, mockFetch, renderApp } from "./helpers";

const PNG_B64 = btoa("\x89PNG\r\n\x1a\n0000");

const song = (n: number, patch: Partial<PlaylistSong> = {}): PlaylistSong => ({
  map_id: item(n).id,
  hash: "A".repeat(40),
  key: null,
  song_name: `Song ${n}`,
  mapper: `Mapper ${n}`,
  missing: false,
  cover_url: null,
  map: item(n),
  ...patch,
});

const GONE = song(9, { map_id: null, hash: "B".repeat(40), missing: true, map: null });

function playlist(patch: Partial<Playlist> = {}): Playlist {
  return {
    id: "p1",
    title: "Chill",
    author: "me",
    description: "",
    folder: "",
    sync: false,
    sync_url: "http://localhost/api/playlists/p1/bplist",
    exported: "",
    updated_at: "t",
    songs_count: 3,
    missing_count: 1,
    cover_url: null,
    songs: [song(1), song(2), GONE],
    ...patch,
  };
}

function serve(bodies: unknown[] = []) {
  return mockFetch((url, init) => {
    const { pathname } = url;
    if (pathname === "/api/playlists" && init?.method === "POST") {
      bodies.push(JSON.parse(String(init.body)));
      return playlist({ id: "n", title: "Mine" });
    }
    if (pathname === "/api/playlists/p1" && init?.method === "POST") {
      bodies.push(JSON.parse(String(init.body)));
      return playlist();
    }
    if (pathname === "/api/playlists/p1") return playlist();
    if (pathname === "/api/playlists/n") return playlist({ id: "n", title: "Mine", songs: [] });
    if (pathname === "/api/playlists/config") return { export_enabled: true, live: {} };
    if (pathname === "/api/playlists/n/export") return { path: "x", relative: "Mine.bplist" };
    if (pathname === `/api/maps/${item(1).id}`) return item(1);
    if (pathname === "/api/maps") return { items: [item(1)], total: 1, offset: 0, limit: 12 };
    if (pathname === "/api/jobs") return { running: [], queued: [], recent: [] };
    return {};
  });
}

const heading = () => screen.getByRole("heading", { level: 1 });

describe("playlist page name", () => {
  test("pencil opens an input; Enter saves the name into the title", async () => {
    serve();
    renderApp("/playlists/new");
    expect((await screen.findByRole("heading", { level: 1 })).textContent).toContain(
      "Untitled playlist",
    );
    fireEvent.click(screen.getByRole("button", { name: "Edit name" }));
    const input = screen.getByLabelText("Playlist name");
    expect(document.activeElement).toBe(input);
    fireEvent.change(input, { target: { value: "Night drive" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(screen.queryByLabelText("Playlist name")).toBeNull();
    expect(heading().textContent).toContain("Night drive");
  });

  test("clicking the name edits it; Escape cancels; blur saves", async () => {
    serve();
    renderApp("/playlists/p1");
    await screen.findByRole("button", { name: "Chill" });
    fireEvent.click(screen.getByRole("button", { name: "Chill" }));
    let input = screen.getByLabelText("Playlist name");
    fireEvent.change(input, { target: { value: "Changed" } });
    fireEvent.keyDown(input, { key: "Escape" });
    expect(heading().textContent).toContain("Chill");
    fireEvent.click(screen.getByRole("button", { name: "Chill" }));
    input = screen.getByLabelText("Playlist name");
    fireEvent.change(input, { target: { value: "Blurred" } });
    fireEvent.blur(input);
    expect(heading().textContent).toContain("Blurred");
    expect(screen.getByText("Unsaved changes")).toBeTruthy();
  });

  test("an empty name is not saved", async () => {
    serve();
    renderApp("/playlists/p1");
    await screen.findByRole("button", { name: "Chill" });
    fireEvent.click(screen.getByRole("button", { name: "Edit name" }));
    const input = screen.getByLabelText("Playlist name");
    fireEvent.change(input, { target: { value: "  " } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(heading().textContent).toContain("Chill");
  });
});

describe("playlist page cover", () => {
  test("upload previews at once and is sent with the playlist", async () => {
    const bodies: unknown[] = [];
    serve(bodies);
    renderApp("/playlists/new");
    fireEvent.click(screen.getByRole("button", { name: "Change cover" }));
    const file = new File([Uint8Array.from(atob(PNG_B64), (c) => c.charCodeAt(0))], "c.png", {
      type: "image/png",
    });
    fireEvent.change(screen.getByLabelText("Cover file"), { target: { files: [file] } });
    await waitFor(() =>
      expect(document.querySelector("img.cover-big")?.getAttribute("src")).toMatch(
        /^data:image\/png;base64,/,
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Edit name" }));
    const input = screen.getByLabelText("Playlist name");
    fireEvent.change(input, { target: { value: "Mine" } });
    fireEvent.keyDown(input, { key: "Enter" });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({ title: "Mine", cover: { data: PNG_B64 } });
  });

  test("a non-image file is refused", async () => {
    serve();
    renderApp("/playlists/new");
    const file = new File(["x"], "c.txt", { type: "text/plain" });
    fireEvent.change(screen.getByLabelText("Cover file"), { target: { files: [file] } });
    expect(await screen.findByText("The cover must be a PNG or JPEG image.")).toBeTruthy();
    expect(document.querySelector("img.cover-big")).toBeNull();
  });

  test("a stored cover shows with the same placeholder rule as the library", async () => {
    serve();
    renderApp("/playlists/p1");
    await screen.findByRole("button", { name: "Chill" });
    expect(document.querySelector(".cover-big.cover-empty")).not.toBeNull();
  });
});

describe("playlist page songs", () => {
  test("the table has the library columns and rows with only a Remove action", async () => {
    serve();
    renderApp("/playlists/p1");
    await screen.findByRole("button", { name: "Chill" });
    const table = await screen.findByRole("table", { name: "Songs in the playlist" });
    await screen.findByText("Song 2");
    const heads = within(table)
      .getAllByRole("columnheader")
      .map((h) => h.textContent);
    for (const label of [
      LABELS.title,
      LABELS.author,
      LABELS.levels,
      LABELS.length,
      LABELS.bpm,
      LABELS.status,
      LABELS.actions,
    ]) {
      expect(heads.some((h) => h?.includes(label))).toBe(true);
    }
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(3);
    for (const row of rows) {
      const buttons = within(row).getAllByRole("button");
      const actions = buttons.filter((b) =>
        /Remove .* from playlist/.test(b.getAttribute("aria-label") ?? b.textContent ?? ""),
      );
      expect(actions).toHaveLength(1);
      expect(within(row).queryByRole("link", { name: /Review/ })).toBeNull();
    }
    expect(within(rows[2]!).getAllByRole("img", { name: /Missing/ }).length).toBeGreaterThan(0);
  });

  test("Remove drops the song from the draft and the next save omits it", async () => {
    const bodies: unknown[] = [];
    serve(bodies);
    renderApp("/playlists/p1");
    await screen.findByRole("button", { name: "Chill" });
    const table = await screen.findByRole("table", { name: "Songs in the playlist" });
    await screen.findByText("Song 2");
    fireEvent.click(within(table).getByRole("button", { name: "Remove Song 1 from playlist" }));
    expect(within(table).getAllByRole("row")).toHaveLength(3);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(bodies).toHaveLength(1));
    const sent = (bodies[0] as { songs: { map_id?: string; hash?: string }[] }).songs;
    expect(sent.map((s) => s.map_id ?? s.hash)).toEqual([item(2).id, "B".repeat(40)]);
  });

  test("library sort works on the songs table", async () => {
    serve();
    renderApp("/playlists/p1");
    await screen.findByRole("button", { name: "Chill" });
    const table = await screen.findByRole("table", { name: "Songs in the playlist" });
    await screen.findByText("Song 2");
    const titles = () =>
      within(table)
        .getAllByRole("row")
        .slice(1)
        .map((r) => within(r).getAllByRole("cell")[1]?.textContent);
    expect(titles()[0]).toContain("Song 1");
    fireEvent.click(within(table).getByRole("button", { name: /Sort by Title/ }));
    expect(titles()[0]).toContain("Song 9");
  });
});

describe("playlist page export and create", () => {
  test("add a library song, set a subfolder, save and export", async () => {
    const bodies: unknown[] = [];
    const { calls } = serve(bodies);
    renderApp("/playlists/new");
    fireEvent.click(screen.getByRole("button", { name: "Edit name" }));
    const input = screen.getByLabelText("Playlist name");
    fireEvent.change(input, { target: { value: "Mine" } });
    fireEvent.keyDown(input, { key: "Enter" });
    fireEvent.click(screen.getByRole("button", { name: "Add songs" }));
    fireEvent.click(await screen.findByRole("button", { name: "Add Song 1" }));
    await waitFor(() =>
      expect(
        within(screen.getByRole("table", { name: "Songs in the playlist" })).getByText("Song 1"),
      ).toBeTruthy(),
    );
    fireEvent.change(screen.getByLabelText(/Subfolder/), { target: { value: "saber-tooth" } });
    expect(screen.getAllByText(/PlaylistManager refreshes/).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Save and export" }));
    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({
      title: "Mine",
      folder: "saber-tooth",
      songs: [{ map_id: item(1).id }],
    });
    await waitFor(() =>
      expect(calls.some((u) => u.pathname === "/api/playlists/n/export")).toBe(true),
    );
  });

  test("the VR twin mounts the same page", async () => {
    serve();
    renderApp("/vr/playlists/p1");
    expect(await screen.findByRole("button", { name: "Chill" })).toBeTruthy();
  });
});
