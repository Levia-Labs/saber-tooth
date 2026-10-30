import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import fc from "fast-check";
import { afterEach, describe, expect, test } from "vitest";
import type { BsPlaylist } from "../src/api/beatsaver";
import {
  encodePlState,
  formatNpsRange,
  formatTotalLength,
  parsePlState,
  plApiParams,
  viewPlaylists,
  DEFAULT_PL_STATE,
} from "../src/lib/plfilters";
import { bsMap } from "./bshelpers";
import { mockFetch, renderApp } from "./helpers";
import { bsPlaylist } from "./plhelpers";

const real = window.matchMedia;
afterEach(() => {
  window.matchMedia = real;
});

function viewport(width: number) {
  window.matchMedia = ((query: string) => {
    const max = /\(max-width:\s*(\d+)px\)/.exec(query);
    return { ...real(query), media: query, matches: max ? width <= Number(max[1]) : false };
  }) as typeof window.matchMedia;
}

const LIST: BsPlaylist[] = [
  bsPlaylist("p1", { name: "Alpha", owner: "Alice", map_count: 5, upvotes: 10, duration: 600 }),
  bsPlaylist("p2", {
    name: "Beta",
    owner: "Bob",
    map_count: 50,
    upvotes: 900,
    duration: 7500,
    rating: 0.91,
  }),
  bsPlaylist("p3", { name: "Gamma", owner: "Alicia", map_count: 20, upvotes: 300, duration: 1800 }),
];

function api(pages?: (cursor: string | null) => unknown) {
  const posts: { path: string; body: unknown }[] = [];
  const stub = mockFetch((url, init) => {
    if (init?.method === "POST")
      posts.push({ path: url.pathname, body: JSON.parse(String(init.body)) });
    if (url.pathname === "/api/beatsaver/playlists/search") {
      return pages?.(url.searchParams.get("cursor")) ?? { items: LIST, cursor: null };
    }
    if (url.pathname.startsWith("/api/beatsaver/playlists/")) {
      return {
        playlist: LIST[0],
        items: [bsMap(1), bsMap(2, { installed: true })],
        cursor: null,
        scanned: 2,
        matched: 2,
      };
    }
    if (url.pathname === "/api/beatsaver/download") return { job: "j1" };
    if (url.pathname.startsWith("/api/jobs/")) {
      return { id: "j1", kind: "download", status: "done", error: null, result: { results: [] } };
    }
    if (url.pathname === "/api/beatsaver/config") return { playlists_enabled: false };
    if (url.pathname === "/api/beatsaver/presets") return [];
    return {};
  });
  return { ...stub, posts };
}

const names = () =>
  screen
    .getAllByRole("row")
    .map((r) => r.getAttribute("data-playlist"))
    .filter(Boolean);

describe("playlists table", () => {
  test("shows the stat columns, a separate author column and no playlist icon in rows", async () => {
    api();
    renderApp("/beatsaver/playlists");
    await screen.findByRole("link", { name: "Beta" });
    for (const label of [
      "Image",
      "Name",
      "Author",
      "Maps",
      "Rating",
      "Upvotes",
      "Length",
      "NPS",
      "Created",
      "Actions",
    ]) {
      expect(
        screen.getByRole("columnheader", { name: new RegExp(`^${label}`) }),
      ).toBeInTheDocument();
    }
    const row = screen.getByRole("link", { name: "Beta" }).closest("[role=row]") as HTMLElement;
    expect(row.querySelector(".col-title svg")).toBeNull();
    expect(row.querySelector(".col-author")).toHaveTextContent("Bob");
    expect(row.querySelector(".col-maps")).toHaveTextContent("50");
    expect(row.querySelector(".col-rating")).toHaveTextContent("91%");
    expect(row.querySelector(".col-length")).toHaveTextContent("2:05");
    expect(row.querySelector(".col-nps")).toHaveTextContent("1.2–6.4");
    expect(row.querySelector(".col-created")).toHaveTextContent("2024-03-01");
    expect(screen.queryByRole("columnheader", { name: /Downloads/ })).toBeNull();
  });

  test("row actions open the playlist, download all matching and link to BeatSaver", async () => {
    const { posts } = api();
    renderApp("/beatsaver/playlists");
    await screen.findByRole("link", { name: "Alpha" });
    expect(screen.getByRole("link", { name: "Open Alpha in Saber Tooth" })).toHaveAttribute(
      "href",
      "/beatsaver/playlists/p1?from=bs-playlists",
    );
    const site = screen.getByRole("link", { name: "Open Alpha on BeatSaver (new tab)" });
    expect(site).toHaveAttribute("target", "_blank");
    await userEvent.click(screen.getByRole("button", { name: "Download all maps of Alpha" }));
    const dialog = await screen.findByRole("dialog", { name: "Download maps" });
    expect(within(dialog).getByText(/1 new map will be downloaded/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Download 1 new" }));
    await waitFor(() =>
      expect(posts).toContainEqual({ path: "/api/beatsaver/download", body: { ids: ["k1"] } }),
    );
  });

  test("sorts the loaded rows by maps with the tip wording of the maps view", async () => {
    api();
    renderApp("/beatsaver/playlists");
    await screen.findByRole("link", { name: "Alpha" });
    expect(names()).toEqual(["p1", "p2", "p3"]);
    const sort = screen.getByRole("button", { name: "Sort by Maps" });
    await userEvent.hover(sort);
    expect(
      await screen.findAllByText("Sorted by map count among the playlists loaded so far."),
    ).not.toHaveLength(0);
    await userEvent.click(sort);
    await waitFor(() => expect(names()).toEqual(["p2", "p3", "p1"]));
    expect(screen.getByRole("columnheader", { name: /Maps/ })).toHaveAttribute(
      "aria-sort",
      "descending",
    );
    await userEvent.click(sort);
    await waitFor(() => expect(names()).toEqual(["p1", "p3", "p2"]));
  });

  test("server sort and filters go to the API and the URL", async () => {
    const { calls } = api();
    const { router } = renderApp("/beatsaver/playlists");
    await screen.findByRole("link", { name: "Alpha" });
    await userEvent.click(screen.getByRole("button", { name: "Sort by Rating" }));
    await waitFor(() => expect(router.state.location.search).toContain("order=Rating"));
    await waitFor(() => expect(calls.at(-1)?.searchParams.get("order")).toBe("Rating"));
    await router.navigate("/beatsaver/playlists?order=Curated&curated=true&maps_min=3&min_nps=1");
    await waitFor(() => {
      const last = calls.at(-1)!;
      expect(last.searchParams.get("curated")).toBe("true");
      expect(last.searchParams.get("maps_min")).toBe("3");
      expect(last.searchParams.get("min_nps")).toBe("1");
    });
  });

  test("author filter narrows loaded rows; the popover has an X and an inline clear", async () => {
    api();
    renderApp("/beatsaver/playlists?owner=alic");
    await screen.findByRole("link", { name: "Alpha" });
    expect(names()).toEqual(["p1", "p3"]);
    await userEvent.click(screen.getByRole("button", { name: /Filter Author/ }));
    const panel = await screen.findByRole("dialog", { name: "Author filter" });
    expect(within(panel).getByRole("button", { name: "Close filter" })).toBeInTheDocument();
    await userEvent.click(within(panel).getByRole("button", { name: "Clear Author filter" }));
    await userEvent.click(within(panel).getByRole("button", { name: "Close filter" }));
    await waitFor(() => expect(names()).toEqual(["p1", "p2", "p3"]));
  });

  test("loads the next page by the cursor while scrolling", async () => {
    const { calls } = api((cursor) =>
      cursor === "5"
        ? { items: [bsPlaylist("p9", { name: "Omega" })], cursor: null }
        : { items: LIST, cursor: "5" },
    );
    renderApp("/beatsaver/playlists");
    expect(await screen.findByRole("link", { name: "Omega" })).toBeInTheDocument();
    expect(calls.some((u) => u.searchParams.get("cursor") === "5")).toBe(true);
  });

  test("shows an alert when the first page fails and retries", async () => {
    let fail = true;
    mockFetch((url) => {
      if (url.pathname !== "/api/beatsaver/playlists/search") return {};
      if (fail) return new Response(JSON.stringify({ error: "down" }), { status: 502 });
      return { items: LIST, cursor: null };
    });
    renderApp("/beatsaver/playlists");
    const alert = await screen.findByRole("alert");
    expect(alert).toBeInTheDocument();
    fail = false;
    await userEvent.click(within(alert).getByRole("button", { name: /try again|retry/i }));
    expect(await screen.findByRole("link", { name: "Alpha" })).toBeInTheDocument();
  });

  test("mobile: cards, order bar and the fullscreen filter sheet", async () => {
    viewport(500);
    const { calls } = api();
    renderApp("/beatsaver/playlists");
    await screen.findByRole("link", { name: "Alpha" });
    expect(screen.getByRole("combobox", { name: "Order by" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /More filters/ }));
    const sheet = await screen.findByRole("dialog", { name: "Playlist filters" });
    await userEvent.click(within(sheet).getByLabelText("Curated playlists only"));
    await waitFor(() => expect(calls.at(-1)?.searchParams.get("curated")).toBe("true"));
  });
});

describe("playlist state", () => {
  test("round-trips through the URL", () => {
    const text = fc.stringMatching(/^[a-z0-9 &=%+]{0,12}$/).map((s) => s.trim());
    fc.assert(
      fc.property(
        text,
        text,
        fc.constantFrom("Latest", "Relevance", "Rating", "Curated"),
        fc.boolean(),
        fc.option(fc.integer({ min: 0, max: 1000 }), { nil: null }),
        (q, owner, order, curated, mapsMin) => {
          const state = { ...DEFAULT_PL_STATE, q, owner, order, curated, mapsMin };
          expect(parsePlState(encodePlState(state).toString())).toEqual(state);
        },
      ),
    );
  });

  test("an inverted range is dropped from the API query and owner never goes out", () => {
    const state = {
      ...DEFAULT_PL_STATE,
      mapsMin: 9,
      mapsMax: 3,
      owner: "x",
      localSort: "maps" as const,
    };
    const p = plApiParams(state, "2");
    expect(p.has("maps_min") || p.has("maps_max") || p.has("owner") || p.has("lsort")).toBe(false);
    expect(p.get("cursor")).toBe("2");
  });

  test("formats length as m:ss or h:mm and NPS as a range", () => {
    expect(formatTotalLength(125)).toBe("2:05");
    expect(formatTotalLength(7500)).toBe("2:05");
    expect(formatTotalLength(3600)).toBe("1:00");
    expect(formatNpsRange(0, 0)).toBe("–");
    expect(viewPlaylists(LIST, { ...DEFAULT_PL_STATE, owner: "bob" }).map((p) => p.id)).toEqual([
      "p2",
    ]);
  });
});
