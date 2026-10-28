import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import type { BsPage } from "../src/api/beatsaver";
import { VrBeatSaverPage } from "../src/vr/VrBeatSaverPage";
import { bsApi, bsMap, page, SEEDED } from "./bshelpers";
import { mockFetch } from "./helpers";
import { renderVr, stubObserver } from "./vrhelpers";

const show = (url = "/vr/beatsaver") => renderVr(url, "/vr/beatsaver", <VrBeatSaverPage />);
const searches = (calls: URL[]) => calls.filter((u) => u.pathname === "/api/beatsaver/search");
const lastSearch = (calls: URL[]) => searches(calls).at(-1)!.searchParams;

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

describe("VR BeatSaver cards", () => {
  test("a card shows the map and a large Download", async () => {
    bsApi();
    show();
    const card = (await screen.findByRole("heading", { name: "Song 1" })).closest("article")!;
    expect(within(card).getByText(/Mapper 1/)).toBeInTheDocument();
    expect(within(card).getByText(/96%/)).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Download Song 1" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Download Song 2" })).toBeEnabled();
  });

  test("Download posts that map's id and locks the other Downloads while the job runs", async () => {
    const { posts } = bsApi();
    const user = userEvent.setup();
    show();
    await user.click(await screen.findByRole("button", { name: "Download Song 1" }));
    await waitFor(() =>
      expect(posts).toEqual([{ path: "/api/beatsaver/download", body: { ids: ["k1"] } }]),
    );
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Downloading: Song 1" })).toBeDisabled(),
    );
    expect(screen.getByRole("button", { name: "Download Song 2" })).toBeDisabled();
  });

  test("an installed map says so and cannot be downloaded again", async () => {
    bsApi({ search: () => page([bsMap(1, { installed: true, library_id: "id0000000001" })]) });
    show();
    expect(await screen.findByRole("button", { name: "Installed: Song 1" })).toBeDisabled();
  });

  test("a failed download shows its reason and offers a retry", async () => {
    bsApi({
      job: () => ({
        id: "j1",
        kind: "download",
        status: "done",
        error: null,
        result: { results: [{ id: "k1", status: "failed", reason: "zip is corrupt" }] },
      }),
    });
    const user = userEvent.setup();
    show();
    await user.click(await screen.findByRole("button", { name: "Download Song 1" }));
    expect(await screen.findByText("zip is corrupt")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry download: Song 1" })).toBeEnabled();
  });

  test("there is no free-text search", async () => {
    bsApi();
    show();
    await screen.findByRole("heading", { name: "Song 1" });
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("searchbox")).toBeNull();
  });

  test("a failed search shows an alert", async () => {
    mockFetch(
      () =>
        new Response(JSON.stringify({ error: "bad" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }),
    );
    show();
    expect(await screen.findByText("Could not load BeatSaver")).toBeInTheDocument();
  });

  test("an empty result says so", async () => {
    bsApi({ search: () => page([]) });
    show();
    expect(await screen.findByText(/No maps match/)).toBeInTheDocument();
  });
});

describe("VR BeatSaver presets, sort and paging", () => {
  test("a preset is a toggle with its description as text and applies its filters", async () => {
    const { calls } = bsApi();
    const user = userEvent.setup();
    show();
    const toggle = await screen.findByRole("button", { name: SEEDED.name });
    expect(toggle).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByText(/with Easy, Normal and Hard/)).toBeInTheDocument();
    await user.click(toggle);
    await waitFor(() => expect(lastSearch(calls).get("order")).toBe("Rating"));
    expect(lastSearch(calls).get("diffs")).toBe("Easy,Normal,Hard");
    expect(lastSearch(calls).get("min_rating")).toBe("0.95");
    expect(screen.getByRole("button", { name: SEEDED.name })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  test("pressing an active preset again clears the filters", async () => {
    const { calls } = bsApi();
    const user = userEvent.setup();
    show();
    await user.click(await screen.findByRole("button", { name: SEEDED.name }));
    await waitFor(() => expect(lastSearch(calls).get("diffs")).toBe("Easy,Normal,Hard"));
    await user.click(screen.getByRole("button", { name: SEEDED.name }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: SEEDED.name })).toHaveAttribute(
        "aria-pressed",
        "false",
      ),
    );
    // The unfiltered list is already cached, so the address is what proves the filters went.
    expect(screen.getByTestId("where")).not.toHaveTextContent("diffs");
  });

  test("the sort choice asks for that order", async () => {
    const { calls } = bsApi();
    const user = userEvent.setup();
    show();
    await screen.findByRole("heading", { name: "Song 1" });
    expect(screen.getByRole("radio", { name: "Latest" })).toBeChecked();
    await user.click(screen.getByRole("radio", { name: "Duration" }));
    await waitFor(() => expect(lastSearch(calls).get("order")).toBe("Duration"));
    expect(screen.getByRole("radio", { name: "Duration" })).toBeChecked();
  });

  test("the next page loads with the cursor when the end of the list scrolls into view", async () => {
    const observer = stubObserver();
    const first: BsPage = page([bsMap(1), bsMap(2)], { cursor: "c1" });
    const { calls } = bsApi({
      search: (url) => (url.searchParams.get("cursor") === "c1" ? page([bsMap(3)]) : first),
    });
    show();
    await screen.findByRole("heading", { name: "Song 2" });
    observer.fire();
    expect(await screen.findByRole("heading", { name: "Song 3" })).toBeInTheDocument();
    expect(searches(calls).map((u) => u.searchParams.get("cursor"))).toEqual([null, "c1"]);
  });
});

describe("VR BeatSaver playlists", () => {
  function playlistApi() {
    return mockFetch((url) => {
      if (url.pathname === "/api/beatsaver/playlists/search") {
        return { items: [PLAYLIST], cursor: null };
      }
      if (url.pathname === "/api/beatsaver/playlists/p1") {
        return { ...page([bsMap(5)]), playlist: PLAYLIST };
      }
      if (url.pathname === "/api/beatsaver/presets") return [];
      if (url.pathname === "/api/beatsaver/download") return { job: "j1" };
      if (url.pathname.startsWith("/api/jobs/")) {
        return { id: "j1", kind: "download", status: "running", error: null, result: null };
      }
      return {};
    });
  }

  test("the section links switch between maps and playlists", async () => {
    bsApi();
    show();
    const nav = await screen.findByRole("navigation", { name: "BeatSaver sections" });
    expect(within(nav).getByRole("link", { name: "Maps" })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("link", { name: "Playlists" })).toHaveAttribute(
      "href",
      "/vr/beatsaver?view=playlists",
    );
    expect(
      within(screen.getByRole("navigation", { name: "Section" })).getByRole("link", {
        name: "Library",
      }),
    ).toHaveAttribute("href", "/vr");
  });

  test("the playlist view lists playlists with an Open link", async () => {
    playlistApi();
    show("/vr/beatsaver?view=playlists");
    expect(await screen.findByRole("heading", { name: "Best of 2024" })).toBeInTheDocument();
    expect(screen.getByText(/Alice/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Best of 2024" })).toHaveAttribute(
      "href",
      "/vr/beatsaver?view=playlists&playlist=p1",
    );
  });

  test("one playlist lists its maps with Download", async () => {
    const { calls } = playlistApi();
    const user = userEvent.setup();
    show("/vr/beatsaver?view=playlists&playlist=p1");
    expect(await screen.findByRole("heading", { name: "Song 5" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Best of 2024", level: 2 })).toBeInTheDocument();
    expect(calls.some((u) => u.pathname === "/api/beatsaver/search")).toBe(false);
    await user.click(screen.getByRole("button", { name: "Download Song 5" }));
    await waitFor(() =>
      expect(calls.some((u) => u.pathname === "/api/beatsaver/download")).toBe(true),
    );
  });
});
