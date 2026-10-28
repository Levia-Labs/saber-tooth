import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import fc from "fast-check";
import { describe, expect, test } from "vitest";
import {
  DEFAULT_BS_STATE,
  encodeBsState,
  parseBsState,
  presetFilters,
  stateFromPreset,
} from "../src/lib/bsfilters";
import { bsApi, bsMap, page, SEEDED } from "./bshelpers";
import { renderApp } from "./helpers";

describe("filter state", () => {
  test("a state survives the URL round trip", () => {
    fc.assert(
      fc.property(
        fc.record({
          q: fc.string({ maxLength: 40 }).map((s) => s.trim()),
          minRating: fc.option(
            fc.integer({ min: 0, max: 100 }).map((n) => n / 100),
            { nil: null },
          ),
          npsMin: fc.option(fc.integer({ min: 0, max: 30 }), { nil: null }),
          ranked: fc.boolean(),
          ascending: fc.boolean(),
          diffsMode: fc.constantFrom("any" as const, "all" as const),
          diffs: fc.subarray(["Easy", "Normal", "Hard", "Expert", "ExpertPlus"] as const),
        }),
        (patch) => {
          const state = { ...DEFAULT_BS_STATE, ...patch, diffs: [...patch.diffs] };
          const again = parseBsState(encodeBsState(state).toString());
          expect(again.q).toBe(state.q);
          expect(again.minRating).toBe(state.minRating);
          expect(again.npsMin).toBe(state.npsMin);
          expect(again.ranked).toBe(state.ranked);
          expect(again.ascending).toBe(state.ascending);
          expect(again.diffs).toEqual(state.diffs);
          if (state.diffs.length) expect(again.diffsMode).toBe(state.diffsMode);
        },
      ),
    );
  });

  test("out of range and unknown values fall back to the defaults", () => {
    const s = parseBsState("min_rating=7&nps_max=-1&order=Bogus&diffs=Easy,Nope&from=x");
    expect(s.minRating).toBeNull();
    expect(s.npsMax).toBeNull();
    expect(s.order).toBe("Latest");
    expect(s.diffs).toEqual(["Easy"]);
    expect(s.from).toBe("");
  });

  test("a preset converts to a state and back", () => {
    const state = stateFromPreset(SEEDED.filters);
    expect(state.diffs).toEqual(["Easy", "Normal", "Hard"]);
    expect(state.minRating).toBe(0.95);
    expect(presetFilters(state)).toEqual({
      ...SEEDED.filters,
      order: "Rating",
    });
  });
});

describe("BeatSaver view", () => {
  test("lists maps with chips, rating, tags and tooltip-labelled actions", async () => {
    bsApi();
    renderApp("/beatsaver");
    await screen.findByText("Song 1");
    const row = document.querySelector('[data-map="k1"]') as HTMLElement;
    expect(within(row).getByText("96%")).toBeInTheDocument();
    expect(within(row).getAllByRole("img", { name: /Easy, 1.2 NPS/ }).length).toBeGreaterThan(0);
    expect(within(row).getByText("+1")).toBeInTheDocument();
    const open = within(row).getByRole("link", { name: /Open Song 1 on BeatSaver/ });
    expect(open).toHaveAttribute("href", "https://beatsaver.com/maps/k1");
    expect(open).toHaveAttribute("target", "_blank");
    expect(open).toHaveAttribute("rel", "noopener noreferrer");
    await userEvent.hover(within(row).getByRole("button", { name: "Download Song 1" }));
    expect(
      (await screen.findAllByText(/Download this map into your CustomLevels folder/)).length,
    ).toBeGreaterThan(0);
  });

  test("the section tabs link Library and BeatSaver and mark the route", async () => {
    bsApi();
    renderApp("/beatsaver");
    await screen.findByText("Song 1");
    const nav = within(screen.getByRole("navigation", { name: "Section" }));
    expect(nav.getByRole("link", { name: "BeatSaver" })).toHaveAttribute("aria-current", "page");
    expect(nav.getByRole("link", { name: "Library" })).toHaveAttribute("href", "/");
    expect(nav.getByRole("link", { name: "Library" })).not.toHaveAttribute("aria-current");
  });

  test("URL filters reach the API and a header filter writes the URL", async () => {
    const { calls } = bsApi();
    const { router } = renderApp("/beatsaver?min_rating=0.9&tags=rock&diffs=Easy,Hard");
    await screen.findByText("Song 1");
    const q = calls.find((u) => u.pathname === "/api/beatsaver/search")!.searchParams;
    expect(q.get("min_rating")).toBe("0.9");
    expect(q.get("tags")).toBe("rock");
    expect(q.get("diffs")).toBe("Easy,Hard");
    await userEvent.click(screen.getByRole("button", { name: /Filter Rating, 1 active/ }));
    const input = await screen.findByLabelText("Minimum rating (%)");
    await userEvent.clear(input);
    await userEvent.type(input, "97");
    await waitFor(() => expect(router.state.location.search).toContain("min_rating=0.97"));
  });

  test("applying the seeded preset sets every filter in the URL", async () => {
    const { calls } = bsApi();
    const { router } = renderApp("/beatsaver");
    await screen.findByText("Song 1");
    const chip = await screen.findByRole("button", { name: "Easy-to-Hard gems" });
    await userEvent.click(chip);
    await waitFor(() => expect(chip).toHaveAttribute("aria-pressed", "true"));
    const search = new URLSearchParams(router.state.location.search);
    expect(search.get("diffs")).toBe("Easy,Normal,Hard");
    expect(search.get("order")).toBe("Rating");
    await waitFor(() =>
      expect(
        calls.some(
          (u) =>
            u.pathname === "/api/beatsaver/search" && u.searchParams.get("min_rating") === "0.95",
        ),
      ).toBe(true),
    );
  });

  test("seeded preset is listed before saved ones and saving posts the filters", async () => {
    const api = bsApi({
      presets: [{ id: 5, name: "Mine", filters: { ranked: "true" } }, SEEDED],
    });
    renderApp("/beatsaver?ranked=true");
    await screen.findByText("Song 1");
    const group = await screen.findByRole("group", { name: "Saved filters" });
    const names = within(group)
      .getAllByRole("button", { pressed: undefined })
      .map((b) => b.textContent);
    expect(names.indexOf("Easy-to-Hard gems")).toBeLessThan(names.indexOf("Mine"));
    await userEvent.click(screen.getByRole("button", { name: "Save filters" }));
    await userEvent.type(await screen.findByLabelText("Name"), "Ranked only");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(api.posts).toContainEqual({
        path: "/api/beatsaver/presets",
        body: { name: "Ranked only", filters: { ranked: "true" } },
      }),
    );
  });

  test("selecting maps counts them and the confirmation separates new from installed", async () => {
    const api = bsApi({
      search: () => page([bsMap(1), bsMap(2, { installed: true }), bsMap(3)]),
      job: () => ({
        id: "j1",
        kind: "download",
        status: "done",
        error: null,
        result: {
          results: [
            { id: "k1", status: "installed", folder: "k1 (Song 1 - M)" },
            { id: "k3", status: "failed", reason: "Needs Noodle" },
          ],
        },
      }),
    });
    renderApp("/beatsaver");
    await screen.findByText("Song 3");
    for (const n of [1, 2, 3])
      await userEvent.click(screen.getByRole("checkbox", { name: `Select Song ${n}` }));
    expect(screen.getByText("3 selected")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Download 3" }));
    const dialog = await screen.findByRole("dialog", { name: "Download maps" });
    expect(within(dialog).getByText(/2 new maps will be downloaded/)).toBeInTheDocument();
    expect(within(dialog).getByText(/1 map already installed will be skipped/)).toBeInTheDocument();
    expect(within(dialog).getByText("Already installed (1)")).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Download 2 new" }));
    await waitFor(() =>
      expect(api.posts).toContainEqual({
        path: "/api/beatsaver/download",
        body: { ids: ["k1", "k3"] },
      }),
    );
    expect(await screen.findByText(/Installed 1, skipped 0, failed 1\./)).toBeInTheDocument();
    expect(screen.getByText(/k3: Needs Noodle/)).toBeInTheDocument();
    expect(screen.queryByText("3 selected")).toBeNull();
  });

  test("a single download shows the row as downloading while the job runs", async () => {
    bsApi();
    renderApp("/beatsaver");
    await screen.findByText("Song 1");
    await userEvent.click(screen.getByRole("button", { name: "Download Song 1" }));
    const row = document.querySelector('[data-map="k1"]') as HTMLElement;
    await waitFor(() =>
      expect(within(row).getByRole("img", { name: /^Downloading\./ })).toBeInTheDocument(),
    );
    expect(within(row).queryByText("Downloading")).toBeNull();
    expect(document.querySelector(".toast-stack .alert-spin")).not.toBeNull();
    expect(within(row).getByRole("button", { name: "Download Song 1" })).toBeDisabled();
  });

  test("an installed map shows Installed and cannot be downloaded again", async () => {
    bsApi({ search: () => page([bsMap(1, { installed: true, library_id: "abc" })]) });
    renderApp("/beatsaver");
    await screen.findByText("Song 1");
    const row = document.querySelector('[data-map="k1"]') as HTMLElement;
    const chip = within(row).getByRole("img", { name: /^Installed\./ });
    expect(chip.textContent).toBe("");
    expect(within(row).queryByText("Installed")).toBeNull();
    expect(within(row).getByRole("button", { name: "Download Song 1" })).toBeDisabled();
  });

  test("Export playlist appears only when the server enables playlists", async () => {
    bsApi({ playlistsEnabled: true });
    renderApp("/beatsaver");
    await screen.findByText("Song 1");
    await userEvent.click(screen.getByRole("checkbox", { name: "Select Song 1" }));
    expect(await screen.findByRole("button", { name: /Export playlist/ })).toBeInTheDocument();
  });

  test("no Export playlist button when playlists are disabled", async () => {
    bsApi({ playlistsEnabled: false });
    renderApp("/beatsaver");
    await screen.findByText("Song 1");
    await userEvent.click(screen.getByRole("checkbox", { name: "Select Song 1" }));
    expect(screen.queryByRole("button", { name: /Export playlist/ })).toBeNull();
  });

  test("the footer reports how far the scan looked", async () => {
    bsApi({ search: () => page([bsMap(1)], { scanned: 300, matched: 1 }) });
    renderApp("/beatsaver");
    expect(await screen.findByText("Scanned 300 BeatSaver maps, 1 match")).toBeInTheDocument();
  });

  test("a rate limited page keeps its maps, shows a banner and retry loads more", async () => {
    let calls = 0;
    const { calls: urls } = bsApi({
      search: (url) => {
        calls += 1;
        if (calls === 1) {
          return page([bsMap(1)], { cursor: "5:0", partial: true, retry_after: 7 });
        }
        expect(url.searchParams.get("cursor")).toBe("5:0");
        return page([bsMap(2)]);
      },
    });
    renderApp("/beatsaver");
    await screen.findByText("Song 1");
    const banner = await screen.findByRole("alert");
    expect(banner).toHaveTextContent("partial");
    expect(banner).toHaveTextContent("7 seconds");
    expect(urls.filter((u) => u.pathname === "/api/beatsaver/search")).toHaveLength(1);
    await userEvent.click(within(banner).getByRole("button", { name: "Retry" }));
    await screen.findByText("Song 2");
    expect(screen.getByText("Song 1")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  test("an unreachable BeatSaver shows the error and a retry", async () => {
    bsApi({
      search: () => new Response(JSON.stringify({ detail: "down" }), { status: 400 }) as never,
    });
    renderApp("/beatsaver");
    expect(await screen.findByText(/Could not reach BeatSaver: down/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
