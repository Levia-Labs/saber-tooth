import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test } from "vitest";
import { item, mockFetch, renderApp } from "./helpers";

const SEARCH_KEY = "saber-tooth.library-search";
const ref = (n: number, title = `Song ${n}`) => ({
  id: `id${String(n).padStart(10, "0")}`,
  title,
  folder: `Folder ${n}`,
});

function api(neighbors: (url: URL) => unknown) {
  return mockFetch((url) => {
    if (url.pathname.endsWith("/neighbors")) return neighbors(url);
    if (url.pathname === "/api/maps/id0000000002") return item(2);
    if (url.pathname.endsWith("/proposals")) return [];
    return { items: [], total: 0, offset: 0, limit: 40 };
  });
}

const fail = (status: number) =>
  new Response(JSON.stringify({ error: "nope" }), {
    status,
    headers: { "Content-Type": "application/json" },
  });

const neighborCalls = (calls: URL[]) => calls.filter((u) => u.pathname.endsWith("/neighbors"));

beforeEach(() => sessionStorage.clear());
afterEach(() => sessionStorage.clear());

describe("map page footer", () => {
  test("shows the previous and next titles as links and the position", async () => {
    api(() => ({ index: 2, total: 7, prev: ref(1), next: ref(3) }));
    renderApp("/maps/id0000000002");
    const prev = await screen.findByRole("link", { name: /Song 1/ });
    const next = screen.getByRole("link", { name: /Song 3/ });
    expect(prev).toHaveAttribute("href", "/maps/id0000000001");
    expect(prev).toHaveClass("back");
    expect(next).toHaveAttribute("href", "/maps/id0000000003");
    expect(next).toHaveClass("back");
    expect(screen.getByText("2 / 7")).toBeInTheDocument();
  });

  test("wraps: the first map shows the last as previous", async () => {
    api(() => ({ index: 1, total: 3, prev: ref(3), next: ref(2) }));
    renderApp("/maps/id0000000002");
    const prev = await screen.findByRole("link", { name: /Song 3/ });
    expect(prev).toHaveAttribute("href", "/maps/id0000000003");
    expect(screen.getByText("1 / 3")).toBeInTheDocument();
  });

  test("wraps: the last map shows the first as next", async () => {
    api(() => ({ index: 3, total: 3, prev: ref(2), next: ref(1) }));
    renderApp("/maps/id0000000002");
    const next = await screen.findByRole("link", { name: /Song 1/ });
    expect(next).toHaveAttribute("href", "/maps/id0000000001");
    expect(screen.getByText("3 / 3")).toBeInTheDocument();
  });

  test("long titles keep the full text in a tooltip and truncate by CSS", async () => {
    const long = "L".repeat(120);
    api(() => ({ index: 2, total: 3, prev: ref(1, long), next: ref(3) }));
    renderApp("/maps/id0000000002");
    const prev = await screen.findByRole("link", { name: new RegExp(long) });
    expect(prev).toHaveAttribute("title", long);
    expect(prev.querySelector(".map-footer-title")).not.toBeNull();
  });

  test("passes the stored library query", async () => {
    sessionStorage.setItem(SEARCH_KEY, "q=song&sort=bpm&order=desc&status=error");
    const { calls } = api(() => ({ index: 1, total: 1, prev: ref(1), next: ref(1) }));
    renderApp("/maps/id0000000002");
    await screen.findByText("1 / 1");
    const url = neighborCalls(calls)[0] as URL;
    expect(url.searchParams.get("q")).toBe("song");
    expect(url.searchParams.get("sort")).toBe("bpm");
    expect(url.searchParams.get("order")).toBe("desc");
    expect(url.searchParams.get("status")).toBe("error");
    expect(url.searchParams.has("offset")).toBe(false);
  });

  test("uses the default order when nothing is stored", async () => {
    const { calls } = api(() => ({ index: 1, total: 1, prev: ref(1), next: ref(1) }));
    renderApp("/maps/id0000000002");
    await screen.findByText("1 / 1");
    expect(neighborCalls(calls)[0]?.search).toBe("");
  });

  test("a 404 with filters retries once without them", async () => {
    sessionStorage.setItem(SEARCH_KEY, "q=zzz");
    const { calls } = api((url) =>
      url.searchParams.has("q") ? fail(404) : { index: 2, total: 5, prev: ref(1), next: ref(3) },
    );
    renderApp("/maps/id0000000002");
    expect(await screen.findByText("2 / 5")).toBeInTheDocument();
    const sent = neighborCalls(calls);
    expect(sent).toHaveLength(2);
    expect(sent[1]?.search).toBe("");
  });

  test("a failed request hides the footer", async () => {
    const { calls } = api(() => fail(500));
    renderApp("/maps/id0000000002");
    await waitFor(() => expect(neighborCalls(calls)).toHaveLength(1));
    await screen.findByRole("heading", { level: 1 });
    expect(document.querySelector(".map-footer")).toBeNull();
  });

  test("a 404 without filters hides the footer", async () => {
    const { calls } = api(() => fail(404));
    renderApp("/maps/id0000000002");
    await waitFor(() => expect(neighborCalls(calls)).toHaveLength(1));
    await screen.findByRole("heading", { level: 1 });
    expect(document.querySelector(".map-footer")).toBeNull();
  });
});
