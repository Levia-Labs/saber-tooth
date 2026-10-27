import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, onTestFinished, test, vi } from "vitest";
import { mockFetch, renderApp } from "./helpers";

const DIR = resolve(__dirname, "../../.cache/api-snapshots");
const load = (name: string): unknown => JSON.parse(readFileSync(resolve(DIR, name), "utf8"));
const IDS = ["5c4d3bdd9d58", "65a4b5707116", "b8c1c0d00ecc"];

function api() {
  return mockFetch((url) => {
    const p = url.pathname;
    if (p === "/api/maps") {
      const page = load("maps.json") as { items: unknown[] };
      const off = Number(url.searchParams.get("offset") ?? 0);
      return { ...page, items: off > 0 ? [] : page.items };
    }
    if (p === "/api/maps/facets") return load("facets.json");
    if (p === "/api/lightshow") return load("lightshow.json");
    const m = /^\/api\/maps\/(\w+)(\/proposals)?$/.exec(p);
    if (m) return load(`${m[2] ? "proposals" : "map"}-${m[1]}.json`);
    return {};
  });
}

// The snapshots live in the untracked .cache folder; the suite is skipped when they are absent.
describe.skipIf(!existsSync(resolve(DIR, "maps.json")))(
  "real API snapshots render without throwing",
  () => {
    test("library", async () => {
      api();
      const err = vi.spyOn(console, "error").mockImplementation(() => undefined);
      renderApp("/");
      await screen.findByText("DLZ");
      expect(screen.queryByText(/Unexpected Application Error/)).toBeNull();
      err.mockRestore();
    });

    test.each(IDS)("map %s", async (id) => {
      api();
      renderApp(`/maps/${id}`);
      await waitFor(() => expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument());
      await new Promise((r) => setTimeout(r, 50));
      expect(screen.queryByText(/Unexpected Application Error/)).toBeNull();
      expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
    });

    test("map with every fix expanded and the canvas drawn", async () => {
      api();
      const store: Record<string | symbol, unknown> = {};
      const ctx = new Proxy(store, {
        get: (t, k) => (k in t ? t[k] : () => ({ width: 10 })),
        set: (t, k, v) => ((t[k] = v), true),
      });
      const original = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = (() => ctx) as never;
      onTestFinished(() => {
        HTMLCanvasElement.prototype.getContext = original;
      });
      renderApp(`/maps/${IDS[0]}`);
      const btn = await screen.findByRole("button", { name: /Expand all/ });
      await waitFor(() => expect(btn).toBeEnabled());
      fireEvent.click(btn);
      await new Promise((r) => setTimeout(r, 100));
      expect(screen.queryByText(/Unexpected Application Error/)).toBeNull();
      expect(screen.getAllByRole("img").length).toBeGreaterThan(100);
    }, 120_000);

    test.each([true, false])("library narrow=%s, every button pressed", async (narrow) => {
      api();
      const orig = window.matchMedia;
      window.matchMedia = ((q: string) => ({ ...orig(q), matches: narrow })) as never;
      try {
        renderApp("/?status=error,unreadable&level=Easy");
        await screen.findByText("DLZ");
        for (const b of screen.getAllByRole("button")) {
          fireEvent.click(b);
          fireEvent.keyDown(document.body, { key: "Escape" });
        }
        await new Promise((r) => setTimeout(r, 50));
        expect(screen.queryByText(/Unexpected Application Error/)).toBeNull();
      } finally {
        window.matchMedia = orig;
      }
    });

    test("every library row of the snapshot renders", async () => {
      const all = (load("maps.json") as { items: { id: string }[] }).items;
      const seen = new Set<string>();
      for (let i = 0; i < all.length; i += 8) {
        mockFetch((url) => {
          if (url.pathname === "/api/maps") {
            const items = url.searchParams.get("offset") === "0" ? all.slice(i, i + 8) : [];
            return { items, total: items.length, offset: 0, limit: 8 };
          }
          return url.pathname === "/api/maps/facets" ? load("facets.json") : {};
        });
        const { unmount } = renderApp("/");
        await waitFor(() =>
          expect(document.querySelectorAll("[data-map]").length).toBe(Math.min(8, all.length - i)),
        );
        document
          .querySelectorAll("[data-map]")
          .forEach((n) => seen.add(n.getAttribute("data-map") ?? ""));
        unmount();
      }
      expect(seen.size).toBe(all.length);
    }, 60_000);

    test("new", async () => {
      api();
      renderApp("/new");
      await screen.findByRole("heading", { level: 1 });
      expect(screen.queryByText(/Unexpected Application Error/)).toBeNull();
    });
  },
);
