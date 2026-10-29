import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { FixesSkeleton, MapHeadSkeleton, PageSkeleton } from "../src/components/Skeletons";
import { mockFetch, renderApp } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

describe("skeleton loading states", () => {
  test("map page shows header and fix skeletons, no visible Loading text", async () => {
    mockFetch(() => new Promise(() => undefined));
    const { container } = renderApp("/maps/id0000000001");
    await vi.waitFor(() => expect(container.querySelector(".card-skeleton")).not.toBeNull());
    expect(container.querySelectorAll(".card-skeleton").length).toBeGreaterThan(0);
    expect(container.querySelector(".maphead[aria-busy='true']")).not.toBeNull();
    expect(screen.getAllByRole("status", { name: "Loading" }).length).toBeGreaterThan(0);
    const visible = [...container.querySelectorAll("p, span, div")].filter(
      (el) => !el.closest(".sr-only") && !el.classList.contains("sr-only"),
    );
    expect(visible.some((el) => el.children.length === 0 && /loading/i.test(el.textContent))).toBe(
      false,
    );
  });

  test("each skeleton is busy and has a hidden Loading label", () => {
    const { container } = render(
      <>
        <MapHeadSkeleton />
        <FixesSkeleton count={3} />
        <PageSkeleton />
      </>,
    );
    expect(container.querySelectorAll("[aria-busy='true']")).toHaveLength(3);
    expect(container.querySelectorAll(".card-skeleton")).toHaveLength(3);
    expect(screen.getAllByRole("status", { name: "Loading" })).toHaveLength(3);
    expect(container).not.toHaveTextContent(/loading/i);
  });
});
