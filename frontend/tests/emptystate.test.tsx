import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { EmptyState } from "../src/components/EmptyState";
import { mockFetch, renderApp } from "./helpers";
import { bsApi, page } from "./bshelpers";

/** The empty state with its icon, its text and (when asked) its action. */
async function emptyState(text: string) {
  const el = (await screen.findByText(text)).closest("[data-empty-state]");
  expect(el, text).not.toBeNull();
  expect(el!.querySelector("svg.empty-state-icon")).not.toBeNull();
  return el!;
}

describe("EmptyState", () => {
  test("renders icon above text, then the action", () => {
    const { container } = render(
      <EmptyState icon="queue" text="Nothing here" action={<button type="button">Go</button>} />,
    );
    const kids = [...container.querySelector(".empty-state")!.children].map((c) => c.tagName);
    expect(kids).toEqual(["svg", "P", "BUTTON"]);
  });
});

test("pending swaps icon and text for the animated spinner", () => {
  const { container } = render(<EmptyState icon="playlist" text="None" pending="Loading x" />);
  expect(screen.getByRole("status", { name: "Loading x" })).toBeInTheDocument();
  expect(container.textContent).toBe("");
});

describe("each empty table uses it", () => {
  test("library, filtered and unfiltered", async () => {
    mockFetch(() => ({ items: [], total: 0, facets: {}, next_cursor: null }));
    renderApp("/?status=error");
    const el = await emptyState("No maps match these filters");
    expect(el.querySelector("button")).toHaveTextContent("Clear filters");
  });

  test("library unfiltered carries the hint", async () => {
    mockFetch(() => ({ items: [], total: 0, facets: {}, next_cursor: null }));
    renderApp("/");
    const el = await emptyState("No maps found");
    expect(el.querySelector(".empty-state-hint")).toHaveTextContent(/Add map folders/);
  });

  test("playlists", async () => {
    mockFetch((url) => (url.pathname === "/api/playlists" ? { items: [] } : {}));
    renderApp("/playlists");
    await emptyState("No playlists yet.");
  });

  test("playlist songs", async () => {
    mockFetch((url) =>
      url.pathname === "/api/playlists/p1"
        ? {
            id: "p1",
            title: "Chill",
            author: "me",
            description: "",
            folder: "",
            sync: false,
            sync_url: "http://localhost/api/playlists/p1/bplist",
            exported: "",
            updated_at: "t",
            songs_count: 0,
            missing_count: 0,
            cover_url: null,
            songs: [],
          }
        : {},
    );
    renderApp("/playlists/p1");
    const el = await emptyState("No songs yet.");
    expect(el.querySelector(".empty-state-hint")).toHaveTextContent(/Add songs/);
  });

  test("jobs", async () => {
    mockFetch(() => ({ running: [], queued: [], recent: [] }));
    renderApp("/jobs");
    await emptyState("Nothing running or queued.");
  });

  test("BeatSaver maps", async () => {
    bsApi({ search: () => page([]) });
    renderApp("/beatsaver");
    await emptyState("No maps found.");
  });
});
