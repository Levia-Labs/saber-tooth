import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, test } from "vitest";
import {
  availableWidth,
  defaultWidths,
  loadWidths,
  tableMinWidth,
  titleWidthAt,
  TRACKS,
  type Breakpoint,
} from "../src/lib/columns";
import { ICON_NAMES } from "../src/components/icons";
import { TIPS } from "../src/lib/tips";
import { FACETS, item, mockFetch, renderApp } from "./helpers";

const real = window.matchMedia;
afterEach(() => {
  window.matchMedia = real;
  localStorage.clear();
});

/** Make `(max-width: Npx)` queries match as they would at this viewport width. */
function viewport(width: number) {
  window.matchMedia = ((query: string) => {
    const max = /\(max-width:\s*(\d+)px\)/.exec(query);
    return { ...real(query), media: query, matches: max ? width <= Number(max[1]) : false };
  }) as typeof window.matchMedia;
}

function css(name: string) {
  return readFileSync(resolve(__dirname, "../src/styles", name), "utf8");
}

function library(extra: Parameters<typeof item>[1] = {}) {
  mockFetch((url) =>
    url.pathname === "/api/maps/facets"
      ? FACETS
      : { items: [item(1, extra)], total: 1, offset: 0, limit: 40 },
  );
}

describe("header actions on narrow screens", () => {
  test.each([1099, 900, 720, 600, 500])(
    "%ipx keeps all three as labelled icon buttons",
    async (w) => {
      viewport(w);
      library();
      renderApp("/");
      await screen.findByRole("link", { name: "Song 1" });
      const generate = screen.getByRole("link", { name: "Generate map" });
      const learn = screen.getByRole("button", { name: "Learn lightshows" });
      const reset = screen.getByRole("button", { name: "Reset column widths" });
      for (const el of [generate, learn, reset]) {
        expect(el.querySelector(".sr")).not.toBeNull();
        expect(el.querySelector("svg")).not.toBeNull();
      }
      expect(css("library.css")).toMatch(/\.lib-tools \.btn\.tap\s*\{[^}]*width:\s*44px/);
    },
  );

  test("icon buttons carry the same Tips", async () => {
    viewport(900);
    library();
    renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    await userEvent.hover(screen.getByRole("button", { name: "Learn lightshows" }));
    expect((await screen.findAllByText(TIPS.learn)).length).toBeGreaterThan(0);
  });

  test("bars never wrap below 1100px", () => {
    expect(css("rows.css")).toMatch(
      /@media \(max-width: 1099px\)\s*\{\s*\.lib-bar\s*\{\s*flex-wrap:\s*nowrap/,
    );
  });

  test("below 480px Generate stays and the rest move into a kebab with the same Tips", async () => {
    viewport(400);
    library();
    renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    expect(screen.getByRole("link", { name: "Generate map" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Learn lightshows" })).toBeNull();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "More actions" }));
    const learn = await screen.findByRole("button", { name: "Learn lightshows" });
    expect(screen.getByRole("button", { name: "Reset column widths" })).toBeInTheDocument();
    await user.hover(learn);
    expect((await screen.findAllByText(TIPS.learn)).length).toBeGreaterThan(0);
  });

  test("wide layout keeps text buttons and no kebab", async () => {
    viewport(1400);
    library();
    renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    expect(screen.getByRole("button", { name: "Learn lightshows" }).textContent).toBe(
      "Learn lightshows",
    );
    expect(screen.queryByRole("button", { name: "More actions" })).toBeNull();
  });
});

describe("table control bar", () => {
  test.each([1099, 800, 500])("%ipx shows the bar directly above the list", async (w) => {
    viewport(w);
    library();
    const { container } = renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    const bar = container.querySelector(".lib-mobile-bar") as HTMLElement;
    expect(bar.nextElementSibling?.className).toBe("lib-scroll");
    const sort = within(bar).getByRole("combobox", { name: "Sort by" });
    expect([...sort.querySelectorAll("option")].map((o) => o.textContent)).toEqual([
      "Title",
      "Author",
      "Levels",
      "Env",
      "Status",
      "Length",
      "BPM",
    ]);
    expect(within(bar).getByRole("button", { name: "Ascending" })).toBeInTheDocument();
    expect(within(bar).queryByRole("button", { name: "Clear filters" })).toBeNull();
  });

  test("1100px and wider has no bar", async () => {
    viewport(1100);
    library();
    const { container } = renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    expect(container.querySelector(".lib-mobile-bar")).toBeNull();
  });

  test("Filters shows the active count and clear filters resets them", async () => {
    viewport(800);
    library();
    const { router, container } = renderApp("/?status=error&env=Origins&q=moon");
    await screen.findByRole("link", { name: "Song 1" });
    const bar = container.querySelector(".lib-mobile-bar") as HTMLElement;
    const filters = within(bar).getByRole("button", { name: /Filters/ });
    expect(filters.querySelector(".filter-badge")?.textContent).toBe("3");
    const user = userEvent.setup();
    await user.click(filters);
    const sheet = await screen.findByRole("dialog", { name: "Filters" });
    expect([...sheet.querySelectorAll(".acc-title")].map((h) => h.textContent)).toEqual([
      "Title",
      "Author",
      "Levels",
      "Length",
      "BPM",
      "Env",
      "Status",
    ]);
    await user.keyboard("{Escape}");
    await user.click(within(bar).getByRole("button", { name: "Clear filters" }));
    await waitFor(() => expect(router.state.location.search).toBe(""));
    expect(within(bar).queryByRole("button", { name: "Clear filters" })).toBeNull();
  });

  test("controls are at least 44px tall", () => {
    const sheet = css("library.css");
    for (const sel of [".filters-btn", ".tap", ".sort-select select", ".order-toggle"]) {
      expect(sheet).toContain(`.lib-mobile-bar ${sel}`);
    }
    expect(sheet).toMatch(/\.lib-mobile-bar \.filters-btn[^{]*\{[^}]*min-height:\s*44px/);
  });
});

describe("fitting columns", () => {
  const BPS: [number, Breakpoint][] = [
    [1280, "wide"],
    [1440, "wide"],
    [1920, "wide"],
  ];

  test.each(BPS)("%ipx: defaults fit with no scroll and Title absorbs the rest", (w, bp) => {
    const widths = defaultWidths(bp);
    expect(tableMinWidth(bp, widths)).toBeLessThanOrEqual(availableWidth(w));
    const title = titleWidthAt(bp, widths, w);
    const fixed = tableMinWidth(bp, widths) - (widths.title ?? 0);
    expect(fixed + title).toBe(availableWidth(w));
    expect(title).toBeGreaterThanOrEqual(widths.title ?? 0);
    expect(title).toBeLessThanOrEqual(520);
  });

  test("mid and compact defaults also fit at their narrowest viewports", () => {
    expect(tableMinWidth("mid", defaultWidths("mid"))).toBeLessThanOrEqual(availableWidth(1100));
    expect(tableMinWidth("compact", defaultWidths("compact"))).toBeLessThanOrEqual(
      availableWidth(720),
    );
  });

  test("the page is capped at 1480px so 1920 matches the cap", () => {
    expect(availableWidth(1920)).toBe(availableWidth(1480));
  });

  test("every breakpoint lists the same keys as its defaults", () => {
    for (const bp of ["wide", "mid", "compact"] as const) {
      expect(Object.keys(defaultWidths(bp)).sort()).toEqual([...TRACKS[bp]].sort());
    }
  });

  test("widths saved under the old key are discarded once", () => {
    localStorage.setItem("saber-tooth.columns.v1.wide", JSON.stringify({ author: 300 }));
    expect(loadWidths("wide").author).toBe(defaultWidths("wide").author);
    expect(localStorage.getItem("saber-tooth.columns.v1.wide")).toBeNull();
  });

  test("Env column header and filter use the short label", async () => {
    viewport(1400);
    library();
    renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    expect(screen.getByRole("columnheader", { name: /Env/ })).toBeInTheDocument();
    expect(screen.queryByText("Environment")).toBeNull();
    expect(screen.getByRole("button", { name: "Filter Env" })).toBeInTheDocument();
  });
});

describe("icons and chips", () => {
  test("columns-reset is replaced by a standard reset icon; clock exists", () => {
    expect(ICON_NAMES).not.toContain("columns-reset");
    expect(ICON_NAMES).toEqual(expect.arrayContaining(["reset", "clock"]));
  });

  test("unscanned status chip shows no text but keeps label and min width", async () => {
    viewport(1400);
    library({ status: "unscanned" });
    const { container } = renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    const chip = screen.getByRole("img", { name: "Not scanned" });
    expect(chip.textContent).toBe("");
    expect(container.textContent).not.toContain("--");
    expect(css("chips.css")).toMatch(/\.chip\s*\{[^}]*min-width:\s*3\.6rem/);
  });

  test("level text is borderless with muted separators and missing levels", () => {
    const text = css("chips.css");
    expect(text).toMatch(/\.level\s*\{[^}]*border:\s*0/);
    expect(text).toMatch(/\.level\.missing\s*\{[^}]*color:\s*var\(--muted\)/);
    expect(text).toMatch(/\.level-sep\s*\{[^}]*color:\s*var\(--muted\)/);
  });
});
