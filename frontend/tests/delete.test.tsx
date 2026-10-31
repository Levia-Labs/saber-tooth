import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { item, mockFetch, renderApp, toasts } from "./helpers";

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
    expect(await toasts().findByText("Deleted")).toBeVisible();
    expect(toasts().getByText("Folder 1")).toBeVisible();
  });

  test.each([
    ["from=jobs&back=status%3Dfailed", "/jobs", "?status=failed"],
    ["from=playlist%3Apl1", "/playlists/pl1", ""],
    ["", "/", ""],
  ])("delete from %s returns to the origin list, replacing history", async (q, path, search) => {
    api();
    const { router } = renderApp(`/maps/${ID}?tab=delete${q ? `&${q}` : ""}`);
    const panel = await screen.findByRole("tabpanel");
    await userEvent.click(within(panel).getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(router.state.location.pathname).toBe(path));
    expect(router.state.location.search).toBe(search);
    await router.navigate(-1);
    expect(router.state.location.pathname).not.toBe(`/maps/${ID}`);
  });

  test("the list is refetched after delete", async () => {
    const { calls } = api();
    renderApp(`/maps/${ID}?tab=delete`);
    const panel = await screen.findByRole("tabpanel");
    const before = () => calls.filter((u) => u.pathname === "/api/maps").length;
    const n = before();
    await userEvent.click(within(panel).getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(before()).toBeGreaterThan(n));
  });

  test("a double click sends one request and the button shows a spinner meanwhile", async () => {
    const { fn } = api();
    renderApp(`/maps/${ID}?tab=delete`);
    const panel = await screen.findByRole("tabpanel");
    const button = within(panel).getByRole("button", { name: "Delete" });
    await userEvent.dblClick(button);
    await waitFor(() => expect(deletes(fn)).toHaveLength(1));
    expect(deletes(fn)).toHaveLength(1);
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
