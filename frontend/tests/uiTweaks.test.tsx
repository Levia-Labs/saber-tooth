import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { cropApi } from "./crophelpers";
import { mockFetch, renderApp } from "./helpers";

describe("BeatSaver toolbar row", () => {
  test("holds saved searches, More filters and the Maps/Playlists tabs in that order", async () => {
    mockFetch(() => ({ maps: [], docs: [], presets: [] }));
    renderApp("/beatsaver");
    const filters = await screen.findByRole("button", { name: /More filters/ });
    const row = filters.closest(".bs-toolbar") as HTMLElement;
    const saved = within(row).getByRole("group", { name: "Saved filters" });
    const tabs = within(row).getByRole("navigation", { name: "BeatSaver sections" });
    expect(within(tabs).getByRole("link", { name: "Maps" })).toBeInTheDocument();
    expect(within(tabs).getByRole("link", { name: "Playlists" })).toBeInTheDocument();
    const follows = Node.DOCUMENT_POSITION_FOLLOWING;
    expect(saved.compareDocumentPosition(filters) & follows).toBeTruthy();
    expect(filters.compareDocumentPosition(tabs) & follows).toBeTruthy();
  });
});

describe("masthead", () => {
  test("About link sits inside the content-width container", async () => {
    mockFetch(() => ({}));
    renderApp("/about");
    const link = await screen.findByRole("link", { name: "About" });
    expect(link.closest(".masthead-inner")).not.toBeNull();
    expect(link.closest(".masthead-inner")?.parentElement).toHaveClass("masthead");
  });
});

describe("Crop on the map page tabs", () => {
  test("is a tab beside Status, selects its panel and loads lazily", async () => {
    const { calls } = cropApi();
    renderApp("/maps/id0000000001");
    const bar = await screen.findByRole("toolbar", { name: "Fix actions" });
    const crop = await screen.findByRole("tab", { name: "Crop" });
    expect(crop).toHaveAttribute("aria-selected", "false");
    expect(within(bar).getByRole("button", { name: "Scan" })).toBeInTheDocument();
    expect(calls.some((u) => u.pathname.endsWith("/timeline"))).toBe(false);
    const user = userEvent.setup();
    await user.click(crop);
    expect(crop).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByRole("slider", { name: "Crop end" })).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Status" }));
    expect(crop).toHaveAttribute("aria-selected", "false");
    expect(screen.queryByRole("slider", { name: "Crop end" })).toBeNull();
  });

  test("a clean fixed copy shows the Crop and Delete tabs, without Fix and Scan", async () => {
    cropApi({ map: { status: "ok", original_id: "id0000000002" } });
    renderApp("/maps/id0000000001");
    await screen.findByRole("tab", { name: "Crop" });
    await waitFor(() => expect(screen.queryByRole("button", { name: "Scan" })).toBeNull());
    expect(screen.getByRole("tab", { name: "Delete" })).toBeInTheDocument();
  });
});

describe("Crop does not depend on the proposals request", () => {
  function proposalsApi(proposals: () => unknown) {
    const calls: URL[] = [];
    cropApi();
    const base = globalThis.fetch;
    globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input instanceof Request ? input.url : input), "http://localhost");
      if (url.pathname === "/api/maps/id0000000001/proposals") return proposals();
      calls.push(url);
      return base(input, init);
    }) as typeof fetch;
    return calls;
  }

  test("present and working while proposals are pending", async () => {
    const calls = proposalsApi(() => new Promise<Response>(() => {}));
    renderApp("/maps/id0000000001");
    const crop = await screen.findByRole("tab", { name: "Crop" });
    await userEvent.setup().click(crop);
    expect(crop).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByRole("slider", { name: "Crop end" })).toBeInTheDocument();
    expect(calls.some((u) => u.pathname.endsWith("/timeline"))).toBe(true);
  });

  test("present and working when proposals fail with 500", async () => {
    proposalsApi(() => Promise.resolve(new Response('{"error":"boom"}', { status: 500 })));
    renderApp("/maps/id0000000001");
    await screen.findByText("Could not load proposals", {}, { timeout: 5000 });
    const crop = await screen.findByRole("tab", { name: "Crop" });
    await userEvent.setup().click(crop);
    expect(await screen.findByRole("slider", { name: "Crop end" })).toBeInTheDocument();
  });
});

describe("clean copy toolbar", () => {
  test("never shows Fix or Scan, before or after the map resolves", async () => {
    let release: () => void = () => {};
    const gate = new Promise<void>((r) => (release = r));
    const calls = cropApi({ map: { status: "ok", original_id: "id0000000002" } });
    void calls;
    const base = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      if (new URL(String(input), "http://localhost").pathname === "/api/maps/id0000000001") {
        await gate;
      }
      return base(input, init);
    }) as typeof fetch;
    renderApp("/maps/id0000000001");
    const none = () => {
      expect(screen.queryByRole("button", { name: /^Fix$/ })).toBeNull();
      expect(screen.queryByRole("button", { name: "Scan" })).toBeNull();
    };
    none();
    expect(screen.queryByRole("toolbar", { name: "Fix actions" })).toBeNull();
    release();
    await screen.findByRole("tab", { name: "Crop" });
    expect(screen.queryByRole("toolbar", { name: "Fix actions" })).toBeNull();
    none();
  });
});
