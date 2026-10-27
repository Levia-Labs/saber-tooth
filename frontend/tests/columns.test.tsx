import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import fc from "fast-check";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, test } from "vitest";
import {
  BREAKPOINTS,
  clampWidth,
  DEFAULTS,
  defaultWidths,
  gridTemplate,
  LIMITS,
  loadWidths,
  ROW_CELLS,
  saveWidths,
  stepWidth,
  tableMinWidth,
  TRACKS,
  type ColumnKey,
} from "../src/lib/columns";
import { FACETS, item, mockFetch, renderApp } from "./helpers";

const keys = (root: Element) =>
  [...root.querySelectorAll("[role=cell], [role=columnheader]")].map(
    (el) => /\bcol-(\w+)/.exec(el.className)?.[1],
  );

function memoryStorage(): Storage {
  const data = new Map<string, string>();
  return {
    get length() {
      return data.size;
    },
    clear: () => data.clear(),
    getItem: (k) => data.get(k) ?? null,
    key: (i) => [...data.keys()][i] ?? null,
    removeItem: (k) => void data.delete(k),
    setItem: (k, v) => void data.set(k, v),
  };
}

function throwingStorage(): Storage {
  const boom = () => {
    throw new Error("blocked");
  };
  return { length: 0, clear: boom, getItem: boom, key: boom, removeItem: boom, setItem: boom };
}

const STORE_WIDE = "saber-tooth.columns.v1.wide";

afterEach(() => localStorage.clear());

function withRow() {
  mockFetch((url) =>
    url.pathname === "/api/maps/facets"
      ? FACETS
      : { items: [item(1)], total: 1, offset: 0, limit: 40 },
  );
}

describe("shared column definition", () => {
  test.each(BREAKPOINTS)("%s tracks are a subset of the row cells, in order", (bp) => {
    const cells = ROW_CELLS.filter((c) => TRACKS[bp].includes(c as ColumnKey));
    expect(cells).toEqual(TRACKS[bp]);
    expect(Object.keys(DEFAULTS[bp]).sort()).toEqual([...TRACKS[bp]].sort());
    const count = gridTemplate(bp, defaultWidths(bp))
      .replace(/\([^)]*\)/g, "")
      .split(" ").length;
    expect(count).toBe(TRACKS[bp].length);
  });

  test("header, row and skeleton share the same column keys in the same order", async () => {
    withRow();
    const { container } = renderApp("/");
    const row = await waitFor(() => {
      const r = container.querySelector("[data-map]");
      if (!r) throw new Error("no row");
      return r;
    });
    const head = container.querySelector(".lib-head") as Element;
    expect(keys(row)).toEqual([...ROW_CELLS]);
    expect(keys(head)).toEqual(ROW_CELLS.filter((c) => c !== "sub"));
    expect(screen.getByRole("columnheader", { name: "Image" })).not.toHaveAttribute("aria-sort");
  });

  test("skeleton rows carry the same cells as rows", async () => {
    mockFetch(() => new Promise(() => undefined) as never);
    const { container } = renderApp("/");
    const sk = await waitFor(() => {
      const r = container.querySelector("[data-skeleton]");
      if (!r) throw new Error("no skeleton");
      return r;
    });
    expect(keys(sk)).toEqual([...ROW_CELLS]);
  });
});

describe("width math", () => {
  test("property: clamp stays inside the limits and is idempotent", () => {
    const resizable = Object.keys(LIMITS) as ColumnKey[];
    fc.assert(
      fc.property(fc.constantFrom(...resizable), fc.double(), (key, px) => {
        const w = clampWidth(key, px);
        const l = LIMITS[key] as { min: number; max: number };
        expect(w).toBeGreaterThanOrEqual(l.min);
        expect(w).toBeLessThanOrEqual(l.max);
        expect(clampWidth(key, w)).toBe(w);
      }),
    );
  });

  test("fixed columns are never clamped", () => {
    expect(clampWidth("cover", 999)).toBe(999);
  });

  test("keyboard steps by 16px, 64px with shift, clamped", () => {
    expect(stepWidth("author", 120, "ArrowRight", false)).toBe(136);
    expect(stepWidth("author", 120, "ArrowLeft", false)).toBe(104);
    expect(stepWidth("author", 120, "ArrowRight", true)).toBe(184);
    expect(stepWidth("author", 110, "ArrowLeft", true)).toBe(100);
    expect(stepWidth("author", 390, "ArrowRight", true)).toBe(400);
    expect(stepWidth("author", 120, "a", false)).toBeNull();
  });

  test("grid template and table minimum follow the widths", () => {
    const w = { ...defaultWidths("compact"), title: 200 };
    expect(gridTemplate("compact", w)).toBe("64px minmax(200px, 1fr) 76px 88px 150px 156px");
    expect(tableMinWidth("compact", w)).toBe(64 + 200 + 76 + 88 + 150 + 156 + 5 * 12 + 24);
  });
});

describe("persistence", () => {
  test("round trip and defaults cleanup", () => {
    const s = memoryStorage();
    saveWidths("wide", { ...defaultWidths("wide"), author: 222 }, s);
    expect(loadWidths("wide", s).author).toBe(222);
    expect(loadWidths("mid", s).author).toBe(120);
    saveWidths("wide", defaultWidths("wide"), s);
    expect(s.length).toBe(0);
  });

  test("throwing storage degrades to defaults without throwing", () => {
    const s = throwingStorage();
    expect(() => saveWidths("wide", { author: 200 }, s)).not.toThrow();
    expect(loadWidths("wide", s)).toEqual(defaultWidths("wide"));
    expect(loadWidths("wide", null)).toEqual(defaultWidths("wide"));
  });

  test("corrupt or out-of-range saved values are repaired", () => {
    const s = memoryStorage();
    s.setItem(STORE_WIDE, "{bad");
    expect(loadWidths("wide", s)).toEqual(defaultWidths("wide"));
    s.setItem(STORE_WIDE, JSON.stringify({ author: 5000, bpm: "x", nope: 1 }));
    const w = loadWidths("wide", s);
    expect(w.author).toBe(400);
    expect(w.bpm).toBe(84);
  });
});

describe("header cells", () => {
  test("label, sort slot and filter button share one nowrap row", async () => {
    withRow();
    const { container } = renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    const head = container.querySelector(".lib-head") as HTMLElement;
    for (const col of ["title", "author", "levels", "env", "status"]) {
      const row = head.querySelector(`.col-${col} > .th-row`) as HTMLElement;
      expect(row).not.toBeNull();
      expect(row.querySelector(".th-sort .th-label")).not.toBeNull();
      expect(row.querySelector(".th-sort .th-slot")).not.toBeNull();
      expect(row.querySelector(".filter-btn")).not.toBeNull();
    }
    const css = readFileSync(resolve(__dirname, "../src/styles/library.css"), "utf8");
    expect(css).toMatch(/\.th-row\s*\{[^}]*flex-flow:\s*row nowrap/);
    expect(css).toMatch(/\.th-label\s*\{[^}]*min-width:\s*0[^}]*text-overflow:\s*ellipsis/);
    expect(css).toMatch(/\.filter-btn\s*\{[^}]*flex:\s*none/);
  });

  test("reset is an icon button beside Learn lightshows, not in the table header", async () => {
    withRow();
    const { container } = renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    expect(container.querySelector(".lib-head")?.textContent).not.toContain("Reset");
    const learn = screen.getByRole("button", { name: "Learn lightshows" });
    const reset = screen.getByRole("button", { name: "Reset column widths" });
    expect(learn.nextElementSibling).toBe(reset);
    expect(reset.textContent).toBe("Reset column widths");
    expect(reset.querySelector(".sr")).not.toBeNull();
  });
});

describe("resize handles", () => {
  test("only resizable columns get a labelled separator", async () => {
    withRow();
    renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    const names = screen.getAllByRole("separator").map((s) => s.getAttribute("aria-label"));
    expect(names).toEqual(
      ["Title", "Author", "Levels", "Length", "BPM", "Environment", "Status"].map(
        (n) => `Resize ${n} column`,
      ),
    );
    const author = screen.getByRole("separator", { name: "Resize Author column" });
    expect(author).toHaveAttribute("aria-valuenow", "120");
    expect(author).toHaveAttribute("aria-valuemin", "100");
    expect(author).toHaveAttribute("aria-valuemax", "400");
  });

  test("arrows resize, home and double click reset, widths persist, Reset columns clears", async () => {
    withRow();
    const { container } = renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    const user = userEvent.setup();
    const author = screen.getByRole("separator", { name: "Resize Author column" });
    author.focus();
    await user.keyboard("{ArrowRight}");
    expect(author).toHaveAttribute("aria-valuenow", "136");
    await user.keyboard("{Shift>}{ArrowRight}{/Shift}");
    expect(author).toHaveAttribute("aria-valuenow", "200");
    const table = container.querySelector(".lib-table") as HTMLElement;
    expect(table.style.getPropertyValue("--cols-wide")).toContain("200px");
    const saved = JSON.parse(localStorage.getItem(STORE_WIDE) ?? "{}") as { author?: number };
    expect(saved.author).toBe(200);
    await user.keyboard("{Home}");
    expect(author).toHaveAttribute("aria-valuenow", "120");
    await user.keyboard("{ArrowLeft}");
    expect(author).toHaveAttribute("aria-valuenow", "104");
    fireEvent.doubleClick(author);
    expect(author).toHaveAttribute("aria-valuenow", "120");
    await user.keyboard("{ArrowRight}");
    await user.click(screen.getByRole("button", { name: "Reset column widths" }));
    expect(screen.getByRole("separator", { name: "Resize Author column" })).toHaveAttribute(
      "aria-valuenow",
      "120",
    );
    expect(localStorage.getItem(STORE_WIDE)).toBeNull();
  });
});
