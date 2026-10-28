import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { FACETS, item, mockFetch, renderApp } from "./helpers";

const MAP = "id0000000001";

interface Posted {
  path: string;
  body: unknown;
}

function api(
  job: Record<string, unknown> = { status: "done", result: { map_id: MAP, folder: "st-x" } },
) {
  const posts: Posted[] = [];
  let polls = 0;
  mockFetch((url, init) => {
    if (init?.method === "POST") {
      posts.push({ path: url.pathname, body: init.body });
      return { job: "j1" };
    }
    if (url.pathname === "/api/jobs/j1") {
      polls += 1;
      const state =
        polls === 1 && job["status"] === "done" ? { status: "running", result: null } : job;
      return { id: "j1", kind: "generate", error: null, ...state };
    }
    if (url.pathname === "/api/maps/facets") return FACETS;
    if (url.pathname === `/api/maps/${MAP}`) return item(1);
    if (url.pathname === `/api/maps/${MAP}/proposals`) return [];
    return { items: [], total: 0, offset: 0, limit: 40 };
  });
  return posts;
}

const audio = (name = "song.mp3", type = "audio/mpeg") => new File(["x"], name, { type });

describe("generate card", () => {
  test("has a link field, a drop zone and one Generate button, no proposal step", async () => {
    api();
    renderApp("/new");
    expect(await screen.findByLabelText("YouTube URL")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Drop an audio file/ })).toBeInTheDocument();
    expect(screen.getByText(/Audio only: mp3/)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Generate" })).toHaveLength(1);
    expect(screen.queryByText(/Write map folder/)).toBeNull();
  });

  test("a pasted link starts one job, shows progress, then opens the finished map", async () => {
    const posts = api();
    const { router } = renderApp("/new");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("YouTube URL"), "https://youtu.be/abc");
    await user.click(screen.getByRole("button", { name: "Generate" }));
    expect(await screen.findByText("Generating https://youtu.be/abc")).toBeInTheDocument();
    await waitFor(() => expect(router.state.location.pathname).toBe(`/maps/${MAP}`), {
      timeout: 4000,
    });
    expect(posts).toHaveLength(1);
    expect(posts[0]).toEqual({
      path: "/api/generate",
      body: JSON.stringify({ url: "https://youtu.be/abc" }),
    });
    const open = await screen.findByRole("link", { name: "Open map" });
    expect(open).toHaveAttribute("href", `/maps/${MAP}`);
    expect(screen.getByText("st-x")).toBeInTheDocument();
  });

  test("a dropped audio file is shown, uploaded as multipart and replaces the link", async () => {
    const posts = api();
    renderApp("/new");
    const zone = await screen.findByRole("button", { name: /Drop an audio file/ });
    fireEvent.dragOver(zone);
    expect(zone).toHaveAttribute("data-over", "true");
    fireEvent.drop(zone, { dataTransfer: { files: [audio("my song.mp3")] } });
    expect(await screen.findByText("my song.mp3")).toBeInTheDocument();
    expect(zone).toHaveAttribute("data-over", "false");
    await userEvent.setup().click(screen.getByRole("button", { name: "Generate" }));
    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0]?.body).toBeInstanceOf(FormData);
    expect((posts[0]?.body as FormData).get("file")).toBeInstanceOf(File);
  });

  test("the picker is reachable by keyboard and a non-audio file is refused", async () => {
    api();
    renderApp("/new");
    const zone = await screen.findByRole("button", { name: /Drop an audio file/ });
    zone.focus();
    expect(zone).toHaveFocus();
    const input = screen.getByLabelText("Audio file");
    fireEvent.change(input, { target: { files: [audio("notes.txt", "text/plain")] } });
    expect(await screen.findByText(/notes.txt is not an audio file/)).toBeInTheDocument();
    fireEvent.change(input, { target: { files: [audio("ok.flac", "")] } });
    expect(await screen.findByText("ok.flac")).toBeInTheDocument();
  });

  test("nothing, or something that is not a link, warns and posts nothing", async () => {
    const posts = api();
    renderApp("/new");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Generate" }));
    expect(
      await screen.findByText("Paste a YouTube link or drop an audio file."),
    ).toBeInTheDocument();
    await user.type(screen.getByLabelText("YouTube URL"), "not a link");
    await user.click(screen.getByRole("button", { name: "Generate" }));
    expect(screen.queryByText("Paste a YouTube link or drop an audio file.")).toBeNull();
    expect(posts).toHaveLength(0);
  });

  test("a failed job shows the reason in a danger toast and stays on the page", async () => {
    api({ status: "failed", error: "beat-analyser unreachable", result: null });
    const { router } = renderApp("/new");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("YouTube URL"), "https://youtu.be/abc");
    await user.click(screen.getByRole("button", { name: "Generate" }));
    const toast = await screen.findByText("beat-analyser unreachable");
    expect(
      within(toast.closest(".toast") as HTMLElement).getByText(/Generation failed/),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/new");
    expect(screen.queryByText(/Generating/)).toBeNull();
  });
});
