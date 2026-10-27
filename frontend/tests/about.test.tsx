import { screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { mockFetch, renderApp } from "./helpers";

describe("about page", () => {
  test("renders with correct external links", async () => {
    mockFetch(() => ({}));
    renderApp("/about");
    expect(await screen.findByRole("heading", { name: "About saber-tooth" })).toBeInTheDocument();
    const want: Record<string, string> = {
      "saber-tooth on GitHub": "https://github.com/Levia-Labs/saber-tooth",
      "Levia Labs": "https://levialabs.net",
      "beat-analyser (companion)": "https://github.com/Levia-Labs/beat-analyser",
      "Crepidoma (companion)": "https://github.com/Levia-Labs/Crepidoma",
    };
    for (const [name, href] of Object.entries(want)) {
      const a = screen.getByRole("link", { name });
      expect(a).toHaveAttribute("href", href);
      expect(a).toHaveAttribute("target", "_blank");
      expect(a).toHaveAttribute("rel", "noopener noreferrer");
    }
    expect(screen.getByText(/^Version /)).toBeInTheDocument();
  });

  test("header has an About link", async () => {
    mockFetch(() => ({}));
    renderApp("/about");
    const link = await screen.findByRole("link", { name: "About" });
    expect(link).toHaveAttribute("href", "/about");
  });
});
