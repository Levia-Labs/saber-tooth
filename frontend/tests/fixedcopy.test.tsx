import { screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { FACETS, item, mockFetch, renderApp } from "./helpers";

const items = [
  item(1, {
    status: "error",
    fixed_copy_id: "id0000000099",
    fixed_copy_folder: "Folder 1 [saber-tooth]",
  }),
  item(2, { status: "ok" }),
];

describe("fixed copy link", () => {
  test("original row links to its fixed copy, other rows show none", async () => {
    mockFetch((url) => {
      if (url.pathname === "/api/maps/facets") return FACETS;
      return { items, total: items.length, offset: 0, limit: 40 };
    });
    renderApp("/");
    const title = await screen.findByRole("link", { name: "Song 1" });
    const row = within(title.closest("[role=row]") as HTMLElement);
    expect(row.getByRole("link", { name: "Folder 1 [saber-tooth]" })).toHaveAttribute(
      "href",
      "/maps/id0000000099",
    );
    const other = within(
      screen.getByRole("link", { name: "Song 2" }).closest("[role=row]") as HTMLElement,
    );
    expect(other.queryByText(/Fixed copy:/)).toBeNull();
  });

  test("map page shows the fixed copy as a banner alert with a link to it", async () => {
    mockFetch((url) => {
      if (url.pathname === "/api/maps/facets") return FACETS;
      if (url.pathname === "/api/maps/id0000000001") return items[0];
      if (url.pathname.endsWith("/proposals")) return [];
      return { items: [], total: 0, offset: 0, limit: 40 };
    });
    renderApp("/maps/id0000000001");
    const title = await screen.findByText("Fixed copy ready");
    const banner = title.closest(".alert") as HTMLElement;
    expect(banner).toHaveClass("alert-success");
    expect(within(banner).getByRole("link", { name: "Folder 1 [saber-tooth]" })).toHaveAttribute(
      "href",
      "/maps/id0000000099",
    );
    expect(screen.queryByText(/Fixed copy:/)).toBeNull();
  });
});
