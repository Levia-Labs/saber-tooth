import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import fc from "fast-check";
import * as Tooltip from "@radix-ui/react-tooltip";
import { MemoryRouter, useNavigate } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { PreviewButton } from "../src/components/PreviewButton";
import { bsSiteUrl, DEFAULT_BS_STATE, encodeBsState, parseBsState } from "../src/lib/bsfilters";
import { compareByUpvotes, sortByUpvotes } from "../src/lib/bsrating";
import { formatCount } from "../src/lib/format";
import { stopPreview } from "../src/lib/previewPlayer";
import { bsApi, bsMap, page } from "./bshelpers";
import { renderApp } from "./helpers";

describe("icon-only row actions and icons", () => {
  test("row actions show no visible labels but keep names", async () => {
    bsApi();
    renderApp("/beatsaver");
    await screen.findByText("Song 1");
    const row = document.querySelector('[data-map="k1"]') as HTMLElement;
    expect(row.querySelector(".col-actions .short")).toBeNull();
    expect(within(row).getByRole("button", { name: "Download Song 1" })).toBeInTheDocument();
    expect(within(row).getByRole("link", { name: /Open Song 1 on BeatSaver/ })).toBeInTheDocument();
    expect(row.querySelectorAll(".col-actions svg").length).toBe(2);
  });

  test("text buttons carry an icon and the shared label-hide class", async () => {
    bsApi();
    renderApp("/beatsaver");
    await screen.findByText("Song 1");
    const save = screen.getByRole("button", { name: /Save current filters/ });
    expect(save.querySelector("svg")).not.toBeNull();
    expect(save.querySelector(".label-hide-mobile")).not.toBeNull();
  });

  test("Add tag is an icon button with a tooltip", async () => {
    bsApi();
    renderApp("/beatsaver");
    await screen.findByText("Song 1");
    await userEvent.click(screen.getByRole("button", { name: /Tags/ }));
    const add = await screen.findByRole("button", { name: "Add tag" });
    expect(add.querySelector("svg")).not.toBeNull();
    expect(add.textContent).toBe("");
    await userEvent.hover(add);
    expect((await screen.findAllByText("Add this tag to the filter")).length).toBeGreaterThan(0);
  });
});

describe("BeatSaver website link", () => {
  test("header link opens beatsaver.com in a new tab", async () => {
    bsApi();
    renderApp("/beatsaver");
    await screen.findByText("Song 1");
    const link = screen.getByRole("link", { name: "Open BeatSaver website" });
    expect(link).toHaveAttribute("href", "https://beatsaver.com");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  test("filters map onto the search URL", async () => {
    bsApi();
    renderApp("/beatsaver?q=daft&tags=rock,pop&order=Rating");
    await screen.findByText("Song 1");
    const href = screen.getByRole("link", { name: "Open BeatSaver website" }).getAttribute("href");
    const url = new URL(href as string);
    expect(url.origin + url.pathname).toBe("https://beatsaver.com/search");
    expect(url.searchParams.get("q")).toBe("daft");
    expect(url.searchParams.get("tags")).toBe("rock,pop");
    expect(url.searchParams.get("order")).toBe("Rating");
    expect(bsSiteUrl(DEFAULT_BS_STATE)).toBe("https://beatsaver.com");
  });
});

describe("rating order", () => {
  const m = (id: string, upvotes: number, rating: number) =>
    bsMap(1, { id, song: id, name: id, upvotes, rating });

  test("comparator: upvotes, then rating, then name", () => {
    expect(compareByUpvotes(m("a", 10, 0.5), m("b", 5, 0.9))).toBeLessThan(0);
    expect(compareByUpvotes(m("a", 5, 0.9), m("b", 5, 0.5))).toBeLessThan(0);
    expect(compareByUpvotes(m("a", 5, 0.5), m("b", 5, 0.5))).toBeLessThan(0);
    expect(compareByUpvotes(m("b", 5, 0.5), m("a", 5, 0.5))).toBeGreaterThan(0);
  });

  test("ascending flips upvotes and rating", () => {
    const list = [m("a", 1, 0.5), m("b", 9, 0.5), m("c", 9, 0.9)];
    expect(sortByUpvotes(list, false).map((x) => x.id)).toEqual(["c", "b", "a"]);
    expect(sortByUpvotes(list, true).map((x) => x.id)).toEqual(["a", "b", "c"]);
  });

  test("a later page sorts in without reordering rows already shown", () => {
    fc.assert(
      fc.property(
        fc.array(fc.tuple(fc.integer({ min: 0, max: 50 }), fc.integer({ min: 0, max: 10 })), {
          maxLength: 30,
        }),
        fc.nat(30),
        (raw, cut) => {
          const all = raw.map(([u, r], i) => m(`m${String(i).padStart(2, "0")}`, u, r / 10));
          const first = sortByUpvotes(all.slice(0, cut), false);
          const merged = sortByUpvotes([...first, ...all.slice(cut)], false);
          const pos = first.map((x) => merged.indexOf(x));
          expect([...pos].sort((a, b) => a - b)).toEqual(pos);
          expect(merged).toEqual(sortByUpvotes(all, false));
        },
      ),
    );
  });

  test("formatCount is compact", () => {
    expect(formatCount(950)).toBe("950");
    expect(formatCount(1200)).toBe("1.2k");
    expect(formatCount(15000)).toBe("15k");
    expect(formatCount(1_100_000)).toBe("1.1M");
  });
});

describe("min upvotes filter", () => {
  test("round-trips through the URL state", () => {
    const s = parseBsState("min_upvotes=250");
    expect(s.minUpvotes).toBe(250);
    expect(encodeBsState(s).get("min_upvotes")).toBe("250");
    expect(parseBsState("min_upvotes=-3").minUpvotes).toBeNull();
  });

  test("reaches the API and the Upvotes popover offers the input", async () => {
    const urls: URL[] = [];
    bsApi({
      search: (u) => {
        urls.push(u);
        return page([bsMap(1)]);
      },
    });
    renderApp("/beatsaver?min_upvotes=100");
    await screen.findByText("Song 1");
    expect(urls[0]?.searchParams.get("min_upvotes")).toBe("100");
    await userEvent.click(screen.getByRole("button", { name: /^Filter Upvotes/ }));
    expect(await screen.findByLabelText("Min upvotes")).toHaveValue(100);
  });
});

describe("preview button", () => {
  let started: string[] = [];
  let live = new Set<string>();
  const active = () => [...live];
  beforeEach(() => {
    started = [];
    live = new Set();
    class FakeAudio extends EventTarget {
      src = "";
      paused = true;
      duration = 10;
      currentTime = 0;
      constructor() {
        super();
      }
      play() {
        this.paused = false;
        started.push(this.src);
        live.add(this.src);
        return Promise.resolve();
      }
      pause() {
        this.paused = true;
        live.delete(this.src);
      }
    }
    vi.stubGlobal("Audio", FakeAudio);
  });
  afterEach(() => {
    act(() => stopPreview());
    vi.unstubAllGlobals();
  });

  test("renders nothing without a source", () => {
    const { container } = render(<PreviewButton title="X" />);
    expect(container).toBeEmptyDOMElement();
  });

  test("toggles play and pause with aria-pressed and labels", async () => {
    render(
      <Tooltip.Provider>
        <PreviewButton src="a.mp3" title="Alpha" />
      </Tooltip.Provider>,
    );
    const btn = screen.getByRole("button", { name: "Play preview of Alpha" });
    expect(btn).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(btn);
    const pause = await screen.findByRole("button", { name: "Pause preview" });
    expect(pause).toHaveAttribute("aria-pressed", "true");
    expect(document.querySelector(".preview-ring")).not.toBeNull();
    await userEvent.click(pause);
    expect(screen.getByRole("button", { name: "Play preview of Alpha" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  test("only one preview plays at a time", async () => {
    render(
      <Tooltip.Provider>
        <PreviewButton src="a.mp3" title="Alpha" />
        <PreviewButton src="b.mp3" title="Beta" />
      </Tooltip.Provider>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Play preview of Alpha" }));
    await userEvent.click(screen.getByRole("button", { name: "Play preview of Beta" }));
    expect(screen.getByRole("button", { name: "Play preview of Alpha" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.getByRole("button", { name: "Pause preview" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(started).toEqual(["a.mp3", "b.mp3"]);
    expect(active()).toEqual(["b.mp3"]);
  });

  test("a route change stops the preview", async () => {
    function Go() {
      const nav = useNavigate();
      return <button onClick={() => void nav("/other")}>go</button>;
    }
    render(
      <MemoryRouter>
        <Tooltip.Provider>
          <Go />
          <PreviewButton src="a.mp3" title="Alpha" />
        </Tooltip.Provider>
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Play preview of Alpha" }));
    await screen.findByRole("button", { name: "Pause preview" });
    await userEvent.click(screen.getByRole("button", { name: "go" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Play preview of Alpha" })).toHaveAttribute(
        "aria-pressed",
        "false",
      ),
    );
  });

  test("a map without preview_url shows no preview button in the title cell", async () => {
    bsApi({ search: () => page([bsMap(2)]) });
    renderApp("/beatsaver");
    await screen.findByText("Song 2");
    expect(screen.queryByRole("button", { name: /preview/i })).toBeNull();
  });
});
