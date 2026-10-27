import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { bsApi, bsMap, page } from "./bshelpers";
import { renderApp } from "./helpers";

describe("BeatSaver client-side sorts", () => {
  const m = (id: string, upvotes: number, rating: number) =>
    bsMap(1, { id, song: id, name: id, upvotes, rating });

  const order = () =>
    [...document.querySelectorAll("[data-map]")].map((r) => r.getAttribute("data-map"));
  const maps = () => [m("k1", 5, 0.7), m("k2", 500, 0.8), m("k3", 1200, 0.99)];

  test("the Rating column sorts loaded maps by percentage and has a tip", async () => {
    bsApi({ search: () => page(maps()) });
    renderApp("/beatsaver?order=Rating");
    await screen.findByText("k1");
    expect(order()).toEqual(["k3", "k2", "k1"]);
    const row = document.querySelector('[data-map="k3"]') as HTMLElement;
    expect(within(row).getByText("99%")).toBeInTheDocument();
    expect(row.querySelector(".col-upvotes")?.textContent).toBe("1.2k");
    await userEvent.hover(screen.getByRole("button", { name: "Sort by Rating" }));
    expect(
      (
        await screen.findAllByText(
          "Sorted by rating percentage, then upvotes, among the maps loaded so far.",
        )
      ).length,
    ).toBeGreaterThan(0);
  });

  test("the Upvotes column sorts client-side without asking the API for another order", async () => {
    const urls: URL[] = [];
    const list = [m("k1", 5, 0.99), m("k2", 500, 0.8), m("k3", 1200, 0.7)];
    bsApi({
      search: (u) => {
        urls.push(u);
        return page(list);
      },
    });
    const { router } = renderApp("/beatsaver");
    await screen.findByText("k1");
    expect(order()).toEqual(["k1", "k2", "k3"]);
    await userEvent.click(screen.getByRole("button", { name: "Sort by Upvotes" }));
    await waitFor(() => expect(order()).toEqual(["k3", "k2", "k1"]));
    expect(router.state.location.search).toContain("lsort=upvotes");
    expect(urls.every((u) => !u.searchParams.has("lsort"))).toBe(true);
    expect(urls).toHaveLength(1);
    await userEvent.click(screen.getByRole("button", { name: "Sort by Upvotes" }));
    await waitFor(() => expect(order()).toEqual(["k1", "k2", "k3"]));
  });

  test("the Upvotes header tip says the sort is among loaded maps", async () => {
    bsApi({ search: () => page(maps()) });
    renderApp("/beatsaver");
    await screen.findByText("k1");
    await userEvent.hover(screen.getByRole("button", { name: "Sort by Upvotes" }));
    expect(
      (await screen.findAllByText("Sorted by upvotes among the maps loaded so far.")).length,
    ).toBeGreaterThan(0);
  });

  test("the BPM column sorts loaded maps fastest first, unknown last", async () => {
    bsApi({
      search: () =>
        page([
          bsMap(1, { id: "k1", bpm: 90 }),
          bsMap(2, { id: "k2", bpm: null }),
          bsMap(3, { id: "k3", bpm: 180 }),
        ]),
    });
    renderApp("/beatsaver?lsort=bpm");
    await screen.findByText("Song 1");
    expect(order()).toEqual(["k3", "k1", "k2"]);
  });
});
