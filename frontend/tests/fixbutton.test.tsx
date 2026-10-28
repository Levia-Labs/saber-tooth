import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test } from "vitest";
import { clearFixOutcomes } from "../src/api/fix";
import { readFixReport } from "../src/lib/fixreport";
import { TIPS } from "../src/lib/tips";
import { FACETS, item, mockFetch, renderApp } from "./helpers";

const items = [item(1, { status: "error", errors: 2 }), item(2, { status: "ok" })];

const REPORT = {
  map_id: "id0000000001",
  folder: "Folder 1 [saber-tooth]",
  fixed_id: "id0000000099",
  applied: 7,
  errors: 0,
  before: {
    Easy: { errors: { "missing-difficulty": 1 }, warnings: {} },
    Hard: { errors: { "too-fast": 2 }, warnings: {} },
  },
  after: {},
  unfixed: [],
};

function api(job: { status: string; error?: string | null; result: unknown }) {
  const posts: string[] = [];
  const mock = mockFetch((url, init) => {
    if (init?.method === "POST") {
      posts.push(url.pathname);
      return { job: "jf" };
    }
    if (url.pathname === "/api/maps/facets") return FACETS;
    if (url.pathname === "/api/maps/id0000000001") return items[0];
    if (url.pathname === "/api/maps/id0000000001/proposals") return [];
    if (url.pathname === "/api/jobs/jf") {
      return { id: "jf", kind: "fix", error: null, ...job };
    }
    return { items, total: items.length, offset: 0, limit: 40 };
  });
  return { ...mock, posts };
}

afterEach(clearFixOutcomes);

describe("fix button", () => {
  test("is the first row action with the tip and starts a fix job", async () => {
    const { posts } = api({ status: "done", result: REPORT });
    renderApp("/");
    const user = userEvent.setup();
    const link = await screen.findByRole("link", { name: "Song 1" });
    const row = within(link.closest("[role=row]") as HTMLElement);
    const actions = row.getAllByRole("button");
    expect(actions[0]).toHaveAccessibleName("Fix Song 1");
    // Fix is styled like a plain icon action, not as a coloured accent button.
    expect(actions[0]).not.toHaveClass("accent");
    await user.hover(actions[0] as HTMLElement);
    expect(await screen.findByRole("tooltip")).toHaveTextContent(TIPS.fix);
    await user.click(actions[0] as HTMLElement);
    await waitFor(() => expect(posts).toContain("/api/maps/id0000000001/fix"));
  });

  test("shows the fixing state on the row while the job runs", async () => {
    api({ status: "running", result: null });
    renderApp("/");
    const user = userEvent.setup();
    const link = await screen.findByRole("link", { name: "Song 1" });
    const row = within(link.closest("[role=row]") as HTMLElement);
    await user.click(row.getByRole("button", { name: "Fix Song 1" }));
    expect(await row.findByRole("img", { name: /Queued|Fixing/ })).toBeInTheDocument();
    expect(row.getByRole("button", { name: "Fix Song 1" })).toBeDisabled();
  });

  test("a finished fix shows a success alert with summary and a link to the new map", async () => {
    api({ status: "done", result: REPORT });
    renderApp("/");
    const user = userEvent.setup();
    const link = await screen.findByRole("link", { name: "Song 1" });
    await user.click(
      within(link.closest("[role=row]") as HTMLElement).getByRole("button", { name: "Fix Song 1" }),
    );
    const alert = await screen.findByText("Fixed: written to Folder 1 [saber-tooth]");
    const box = alert.closest(".alert") as HTMLElement;
    expect(box).toHaveClass("alert-success");
    expect(box).toHaveTextContent("Errors 3 -> 0, 1 difficulty added, 7 fixes applied");
    expect(within(box).getByRole("link", { name: "Open fixed map" })).toHaveAttribute(
      "href",
      "/maps/id0000000099",
    );
  });

  test("a failed fix shows a danger alert listing the unfixed findings", async () => {
    api({
      status: "done",
      result: {
        ...REPORT,
        errors: 1,
        unfixed: [{ difficulty: "Hard", rule: "x", message: "bad wall", reason: "no safe spot" }],
      },
    });
    renderApp("/");
    const user = userEvent.setup();
    const link = await screen.findByRole("link", { name: "Song 1" });
    await user.click(
      within(link.closest("[role=row]") as HTMLElement).getByRole("button", { name: "Fix Song 1" }),
    );
    const alert = (await screen.findByText(/Fix incomplete/)).closest(".alert") as HTMLElement;
    expect(alert).toHaveClass("alert-danger");
    expect(alert).toHaveTextContent("Hard: bad wall (no safe spot)");
  });

  test("a failed job shows a danger alert with the error", async () => {
    api({ status: "failed", error: "disk full", result: null });
    renderApp("/");
    const user = userEvent.setup();
    const link = await screen.findByRole("link", { name: "Song 1" });
    await user.click(
      within(link.closest("[role=row]") as HTMLElement).getByRole("button", { name: "Fix Song 1" }),
    );
    const alert = (await screen.findByText(/Fix failed/)).closest(".alert") as HTMLElement;
    expect(alert).toHaveClass("alert-danger");
    expect(alert).toHaveTextContent("disk full");
  });

  test("the map page toolbar leads with the Fix button", async () => {
    const { posts } = api({ status: "done", result: REPORT });
    renderApp("/maps/id0000000001");
    const user = userEvent.setup();
    const toolbar = await screen.findByRole("toolbar", { name: "Fix actions" });
    const first = within(toolbar).getAllByRole("button")[0] as HTMLElement;
    expect(first).toHaveTextContent("Fix");
    await user.click(first);
    await waitFor(() => expect(posts).toContain("/api/maps/id0000000001/fix"));
    expect(await screen.findByText("Fixed: written to Folder 1 [saber-tooth]")).toBeInTheDocument();
  });
});

describe("readFixReport", () => {
  test("sums errors and counts added difficulties", () => {
    const rep = readFixReport({
      id: "j",
      kind: "fix",
      status: "done",
      error: null,
      result: REPORT,
    });
    expect(rep).toMatchObject({
      errorsBefore: 3,
      errorsAfter: 0,
      difficultiesAdded: 1,
      applied: 7,
    });
  });
});
