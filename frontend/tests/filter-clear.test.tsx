import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { FACETS, item, mockFetch, renderApp } from "./helpers";

function api() {
  const items = [item(1, { status: "ok" })];
  return mockFetch((url) => {
    if (url.pathname === "/api/maps/facets") return FACETS;
    if (url.pathname === "/api/maps") return { items, total: 1, offset: 0, limit: 40 };
    return {};
  });
}

describe("desktop filter clear icon", () => {
  test("title clear icon sits in the input row, clears the filter, disabled when empty", async () => {
    api();
    const { router } = renderApp("/?q=abc&qField=title");
    const user = userEvent.setup();
    await screen.findByRole("link", { name: "Song 1" });
    await user.click(screen.getByRole("button", { name: /^Filter Title/ }));
    const dialog = await screen.findByRole("dialog", { name: "Title filter" });
    const input = within(dialog).getByRole("textbox", { name: "Title contains" });
    const clear = within(dialog).getByRole("button", { name: "Clear Title filter" });
    expect(input.closest(".filter-row")).toBe(clear.closest(".filter-row"));
    expect(input.closest(".filter-row")).not.toBeNull();
    expect(within(dialog).getAllByRole("button", { name: /clear/i })).toHaveLength(1);
    expect(clear).toBeEnabled();
    await user.click(clear);
    await waitFor(() => expect(router.state.location.search).not.toContain("q="));
    expect(input).toHaveValue("");
    expect(clear).toBeDisabled();
  });

  test("author clear icon sits beside the mapper search and clears the whole column", async () => {
    api();
    const { router } = renderApp("/?mapper=Alice");
    const user = userEvent.setup();
    await screen.findByRole("link", { name: "Song 1" });
    await user.click(screen.getByRole("button", { name: /^Filter Author/ }));
    const dialog = await screen.findByRole("dialog", { name: "Author filter" });
    const search = within(dialog).getByRole("searchbox", { name: "Search mappers" });
    const clears = within(dialog).getAllByRole("button", { name: "Clear Author filter" });
    expect(clears.some((c) => c.closest(".filter-row") === search.closest(".filter-row"))).toBe(
      true,
    );
    await user.click(clears[clears.length - 1] as HTMLElement);
    await waitFor(() => expect(router.state.location.search).toBe(""));
  });

  test("desktop popovers keep no plain Clear button", async () => {
    api();
    renderApp("/");
    const user = userEvent.setup();
    await screen.findByRole("link", { name: "Song 1" });
    for (const col of ["Levels", "Env", "Status"]) {
      await user.click(screen.getByRole("button", { name: `Filter ${col}` }));
      const dialog = await screen.findByRole("dialog", { name: `${col} filter` });
      expect(within(dialog).queryByRole("button", { name: "Clear" })).toBeNull();
      const clear = within(dialog).getByRole("button", { name: `Clear ${col} filter` });
      expect(clear).toBeDisabled();
      await user.keyboard("{Escape}");
      await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    }
  });
});
