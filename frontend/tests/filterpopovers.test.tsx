import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { FACETS, item, mockFetch, renderApp } from "./helpers";

const css = (name: string) => readFileSync(resolve(__dirname, "../src/styles", name), "utf8");
/** The declarations of the rule whose selector is exactly `selector`. */
const rule = (file: string, selector: string) => {
  const text = css(file);
  const start = text.indexOf(`\n${selector} {`);
  if (start < 0) return "";
  return text.slice(start, text.indexOf("}", start));
};

function api() {
  return mockFetch((url) => {
    if (url.pathname === "/api/maps/facets") return FACETS;
    return { items: [item(1)], total: 1, offset: 0, limit: 40 };
  });
}

describe("filter popover bodies", () => {
  test("the Author popover holds one text input, the mapper search", async () => {
    api();
    renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    await userEvent.click(screen.getByRole("button", { name: /^Filter Author/ }));
    const dialog = await screen.findByRole("dialog", { name: "Author filter" });
    expect(within(dialog).getAllByRole("searchbox")).toHaveLength(1);
    expect(within(dialog).queryByRole("textbox")).toBeNull();
    expect(within(dialog).getByLabelText("Search mappers")).toBeInTheDocument();
    expect(within(dialog).queryByLabelText("Name contains")).toBeNull();
  });

  test("the Author clear button still clears an old q=...&qField=mapper URL", async () => {
    api();
    const { router } = renderApp("/?q=abc&qf=mapper");
    await screen.findByRole("link", { name: "Song 1" });
    await userEvent.click(screen.getByRole("button", { name: /^Filter Author/ }));
    await userEvent.click(await screen.findByRole("button", { name: "Clear Author filter" }));
    await waitFor(() => expect(router.state.location.search).not.toContain("q="));
  });

  test("the Length inputs take mm:ss on one row with the clear button at its right", async () => {
    const { calls } = api();
    const { router } = renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    await userEvent.click(screen.getByRole("button", { name: /^Filter Length/ }));
    const dialog = await screen.findByRole("dialog", { name: "Length filter" });
    const min = within(dialog).getByLabelText("Minimum length");
    const max = within(dialog).getByLabelText("Maximum length");
    expect(min).toHaveAttribute("placeholder", "mm:ss");
    const clear = within(dialog).getByRole("button", { name: "Clear Length filter" });
    const row = min.closest(".filter-row") as HTMLElement;
    expect(row).not.toBeNull();
    expect(row).toContainElement(max);
    expect(row).toContainElement(clear);
    expect(row.lastElementChild).toBe(clear);
    expect(row.textContent).toContain("-");
    await userEvent.type(min, "3:30");
    await waitFor(() => expect(router.state.location.search).toContain("duration_min=210"));
    await waitFor(() =>
      expect(
        calls.some(
          (u) => u.pathname === "/api/maps" && u.searchParams.get("duration_min") === "210",
        ),
      ).toBe(true),
    );
    await userEvent.type(max, "1:7x");
    expect(router.state.location.search).not.toContain("duration_max");
    await userEvent.clear(max);
    await userEvent.type(max, "5:00");
    await waitFor(() => expect(router.state.location.search).toContain("duration_max=300"));
  });

  test("an outside value shows as mm:ss", async () => {
    api();
    renderApp("/?duration_min=210");
    await screen.findByRole("link", { name: "Song 1" });
    await userEvent.click(screen.getByRole("button", { name: /^Filter Length/ }));
    expect(await screen.findByLabelText("Minimum length")).toHaveValue("03:30");
  });

  test("Status, Levels, Env and Author put clear at the right of the first row", async () => {
    api();
    renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    for (const col of ["Status", "Levels", "Env", "Author"]) {
      await userEvent.click(screen.getByRole("button", { name: new RegExp(`^Filter ${col}`) }));
      const dialog = await screen.findByRole("dialog", { name: `${col} filter` });
      const clear = within(dialog).getByRole("button", { name: `Clear ${col} filter` });
      const body = dialog.querySelector(".filter-body") as HTMLElement;
      expect(body.firstElementChild).toContainElement(clear);
      expect(body.firstElementChild?.lastElementChild).toBe(clear);
      await userEvent.keyboard("{Escape}");
    }
  });
});

describe("filter popover scrolling", () => {
  test("the popover is a column that does not scroll; the lists do", () => {
    const popover = rule("overlays.css", ".popover");
    expect(popover).toMatch(/display:\s*flex/);
    expect(popover).toMatch(/flex-direction:\s*column/);
    expect(popover).toMatch(/overflow:\s*hidden/);
    expect(popover).toMatch(/max-height:/);
    const body = rule("filters.css", ".popover .filter-body");
    expect(body).toMatch(/display:\s*flex/);
    expect(body).toMatch(/min-height:\s*0/);
    expect(body).not.toMatch(/overflow:\s*auto/);
    const checks = rule("filters.css", ".filter-body .checks");
    expect(checks).toMatch(/overflow(-y)?:\s*auto/);
    expect(checks).toMatch(/min-height:\s*0/);
  });
});
