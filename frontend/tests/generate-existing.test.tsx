import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { mockFetch, renderApp } from "./helpers";

const LINK = "https://www.youtube.com/watch?v=rDQGieROK_w";

const conflict = (fields: Record<string, string>, error: string) =>
  new Response(JSON.stringify({ error, ...fields }), {
    status: 409,
    headers: { "Content-Type": "application/json" },
  });

async function submit() {
  renderApp("/new");
  const user = userEvent.setup();
  await user.type(await screen.findByLabelText("YouTube URL"), LINK);
  await user.click(screen.getByRole("button", { name: "Generate" }));
}

describe("generate: a song that is already there", () => {
  test("already being imported shows the message and an Open job link, no toast", async () => {
    mockFetch((_url, init) =>
      init?.method === "POST"
        ? conflict({ job: "j9" }, "already being imported")
        : { items: [], total: 0, offset: 0, limit: 40 },
    );
    await submit();
    expect(await screen.findByText("already being imported")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open job" })).toHaveAttribute("href", "/jobs");
    expect(screen.queryByRole("list")).toBeNull();
    expect(document.querySelector(".toast")).toBeNull();
    expect(screen.getByRole("button", { name: "Generate" })).toBeEnabled();
  });

  test("already imported shows an Open map link", async () => {
    mockFetch((_url, init) =>
      init?.method === "POST"
        ? conflict({ map_id: "id0000000001" }, "already imported")
        : { items: [], total: 0, offset: 0, limit: 40 },
    );
    await submit();
    expect(await screen.findByText("already imported")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open map" })).toHaveAttribute(
      "href",
      "/maps/id0000000001",
    );
  });

  test("the song title from the server replaces the link on the card", async () => {
    mockFetch((url, init) => {
      if (init?.method === "POST") return { job: "j1" };
      if (url.pathname === "/api/jobs/j1") {
        return {
          id: "j1",
          kind: "generate",
          status: "queued",
          position: 1,
          error: null,
          title: "Artist - Song",
        };
      }
      return { items: [], total: 0, offset: 0, limit: 40 };
    });
    await submit();
    expect(await screen.findByText("Artist - Song")).toBeInTheDocument();
  });
});
