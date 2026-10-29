import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import fc from "fast-check";
import { describe, expect, test } from "vitest";
import { bsApiParams, DEFAULT_BS_STATE, encodeBsState, parseBsState } from "../src/lib/bsfilters";
import { BS_COLUMNS } from "../src/lib/bscolumns";
import {
  availableWidth,
  defaultWidths,
  loadWidths,
  tableMinWidth,
  titleWidthAt,
} from "../src/lib/columns";
import { durationInput, inverted, parseBounded, parseDuration } from "../src/lib/range";
import { apiParams, DEFAULT_STATE, parseState } from "../src/lib/urlstate";
import { bsApi, bsMap, page } from "./bshelpers";
import { FACETS, item, mockFetch, renderApp } from "./helpers";

describe("range parsing", () => {
  test("durations accept m:ss and plain seconds", () => {
    expect(parseDuration("2:05")).toBe(125);
    expect(parseDuration("90")).toBe(90);
    expect(parseDuration("")).toBeNull();
    expect(parseDuration("1:75")).toBeUndefined();
    expect(parseDuration("abc")).toBeUndefined();
    expect(parseDuration("-5")).toBeUndefined();
  });

  test("property: durationInput round-trips through parseDuration", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 7200 }), (s) => {
        expect(parseDuration(durationInput(s))).toBe(s);
      }),
    );
  });

  test("property: parseBounded never returns a value outside the bounds", () => {
    fc.assert(
      fc.property(fc.string({ maxLength: 12 }), (text) => {
        const v = parseBounded(text, 0, 1000);
        expect(v === undefined || v === null || (v >= 0 && v <= 1000)).toBe(true);
      }),
    );
  });

  test("inverted pairs", () => {
    expect(inverted(5, 3)).toBe(true);
    expect(inverted(3, 5)).toBe(false);
    expect(inverted(null, 3)).toBe(false);
  });
});

describe("library range state", () => {
  test("bounds round trip through the URL and reach the API", () => {
    const s = parseState("duration_min=60&duration_max=180&bpm_min=120&bpm_max=200");
    expect([s.durationMin, s.durationMax, s.bpmMin, s.bpmMax]).toEqual([60, 180, 120, 200]);
    const p = apiParams(s, 0, 40);
    expect(p.get("duration_min")).toBe("60");
    expect(p.get("bpm_max")).toBe("200");
  });

  test("out-of-range and junk bounds are dropped", () => {
    const s = parseState("duration_min=-1&duration_max=99999&bpm_min=x&bpm_max=1001");
    expect([s.durationMin, s.durationMax, s.bpmMin, s.bpmMax]).toEqual([null, null, null, null]);
  });

  test("an inverted pair is not sent to the API", () => {
    const p = apiParams({ ...DEFAULT_STATE, bpmMin: 200, bpmMax: 100, durationMin: 30 }, 0, 40);
    expect(p.has("bpm_min") || p.has("bpm_max")).toBe(false);
    expect(p.get("duration_min")).toBe("30");
  });
});

describe("BeatSaver range state", () => {
  test("the local sort stays in the URL but never reaches the API", () => {
    const s = parseBsState("lsort=bpm&order=Duration&duration_min=60");
    expect(s.localSort).toBe("bpm");
    expect(encodeBsState(s).get("lsort")).toBe("bpm");
    const p = bsApiParams(s, null, 40);
    expect(p.has("lsort")).toBe(false);
    expect(p.get("order")).toBe("Duration");
    expect(parseBsState("lsort=nope").localSort).toBeNull();
  });

  test("an inverted pair is dropped from the API call", () => {
    const p = bsApiParams({ ...DEFAULT_BS_STATE, bpmMin: 200, bpmMax: 100 }, null, 40);
    expect(p.has("bpm_min") || p.has("bpm_max")).toBe(false);
  });
});

describe("fit", () => {
  test.each([
    [1280, "wide"],
    [1440, "wide"],
    [1920, "wide"],
    [1100, "mid"],
    [720, "compact"],
  ] as const)("BeatSaver defaults fit at %ipx with no scroll", (w, bp) => {
    const widths = defaultWidths(bp, BS_COLUMNS);
    expect(tableMinWidth(bp, widths, BS_COLUMNS)).toBeLessThanOrEqual(availableWidth(w));
    expect(titleWidthAt(bp, widths, w, BS_COLUMNS)).toBeGreaterThanOrEqual(widths.title ?? 0);
  });

  test("the BeatSaver tracks list the split columns", () => {
    expect(BS_COLUMNS.tracks.wide).toEqual([
      "select",
      "cover",
      "title",
      "author",
      "levels",
      "rating",
      "upvotes",
      "length",
      "bpm",
      "tags",
      "status",
      "actions",
    ]);
    expect(Object.keys(defaultWidths("wide", BS_COLUMNS)).sort()).toEqual(
      [...BS_COLUMNS.tracks.wide].sort(),
    );
  });

  test("widths saved under the old BeatSaver key are discarded", () => {
    localStorage.setItem("saber-tooth.columns.bs.v1.wide", JSON.stringify({ rating: 150 }));
    expect(loadWidths("wide", localStorage, BS_COLUMNS).rating).toBe(98);
    expect(localStorage.getItem("saber-tooth.columns.bs.v1.wide")).toBeNull();
  });
});

describe("BeatSaver columns", () => {
  test("rating, upvotes, length and BPM are separate cells with their own headers", async () => {
    bsApi({
      search: () => page([bsMap(1, { rating: 0.93, upvotes: 1234, duration: 125, bpm: 140 })]),
    });
    renderApp("/beatsaver");
    await screen.findByText("Song 1");
    const row = document.querySelector('[data-map="k1"]') as HTMLElement;
    const text = (c: string) => row.querySelector(`.col-${c}`)?.textContent;
    expect(text("rating")).toBe("93%");
    expect(text("upvotes")).toBe("1.2k");
    expect(text("length")).toBe("2:05");
    expect(text("bpm")).toBe("140 BPM");
    for (const name of ["Rating", "Upvotes", "Length", "BPM"]) {
      expect(screen.getByRole("button", { name: `Sort by ${name}` })).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: new RegExp(`^Filter ${name}`) }),
      ).toBeInTheDocument();
    }
    expect(document.querySelector(".th.col-tempo")).toBeNull();
  });

  test("Length sorts by the server Duration order", async () => {
    bsApi();
    const { router } = renderApp("/beatsaver");
    await screen.findByText("Song 1");
    await userEvent.click(screen.getByRole("button", { name: "Sort by Length" }));
    await waitFor(() => expect(router.state.location.search).toContain("order=Duration"));
  });

  test("the Length popover takes m:ss and sends duration seconds; BPM sends bpm bounds", async () => {
    const urls: URL[] = [];
    bsApi({
      search: (u) => {
        urls.push(u);
        return page([bsMap(1)]);
      },
    });
    const { router } = renderApp("/beatsaver");
    await screen.findByText("Song 1");
    await userEvent.click(screen.getByRole("button", { name: /^Filter Length/ }));
    await userEvent.type(await screen.findByLabelText("Minimum length"), "1:30");
    await userEvent.type(screen.getByLabelText("Maximum length"), "3:00");
    await waitFor(() => expect(router.state.location.search).toContain("duration_max=180"));
    expect(router.state.location.search).toContain("duration_min=90");
    await waitFor(() => expect(urls.at(-1)?.searchParams.get("duration_min")).toBe("90"));
    expect(urls.at(-1)?.searchParams.get("duration_max")).toBe("180");
    await userEvent.keyboard("{Escape}");
    await userEvent.click(screen.getByRole("button", { name: /^Filter BPM/ }));
    await userEvent.type(await screen.findByLabelText("BPM, at least"), "120");
    await waitFor(() => expect(urls.at(-1)?.searchParams.get("bpm_min")).toBe("120"));
  });

  test("status chips show icons only, with words in the label", async () => {
    bsApi({ search: () => page([bsMap(1, { installed: true, library_id: "abc" })]) });
    renderApp("/beatsaver");
    await screen.findByText("Song 1");
    const chip = document.querySelector('[data-map="k1"] .chip') as HTMLElement;
    expect(chip.textContent).toBe("");
    expect(chip.getAttribute("aria-label")).toMatch(/^Installed\./);
  });
});

describe("Library range filters", () => {
  const api = () =>
    mockFetch((url) => {
      if (url.pathname === "/api/maps/facets") {
        return { ...FACETS, duration: { min: 61, max: 300 }, bpm: { min: 90, max: 220 } };
      }
      return { items: [item(1)], total: 1, offset: 0, limit: 40 };
    });

  test("Length and BPM headers sort and filter; bounds reach the API", async () => {
    const { calls } = api();
    const { router } = renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    expect(screen.getByRole("button", { name: "Sort by Length" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /^Filter Length/ }));
    const min = await screen.findByLabelText("Minimum length");
    expect(min).toHaveAttribute("placeholder", "01:01");
    await userEvent.type(min, "2:00");
    await waitFor(() => expect(router.state.location.search).toContain("duration_min=120"));
    await waitFor(() =>
      expect(
        calls.some(
          (u) => u.pathname === "/api/maps" && u.searchParams.get("duration_min") === "120",
        ),
      ).toBe(true),
    );
    await userEvent.click(screen.getByRole("button", { name: "Clear Length filter" }));
    await waitFor(() => expect(router.state.location.search).not.toContain("duration_min"));
  });

  test("the BPM popover shows the facet bounds and rejects junk", async () => {
    api();
    const { router } = renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    await userEvent.click(screen.getByRole("button", { name: /^Filter BPM/ }));
    const max = await screen.findByLabelText("BPM, at most");
    expect(max).toHaveAttribute("placeholder", "220");
    await userEvent.type(max, "9x.9");
    expect(max).toHaveValue("99");
    await userEvent.clear(max);
    await userEvent.type(max, "180");
    await waitFor(() => expect(router.state.location.search).toContain("bpm_max=180"));
  });

  test("the mobile filter sheet has Length and BPM groups", async () => {
    window.matchMedia = ((query: string) => ({
      matches: query === "(max-width: 1099px)" || query === "(max-width: 719px)",
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      onchange: null,
      dispatchEvent: () => false,
    })) as unknown as typeof window.matchMedia;
    api();
    renderApp("/?bpm_min=100&bpm_max=140");
    await screen.findByRole("link", { name: "Song 1" });
    await userEvent.click(screen.getByRole("button", { name: /^Filters/ }));
    const sheet = await screen.findByRole("dialog", { name: "Filters" });
    const titles = [...sheet.querySelectorAll(".acc-title")].map((t) => t.textContent);
    expect(titles).toContain("Length");
    expect(titles).toContain("BPM");
    const bpm = [...sheet.querySelectorAll(".acc-head")].find((h) =>
      h.textContent?.startsWith("BPM"),
    );
    expect(bpm?.textContent).toContain("100-140");
  });
});
