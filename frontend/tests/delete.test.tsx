import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { item, mockFetch, renderApp } from "./helpers";

const ID = "id0000000001";

function api(opts: { fail?: boolean; job?: boolean } = {}) {
  return mockFetch((url, init) => {
    if (init?.method === "DELETE" && url.pathname === `/api/maps/${ID}`) {
      if (opts.fail) {
        return new Response(JSON.stringify({ error: "map has a job" }), {
          status: 409,
          headers: { "Content-Type": "application/json" },
        });
      }
      return { deleted: "Folder 1" };
    }
    if (url.pathname === `/api/maps/${ID}`) {
      return item(1, opts.job ? { job: { id: "j", kind: "scan", status: "running" } } : {});
    }
    if (url.pathname.endsWith("/proposals")) return [];
    if (url.pathname === "/api/maps") return { items: [], total: 0, offset: 0, limit: 40 };
    return {};
  });
}

const deletes = (fn: ReturnType<typeof api>["fn"]) =>
  fn.mock.calls.filter(([, init]) => init?.method === "DELETE");

describe("delete map", () => {
  test("the Delete tab confirms inline, naming the folder; Back does nothing", async () => {
    const { fn } = api();
    renderApp(`/maps/${ID}`);
    await userEvent.click(await screen.findByRole("tab", { name: "Delete" }));
    const panel = await screen.findByRole("tabpanel");
    expect(panel).toHaveTextContent("Delete permanently?");
    expect(panel).toHaveTextContent("Folder 1");
    expect(panel).toHaveTextContent("cannot be undone");
    expect(screen.queryByRole("dialog")).toBeNull();
    await userEvent.click(within(panel).getByRole("button", { name: "Back" }));
    expect(screen.getByRole("tab", { name: "Status" })).toHaveAttribute("aria-selected", "true");
    expect(deletes(fn)).toHaveLength(0);
  });

  test("confirm sends DELETE, navigates to the library and shows a banner", async () => {
    const { fn } = api();
    const { router } = renderApp(`/maps/${ID}`);
    await userEvent.click(await screen.findByRole("tab", { name: "Delete" }));
    const panel = await screen.findByRole("tabpanel");
    await userEvent.click(within(panel).getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(deletes(fn)).toHaveLength(1));
    expect(String(deletes(fn)[0]?.[0])).toContain(`/api/maps/${ID}`);
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    expect(await screen.findByText("Deleted")).toBeVisible();
  });

  test("an error announces danger and stays on the page", async () => {
    api({ fail: true });
    const { router } = renderApp(`/maps/${ID}`);
    await userEvent.click(await screen.findByRole("tab", { name: "Delete" }));
    const panel = await screen.findByRole("tabpanel");
    await userEvent.click(within(panel).getByRole("button", { name: "Delete" }));
    expect(await screen.findByText(/map has a job/)).toBeVisible();
    expect(router.state.location.pathname).toBe(`/maps/${ID}`);
  });

  test("the button is disabled while a job runs", async () => {
    api({ job: true });
    renderApp(`/maps/${ID}?tab=delete`);
    const panel = await screen.findByRole("tabpanel");
    expect(within(panel).getByRole("button", { name: "Delete" })).toBeDisabled();
  });
});
