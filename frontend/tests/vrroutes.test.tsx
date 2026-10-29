import { screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { bsMap, page, SEEDED } from "./bshelpers";
import { item, mockFetch, renderApp } from "./helpers";

function api() {
  return mockFetch((url) => {
    if (url.pathname === "/api/maps") return { items: [item(1)], total: 1, offset: 0, limit: 40 };
    if (url.pathname === "/api/maps/id0000000001") return item(1);
    if (url.pathname.endsWith("/proposals")) return [];
    if (url.pathname === "/api/beatsaver/search") return page([bsMap(1)]);
    if (url.pathname === "/api/beatsaver/presets") return [SEEDED];
    return {};
  });
}

describe("VR routes", () => {
  test("/vr is the desktop library table under the VR styling", async () => {
    api();
    renderApp("/vr");
    expect(await screen.findByRole("heading", { name: "Library", level: 1 })).toBeInTheDocument();
    expect(await screen.findByText("Song 1")).toBeInTheDocument();
    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(document.documentElement.dataset.ui).toBe("vr");
  });

  test("/vr/maps/:id is the desktop map page", async () => {
    api();
    renderApp("/vr/maps/id0000000001");
    expect(await screen.findByRole("heading", { name: "Song 1" })).toBeInTheDocument();
    expect(document.documentElement.dataset.ui).toBe("vr");
  });

  test("/vr/beatsaver is the desktop BeatSaver page", async () => {
    api();
    renderApp("/vr/beatsaver");
    expect(
      await screen.findByRole("navigation", { name: "BeatSaver sections" }),
    ).toBeInTheDocument();
    expect(document.documentElement.dataset.ui).toBe("vr");
  });

  test("an unknown VR path still reaches the not-found page", async () => {
    api();
    renderApp("/vr/nope");
    expect(await screen.findByText(/not found/i)).toBeInTheDocument();
  });

  test("the desktop routes are unchanged", async () => {
    api();
    renderApp("/beatsaver");
    expect(
      await screen.findByRole("navigation", { name: "BeatSaver sections" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("radiogroup", { name: "Sort by" })).toBeNull();
  });
});
