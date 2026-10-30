import { screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { mockFetch, renderApp } from "./helpers";

describe("about page", () => {
  test("renders with correct external links", async () => {
    mockFetch(() => ({}));
    renderApp("/about");
    expect(await screen.findByRole("heading", { name: "About Saber Tooth" })).toBeInTheDocument();
    const want: Record<string, string> = {
      "Saber Tooth on GitHub": "https://github.com/Levia-Labs/saber-tooth",
      "Docker Hub": "https://hub.docker.com/r/levialabs/sabertooth",
      "API reference": "https://github.com/Levia-Labs/saber-tooth/blob/main/docs/api.md",
      "MCP setup": "https://github.com/Levia-Labs/saber-tooth/blob/main/docs/api.md#mcp",
      BeatSaver: "https://beatsaver.com",
      "Levia Labs": "https://levialabs.net",
      "beat-analyser (companion)": "https://github.com/Levia-Labs/beat-analyser",
      "Crepidoma (companion)": "https://github.com/Levia-Labs/Crepidoma",
    };
    const links = screen.getByRole("list", { name: "Links" });
    for (const [title, href] of Object.entries(want)) {
      const a = within(links).getByRole("heading", { level: 3, name: title }).closest("a");
      expect(a, title).not.toBeNull();
      expect(a).toHaveAttribute("href", href);
      expect(a?.querySelector("svg.ic")).not.toBeNull();
      expect(a?.querySelector("p")?.textContent?.length).toBeGreaterThan(10);
      expect(a).toHaveAttribute("target", "_blank");
      expect(a).toHaveAttribute("rel", "noopener noreferrer");
    }
    expect(screen.getByText(/^Version /)).toBeInTheDocument();
  });

  test("describes the current features, each in its own card", async () => {
    mockFetch(() => ({}));
    renderApp("/about");
    await screen.findByRole("heading", { name: "About Saber Tooth" });
    const cards = screen.getByRole("list", { name: "Features" });
    const titles = within(cards)
      .getAllByRole("heading", { level: 3 })
      .map((h) => h.textContent);
    expect(titles).toEqual([
      "Quality checker",
      "One-click Fix",
      "Generate from a song",
      "Lightshows",
      "Crop",
      "BeatSaver",
      "Jobs",
      "VR mode",
      "MCP tools",
    ]);
    for (const card of within(cards).getAllByRole("listitem")) {
      const title = within(card).getByRole("heading", { level: 3 });
      const head = title.parentElement as HTMLElement;
      expect(head).toHaveClass("about-card-head");
      expect(head.querySelector("svg.ic")).not.toBeNull();
      expect(head.firstElementChild).toHaveClass("about-icon");
    }
    expect(screen.getByText(/Chroma, Noodle Extensions or Vivify/)).toBeInTheDocument();
  });

  test("the tab bar stays put and only the content region scrolls, like the Library page", async () => {
    mockFetch(() => ({}));
    renderApp("/about");
    const nav = await screen.findByRole("navigation", { name: "Section" });
    const region = screen.getByRole("region", { name: "About content" });
    expect(region).toHaveClass("lib-scroll");
    expect(region).toHaveAttribute("tabindex", "0");
    expect(region.contains(nav)).toBe(false);
    expect(region.contains(screen.getByRole("list", { name: "Features" }))).toBe(true);
    const page = region.closest("section") as HTMLElement;
    expect(page).toHaveClass("library");
    expect(page).not.toHaveClass("page");
    expect(page.contains(nav)).toBe(true);
  });

  test("the good-to-know notes are cards with an icon and a bold title", async () => {
    mockFetch(() => ({}));
    renderApp("/about");
    const notes = await screen.findByRole("list", { name: "Good to know" });
    const cards = within(notes).getAllByRole("listitem");
    expect(cards).toHaveLength(3);
    for (const card of cards) {
      const head = within(card).getByRole("heading", { level: 3 }).parentElement as HTMLElement;
      expect(head).toHaveClass("about-card-head");
      expect(head.firstElementChild).toHaveClass("about-icon");
    }
  });

  test("explains how to use it as ordered steps", async () => {
    mockFetch(() => ({}));
    renderApp("/about");
    const steps = await screen.findByRole("list", { name: "How to use it" });
    expect(steps.tagName).toBe("OL");
    expect(steps).toHaveClass("about-timeline");
    const items = within(steps).getAllByRole("listitem");
    expect(items.length).toBeGreaterThanOrEqual(4);
    for (const li of items) {
      expect(within(li).getByRole("heading", { level: 3 })).toBeInTheDocument();
      expect(li.querySelector("p")).not.toBeNull();
    }
  });
});
