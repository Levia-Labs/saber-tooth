import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import type { Proposal } from "../src/api/types";
import { FACETS, item, mockFetch, renderApp } from "./helpers";

const note = { beat: 4, x: 1, y: 0, color: 0, cut: 1 };

function proposal(id: number, patch: Partial<Proposal> = {}): Proposal {
  return {
    id,
    rule: "flip-cut",
    difficulty: "Hard",
    severity: "error",
    summary: `Fix ${id}`,
    status: "pending",
    before: [note],
    after: [{ ...note, cut: 0 }],
    walls_before: [],
    walls_after: [],
    walls_context: [],
    ...patch,
  };
}

const notFound = () =>
  new Response(JSON.stringify({ error: "unknown map" }), {
    status: 404,
    headers: { "Content-Type": "application/json" },
  });

function mapApi(proposals: Proposal[]) {
  const posts: string[] = [];
  const state = { proposals };
  const api = mockFetch((url, init) => {
    if (init?.method === "POST") {
      posts.push(url.pathname);
      if (url.pathname.endsWith("/approve")) {
        const id = Number(url.pathname.split("/")[3]);
        state.proposals = state.proposals.map((p) =>
          p.id === id ? { ...p, status: "approved" } : p,
        );
        return { id, status: "approved" };
      }
      return { job: "j1" };
    }
    if (url.pathname === "/api/maps/facets") return FACETS;
    if (url.pathname === "/api/maps/id0000000001") {
      return item(1, { status: "error", errors: 2, cover_url: "/api/maps/id0000000001/cover" });
    }
    if (url.pathname === "/api/maps/id0000000001/proposals") return state.proposals;
    if (url.pathname.startsWith("/api/maps/missing0000")) return notFound();
    if (url.pathname === "/api/jobs/j1") {
      return { id: "j1", kind: "scan", status: "done", error: null, result: {} };
    }
    return { items: [], total: 0, offset: 0, limit: 40 };
  });
  return { ...api, posts };
}

describe("routes", () => {
  test("map page renders header, tempo, levels and grouped proposals", async () => {
    mapApi([proposal(1), proposal(2, { difficulty: "Expert" })]);
    renderApp("/maps/id0000000001");
    expect(await screen.findByRole("heading", { name: "Song 1" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "2 errors" })).toBeInTheDocument();
    expect(screen.getByText(/3:21/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Expert+" })).toBeInTheDocument();
    expect(await screen.findByText("Fix 1")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Hard" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Expert" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Library/ })[0]).toHaveAttribute("href", "/");
  });

  test("approving a proposal posts and disables that button", async () => {
    const { posts } = mapApi([proposal(1)]);
    renderApp("/maps/id0000000001");
    const user = userEvent.setup();
    const card = (await screen.findByText("Fix 1")).closest("article") as HTMLElement;
    await user.click(within(card).getByRole("button", { name: "Approve" }));
    await waitFor(() => expect(posts).toContain("/api/proposals/1/approve"));
    await waitFor(() =>
      expect(within(card).getByRole("button", { name: "Approve" })).toBeDisabled(),
    );
    await waitFor(() => expect(within(card).getByRole("button", { name: "Reject" })).toHaveFocus());
  });

  test("Approve all asks for confirmation first", async () => {
    const { posts } = mapApi([proposal(1)]);
    renderApp("/maps/id0000000001");
    const user = userEvent.setup();
    await screen.findByText("Fix 1");
    await user.click(screen.getByRole("button", { name: "Approve all" }));
    const dialog = await screen.findByRole("dialog");
    expect(posts).toEqual([]);
    await user.click(within(dialog).getByRole("button", { name: "Approve all" }));
    await waitFor(() => expect(posts).toContain("/api/maps/id0000000001/approve-all"));
  });

  test("unknown map shows a not found page", async () => {
    mapApi([]);
    renderApp("/maps/missing0000");
    expect(await screen.findByRole("heading", { name: "Map not found" })).toBeInTheDocument();
  });

  test("unknown path shows the 404 page", async () => {
    mapApi([]);
    renderApp("/nope/at/all");
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });

  test("generate page requires a URL or a file, then runs the job", async () => {
    const { posts } = mapApi([]);
    renderApp("/new");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Generate" }));
    expect(
      await screen.findByText("Paste a YouTube link or drop an audio file."),
    ).toBeInTheDocument();
    await user.type(screen.getByLabelText("YouTube URL"), "https://youtu.be/abc");
    await user.click(screen.getByRole("button", { name: "Generate" }));
    await waitFor(() => expect(posts).toContain("/api/generate"));
  });

  test("the map page links back to the library with its filters", async () => {
    mapApi([]);
    const { router } = renderApp("/?status=error");
    await screen.findByText("No maps match these filters");
    await router.navigate("/maps/id0000000001");
    const main = within(screen.getByRole("main"));
    await waitFor(() =>
      expect(main.getByRole("link", { name: "Back to list" })).toHaveAttribute(
        "href",
        "/?status=error",
      ),
    );
  });
});
