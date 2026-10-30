import { screen } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import { mediaFor } from "../src/lib/breakpoint";
import { FACETS, item, mockFetch, renderApp } from "./helpers";

const real = window.matchMedia;
afterEach(() => {
  window.matchMedia = real;
  localStorage.clear();
});

/** Evaluate width queries (max and min, decimals allowed) as they would at this viewport. */
function viewport(width: number) {
  window.matchMedia = ((query: string) => {
    const text = mediaFor(query, false);
    const max = /\(max-width:\s*([\d.]+)px\)/.exec(text);
    const min = /\(min-width:\s*([\d.]+)px\)/.exec(text);
    const matches = max ? width <= Number(max[1]) : min ? width >= Number(min[1]) : false;
    return { ...real(query), media: query, matches };
  }) as typeof window.matchMedia;
}

function library() {
  mockFetch((url) =>
    url.pathname === "/api/maps/facets"
      ? FACETS
      : { items: [item(1)], total: 1, offset: 0, limit: 40 },
  );
}

describe("mobile view starts below 1300 px", () => {
  test("at 1000 px the library has the mobile filter bar", async () => {
    viewport(1000);
    library();
    const { container } = renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    expect(container.querySelector(".lib-mobile-bar")).not.toBeNull();
  });

  test("at 1299 px it is still mobile", async () => {
    viewport(1299);
    library();
    const { container } = renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    expect(container.querySelector(".lib-mobile-bar")).not.toBeNull();
  });

  test("at 1400 px it is the desktop table with a column header and no mobile bar", async () => {
    viewport(1400);
    library();
    const { container } = renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    expect(container.querySelector(".lib-mobile-bar")).toBeNull();
    expect(container.querySelector(".lib-head")).not.toBeNull();
  });
});
