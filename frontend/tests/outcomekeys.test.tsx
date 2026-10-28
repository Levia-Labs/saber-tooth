import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { FACETS, item, mockFetch, renderApp, toasts } from "./helpers";

const REPORT = {
  folder: "Same [saber-tooth]",
  fixed_id: "id0000000099",
  applied: 3,
  errors: 0,
  before: { Easy: { errors: { "too-fast": 1 }, warnings: {} } },
  after: {},
  unfixed: [],
};

describe("toast keys include the map id", () => {
  test("fix results for two maps with the same name stay as two toasts", async () => {
    const items = [
      item(1, { title: "Same", status: "error", errors: 1 }),
      item(2, { title: "Same", status: "error", errors: 1 }),
    ];
    mockFetch((url, init) => {
      if (init?.method === "POST") return { job: "jf" };
      if (url.pathname === "/api/maps/facets") return FACETS;
      if (url.pathname === "/api/jobs/jf") {
        return { id: "jf", kind: "fix", status: "done", error: null, result: REPORT };
      }
      return { items, total: 2, offset: 0, limit: 40 };
    });
    renderApp("/");
    const user = userEvent.setup();
    const buttons = await screen.findAllByRole("button", { name: "Fix Same" });
    expect(buttons).toHaveLength(2);
    await user.click(buttons[0] as HTMLElement);
    await user.click(buttons[1] as HTMLElement);
    await waitFor(() =>
      expect(toasts().getAllByText("Fixed: written to Same [saber-tooth]")).toHaveLength(2),
    );
  });

  test("retry from a failed scan shows the progress toast at once", async () => {
    const map = item(1, { status: "error", errors: 2 });
    let polls = 0;
    mockFetch((url, init) => {
      if (init?.method === "POST") return { job: "js" };
      if (url.pathname === "/api/maps/facets") return FACETS;
      if (url.pathname === "/api/maps/id0000000001") return map;
      if (url.pathname.endsWith("/proposals")) return [];
      if (url.pathname === "/api/jobs/js") {
        polls += 1;
        const failed = polls === 1;
        return {
          id: "js",
          kind: "scan",
          status: failed ? "failed" : "running",
          error: failed ? "scanner crashed" : null,
          result: null,
        };
      }
      return { items: [map], total: 1, offset: 0, limit: 40 };
    });
    renderApp("/maps/id0000000001");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Scan" }));
    await user.click(await toasts().findByRole("button", { name: "Try again" }));
    const stack = document.querySelector(".toast-stack") as HTMLElement;
    await waitFor(() => expect(within(stack).getByText(/Queued|Running/)).toBeInTheDocument());
    expect(within(stack).queryByText("Scan failed")).toBeNull();
  });
});
