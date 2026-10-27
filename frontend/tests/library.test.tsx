import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { FIRST_SKELETONS } from "../src/components/LibraryTable";
import { FACETS, item, mockFetch, renderApp } from "./helpers";

const items = [
  item(1, { status: "error", errors: 3, pending: 2 }),
  item(2, { status: "ok" }),
  item(3, { status: "scanning", job: { id: "j1", kind: "scan", status: "running" } }),
  item(4, { status: "unscanned", bpm: null, duration_s: null, approved: 1 }),
];

function api(page = items) {
  return mockFetch((url) => {
    if (url.pathname === "/api/maps/facets") return FACETS;
    if (url.pathname === "/api/maps") {
      return { items: page, total: page.length, offset: 0, limit: 40 };
    }
    if (url.pathname.startsWith("/api/jobs/")) {
      return { id: "j1", kind: "scan", status: "running", error: null, result: null };
    }
    return {};
  });
}

describe("library page", () => {
  test("shows skeleton rows with the final row structure while loading", async () => {
    mockFetch(() => new Promise(() => undefined) as never);
    const { container } = renderApp("/");
    await waitFor(() =>
      expect(container.querySelectorAll("[data-skeleton]")).toHaveLength(FIRST_SKELETONS),
    );
    const first = container.querySelector("[data-skeleton]") as HTMLElement;
    expect(first.querySelectorAll("[role=cell]")).toHaveLength(10);
    expect(screen.getByRole("columnheader", { name: /title/i })).toBeInTheDocument();
  });

  test("renders rows with status, levels, length, bpm and actions", async () => {
    api();
    renderApp("/");
    const first = (await screen.findByRole("link", { name: "Song 1" })).closest("[role=row]");
    const row = within(first as HTMLElement);
    expect(row.getByText("3 errors")).toBeInTheDocument();
    expect(row.getAllByText("3:21").length).toBeGreaterThan(0);
    expect(row.getAllByText("128 BPM").length).toBeGreaterThan(0);
    expect(row.getAllByText("Expert+").length).toBeGreaterThan(0);
    expect(row.getByRole("link", { name: /Review Song 1, 2 fixes/ })).toHaveAttribute(
      "href",
      "/maps/id0000000001",
    );
    expect(row.getByRole("button", { name: "Scan Song 1" })).toBeEnabled();
    expect(row.queryByRole("button", { name: /Apply approved/ })).toBeNull();
  });

  test("each column cell shows only its own data", async () => {
    api();
    renderApp("/");
    const first = (await screen.findByRole("link", { name: "Song 1" })).closest("[role=row]");
    const cells = (cls: string) => (first as HTMLElement).querySelector(`.${cls}`) as HTMLElement;
    const title = cells("col-title");
    expect(title.textContent).toBe("Song 1");
    expect(title.querySelector(".level, .chip")).toBeNull();
    expect(title.textContent).not.toContain("Mapper 1");
    const levels = cells("col-levels");
    expect(levels.querySelectorAll("li.level")).toHaveLength(3);
    expect(levels.textContent).toBe("EasyExpertExpert+");
    expect(levels.querySelector(".chip")).toBeNull();
    expect(cells("col-author").textContent).toBe("Mapper 1");
    expect(cells("col-env").textContent).toBe("Origins");
  });

  test("environment names are shown without the Environment suffix", async () => {
    api();
    renderApp("/");
    const second = (await screen.findByRole("link", { name: "Song 2" })).closest("[role=row]");
    expect((second as HTMLElement).querySelector(".col-env")?.textContent).toBe("Big Mirror");
  });

  test("mapper and level URL filters become API parameters", async () => {
    const { calls } = api();
    renderApp("/?mapper=Mapper%201&mapper=A%2C%20B&level=Easy&level=Hard&lmode=all&sort=levels");
    await screen.findByRole("link", { name: "Song 1" });
    const request = calls.find((u) => u.pathname === "/api/maps");
    expect(request?.searchParams.getAll("mapper")).toEqual(["Mapper 1", "A, B"]);
    expect(request?.searchParams.getAll("level")).toEqual(["Easy", "Hard"]);
    expect(request?.searchParams.get("level_mode")).toBe("all");
    expect(request?.searchParams.get("sort")).toBe("levels");
  });

  test("author and levels headers sort and open their filters", async () => {
    api();
    renderApp("/");
    await screen.findByRole("link", { name: "Song 1" });
    expect(screen.getByRole("button", { name: "Sort by Author" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sort by Levels" })).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Filter Levels" }));
    const dialog = await screen.findByRole("dialog", { name: "Levels filter" });
    expect(within(dialog).getByRole("button", { name: "Any" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(within(dialog).getByRole("checkbox", { name: "Expert+" })).toBeInTheDocument();
  });

  test("a row with approved fixes offers Apply and a running row disables Scan", async () => {
    api();
    renderApp("/");
    const four = (await screen.findByRole("link", { name: "Song 4" })).closest("[role=row]");
    expect(
      within(four as HTMLElement).getByRole("button", { name: /Apply approved/ }),
    ).toBeEnabled();
    expect(within(four as HTMLElement).getAllByText("–").length).toBeGreaterThan(0);
    const three = (await screen.findByRole("link", { name: "Song 3" })).closest("[role=row]");
    expect(within(three as HTMLElement).getByText("Scanning")).toBeInTheDocument();
    expect(
      within(three as HTMLElement).getByRole("button", { name: "Scan Song 3" }),
    ).toBeDisabled();
  });

  test("filters in the URL become API parameters", async () => {
    const { calls } = api();
    renderApp("/?q=moon&status=error,warn&env=Origins&sort=bpm&order=desc");
    await screen.findByRole("link", { name: "Song 1" });
    const request = calls.find((u) => u.pathname === "/api/maps");
    expect(request?.searchParams.get("q")).toBe("moon");
    expect(request?.searchParams.get("q_fields")).toBe("title");
    expect(request?.searchParams.get("status")).toBe("error,warn");
    expect(request?.searchParams.getAll("env")).toEqual(["Origins"]);
    expect(request?.searchParams.get("sort")).toBe("bpm");
    expect(request?.searchParams.get("order")).toBe("desc");
  });

  test("clicking a sort header updates the URL and sets aria-sort", async () => {
    api();
    const { router } = renderApp("/");
    const user = userEvent.setup();
    await screen.findByRole("link", { name: "Song 1" });
    await user.click(screen.getByRole("button", { name: "Sort by BPM" }));
    expect(router.state.location.search).toBe("?sort=bpm&order=desc");
    expect(screen.getByRole("columnheader", { name: /BPM/ })).toHaveAttribute(
      "aria-sort",
      "descending",
    );
  });
});

describe("column filters", () => {
  test("status popover lists facet counts and writes the selection to the URL", async () => {
    api();
    const { router } = renderApp("/");
    const user = userEvent.setup();
    await screen.findByRole("link", { name: "Song 1" });
    await user.click(screen.getByRole("button", { name: "Filter Status" }));
    const dialog = await screen.findByRole("dialog", { name: "Status filter" });
    expect(within(dialog).getByText("Scanning")).toBeInTheDocument();
    expect(within(dialog).getByText("Queued")).toBeInTheDocument();
    await user.click(within(dialog).getByRole("checkbox", { name: "Errors" }));
    await user.click(within(dialog).getByRole("checkbox", { name: "Warnings" }));
    expect(router.state.location.search).toBe("?status=error%2Cwarn");
    await user.click(within(dialog).getByRole("button", { name: "Clear" }));
    expect(router.state.location.search).toBe("");
  });

  test("Escape closes the popover and returns focus to its button", async () => {
    api();
    renderApp("/");
    const user = userEvent.setup();
    await screen.findByRole("link", { name: "Song 1" });
    const button = screen.getByRole("button", { name: "Filter Environment" });
    await user.click(button);
    expect(await screen.findByRole("dialog", { name: "Environment filter" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(button).toHaveFocus();
  });

  test("title filter debounces into q and shows an active badge", async () => {
    api();
    const { router } = renderApp("/");
    const user = userEvent.setup();
    await screen.findByRole("link", { name: "Song 1" });
    await user.click(screen.getByRole("button", { name: "Filter Title" }));
    await user.type(await screen.findByLabelText("Title contains"), "moon");
    await waitFor(() => expect(router.state.location.search).toBe("?q=moon"));
    await user.keyboard("{Escape}");
    expect(
      await screen.findByRole("button", { name: "Filter Title, 1 active" }),
    ).toBeInTheDocument();
  });

  test("every header and row button has a tooltip on focus", async () => {
    api();
    renderApp("/");
    const user = userEvent.setup();
    await screen.findByRole("link", { name: "Song 1" });
    await user.tab();
    await user.hover(screen.getByRole("link", { name: /Generate map/ }));
    const tip = await screen.findByRole("tooltip");
    expect(tip).toHaveTextContent("Create a new map with all five difficulties");
  });
});

describe("live job status", () => {
  test("starting a scan shows queued on that row at once and polls the job", async () => {
    const { calls } = mockFetch((url, init) => {
      if (url.pathname === "/api/maps/facets") return FACETS;
      if (url.pathname === "/api/maps/id0000000002/scan" && init?.method === "POST") {
        return { job: "j9" };
      }
      if (url.pathname === "/api/jobs/j9") {
        return { id: "j9", kind: "scan", status: "running", error: null, result: null };
      }
      return { items, total: items.length, offset: 0, limit: 40 };
    });
    renderApp("/");
    const user = userEvent.setup();
    const link = await screen.findByRole("link", { name: "Song 2" });
    const row = within(link.closest("[role=row]") as HTMLElement);
    await user.click(row.getByRole("button", { name: "Scan Song 2" }));
    expect(await row.findByText("Queued")).toBeInTheDocument();
    expect(row.getByRole("button", { name: "Scan Song 2" })).toBeDisabled();
    await waitFor(() => expect(calls.some((u) => u.pathname === "/api/jobs/j9")).toBe(true));
  });
});
