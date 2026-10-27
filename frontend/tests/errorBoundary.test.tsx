import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { PageBoundary } from "../src/components/ErrorPanel";
import { RouteError } from "../src/components/RouteError";
import { mockFetch, renderApp } from "./helpers";

let broken = true;
function Flaky() {
  if (broken) throw new Error("kaboom: bpm is null");
  return <p>page ok</p>;
}

let spy: ReturnType<typeof vi.spyOn>;
beforeEach(() => {
  broken = true;
  spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
});
afterEach(() => spy.mockRestore());

function inRouter(ui: ReactNode) {
  const router = createMemoryRouter([{ path: "/", element: ui, errorElement: <RouteError /> }]);
  return render(<RouterProvider router={router} />);
}

describe("PageBoundary", () => {
  test("renders the friendly panel, details and logs the error", () => {
    inRouter(
      <PageBoundary>
        <Flaky />
      </PageBoundary>,
    );
    expect(screen.getByText("This page hit a problem and could not be shown.")).toBeInTheDocument();
    expect(screen.getByText("kaboom: bpm is null")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to library" })).toHaveAttribute("href", "/");
    expect(spy).toHaveBeenCalled();
  });

  test("Try again recovers once the error stops", async () => {
    inRouter(
      <PageBoundary>
        <Flaky />
      </PageBoundary>,
    );
    broken = false;
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(screen.getByText("page ok")).toBeInTheDocument();
  });
});

describe("route errorElement", () => {
  test("a route that throws shows the panel and Try again re-renders it", async () => {
    inRouter(<Flaky />);
    expect(screen.getByText("This page hit a problem and could not be shown.")).toBeInTheDocument();
    broken = false;
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("page ok")).toBeInTheDocument();
  });

  test("unknown address shows Not found", async () => {
    mockFetch(() => ({}));
    renderApp("/nope/at/all");
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });
});
