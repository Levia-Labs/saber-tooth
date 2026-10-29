import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, test } from "vitest";
import { useJobRunner } from "../src/api/jobs";
import { AnnouncerProvider } from "../src/components/Announcer";
import { mockFetch, toasts } from "./helpers";

function Harness() {
  const runner = useJobRunner("Fix Song");
  return (
    <button type="button" onClick={() => void runner.run(async () => ({ job: "j1" }))}>
      go
    </button>
  );
}

function mount() {
  const router = createMemoryRouter(
    [
      { path: "/", element: <Harness /> },
      { path: "/jobs", element: <p>jobs page</p> },
    ],
    { initialEntries: ["/"] },
  );
  render(
    <AnnouncerProvider>
      <RouterProvider router={router} />
    </AnnouncerProvider>,
  );
  return router;
}

describe("page-started job toasts", () => {
  test("running toast has rounds, no buttons beyond the X, and opens /jobs on click", async () => {
    mockFetch(() => ({
      id: "j1",
      kind: "fix",
      status: "running",
      progress: "round 1 of 3",
      cancel_requested: false,
    }));
    const router = mount();
    fireEvent.click(screen.getByText("go"));
    const title = await toasts().findByText("Fix Song");
    expect(await toasts().findByText("1/3")).toBeTruthy();
    expect(toasts().queryByRole("button", { name: /cancel/i })).toBeNull();
    expect(toasts().getAllByRole("button")).toHaveLength(2);
    await act(async () => title.click());
    await waitFor(() => expect(router.state.location.pathname).toBe("/jobs"));
  });

  test("the outcome toast opens /jobs on click", async () => {
    mockFetch(() => ({ id: "j1", kind: "fix", status: "done", result: {} }));
    const router = mount();
    fireEvent.click(screen.getByText("go"));
    fireEvent.click(await toasts().findByText("Done"));
    await waitFor(() => expect(router.state.location.pathname).toBe("/jobs"));
  });
});
