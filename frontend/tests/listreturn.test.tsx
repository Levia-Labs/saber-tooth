import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test } from "vitest";
import { useListScroll } from "../src/lib/listscroll";
import { TIMELINE } from "./crophelpers";
import { item, mockFetch, renderApp } from "./helpers";

const css = (name: string) => readFileSync(resolve(__dirname, "../src/styles", name), "utf8");

beforeEach(() => sessionStorage.clear());
afterEach(() => sessionStorage.clear());

function Harness({ ready, count }: { ready: boolean; count: number }) {
  useListScroll(ready, count, false);
  return <div className="lib-scroll" data-testid="s" />;
}
const mount = (ready: boolean, count: number, at = "/?q=1") =>
  render(
    <MemoryRouter initialEntries={[at]}>
      <Harness ready={ready} count={count} />
    </MemoryRouter>,
  );

describe("list scroll restore", () => {
  test("a scrolled list is restored by its path and query after the rows render", () => {
    const first = mount(true, 5);
    const el = screen.getByTestId("s");
    el.scrollTop = 340;
    fireEvent.scroll(el);
    expect(sessionStorage.getItem("saber-tooth.scroll:/?q=1")).toBe("340");
    first.unmount();
    const waiting = mount(false, 0);
    expect(screen.getByTestId("s").scrollTop).toBe(0);
    waiting.rerender(
      <MemoryRouter initialEntries={["/?q=1"]}>
        <Harness ready count={5} />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("s").scrollTop).toBe(340);
  });

  test("another query keeps its own position", () => {
    sessionStorage.setItem("saber-tooth.scroll:/?q=1", "340");
    mount(true, 5, "/?q=2");
    expect(screen.getByTestId("s").scrollTop).toBe(0);
  });

  test("an unrestored list does not overwrite the saved position", () => {
    sessionStorage.setItem("saber-tooth.scroll:/?q=1", "340");
    mount(false, 0);
    fireEvent.scroll(screen.getByTestId("s"));
    expect(sessionStorage.getItem("saber-tooth.scroll:/?q=1")).toBe("340");
  });
});

const pl = (id: string, title: string) => ({
  id,
  title,
  author: "",
  description: "",
  folder: "",
  sync: false,
  sync_url: "",
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
      song_name: "S",
      mapper: "m",
      missing: false,
      cover_url: null,
      map: item(1, { status: "error", errors: 2 }),
    },
  ],
});

function serve() {
  return mockFetch((url) => {
    const p = url.pathname;
    if (p === "/api/playlists") return { items: [pl("a", "Alpha"), pl("b", "Bravo")] };
    if (p === "/api/playlists/config") return { export_enabled: true, live: {} };
    if (p === "/api/playlists/a") return pl("a", "Alpha");
    if (p === "/api/playlists/b") return pl("b", "Bravo");
    if (p === "/api/maps/id0000000002") return item(2, { status: "crop" });
    if (p === "/api/maps/id0000000003") return item(3, { status: "error", errors: 2 });
    if (p.endsWith("/neighbors")) return {};
    if (p.endsWith("/timeline")) return TIMELINE;
    if (p.endsWith("/proposals")) return [];
    if (p === "/api/jobs") return { running: [], queued: [], recent: [] };
    return { items: [], total: 0, offset: 0, limit: 40 };
  });
}

describe("playlists list and page", () => {
  test("a playlist opens by a real link and Back to list keeps the list query", async () => {
    serve();
    const { router } = renderApp("/playlists?x=1");
    const link = await screen.findByRole("link", { name: "Alpha" });
    expect(link).toHaveAttribute("href", "/playlists/a?from=playlists&back=x%3D1");
    await router.navigate("/playlists/a?from=playlists&back=x%3D1");
    expect(await screen.findByRole("link", { name: "Back to list" })).toHaveAttribute(
      "href",
      "/playlists?x=1",
    );
  });

  test("the playlist footer is pinned like the map page footer", async () => {
    serve();
    const { container } = renderApp("/playlists/a");
    await screen.findByRole("navigation", { name: "Neighbouring playlists" });
    const page = container.querySelector("section.page")!;
    expect(page).toHaveClass("map-page");
    expect(page.lastElementChild).toHaveClass("map-footer");
    expect(page.querySelector(".map-scroll")).not.toBeNull();
    expect(css("mapfooter.css")).not.toMatch(/\.lp-page > \.map-footer/);
  });

  test("a song's status chip links to the map page from the playlist", async () => {
    serve();
    renderApp("/playlists/a");
    const chip = await screen.findByRole("link", { name: "Open status: 2 errors" });
    expect(chip).toHaveAttribute("href", "/maps/id0000000001?tab=status&from=playlist%3Aa");
  });
});

describe("map header status chip", () => {
  test("a crop chip switches to the Crop tab without navigating", async () => {
    serve();
    const { router } = renderApp("/maps/id0000000002?from=library");
    fireEvent.click(await screen.findByRole("button", { name: "Open crop" }));
    await waitFor(() => expect(router.state.location.search).toContain("tab=crop"));
    expect(router.state.location.pathname).toBe("/maps/id0000000002");
  });

  test("an error chip switches back to the Status tab", async () => {
    serve();
    const { router } = renderApp("/maps/id0000000003?tab=delete&from=library");
    fireEvent.click(await screen.findByRole("button", { name: "Open status: 2 errors" }));
    await waitFor(() => expect(router.state.location.search).not.toContain("tab="));
  });
});
