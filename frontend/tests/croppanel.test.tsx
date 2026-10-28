import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { CropPanel } from "../src/components/CropPanel";
import { TIMELINE, cropApi, renderPanel } from "./crophelpers";

const P120 = TIMELINE.lengths["120"];

async function openPanel(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: /Crop to 1 or 2 minutes/ }));
  await screen.findByRole("slider", { name: "Crop end" });
}

function setup(options = {}, busy = false) {
  const api = cropApi(options);
  renderPanel(<CropPanel mapId="id0000000001" busy={busy} />);
  return { ...api, user: userEvent.setup() };
}

describe("CropPanel", () => {
  test("stays closed, and fetches nothing, until it is opened", async () => {
    const { calls, user } = setup();
    const toggle = screen.getByRole("button", { name: /Crop to 1 or 2 minutes/ });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(calls.some((u) => u.pathname.endsWith("/timeline"))).toBe(false);
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    await screen.findByRole("slider", { name: "Crop start" });
  });

  test("shows a skeleton while the timeline loads", async () => {
    const slow = new Promise((resolve) => setTimeout(() => resolve(TIMELINE), 100));
    const { user } = setup({ timeline: slow });
    await user.click(screen.getByRole("button", { name: /Crop to 1 or 2 minutes/ }));
    expect(document.querySelector("[data-skeleton]")).not.toBeNull();
    await screen.findByRole("slider", { name: "Crop end" });
    expect(document.querySelector("[data-skeleton]")).toBeNull();
  });

  test("opens on the suggestion with its exact length", async () => {
    const { user } = setup();
    await openPanel(user);
    const readout = screen.getByText(/^Length 1:04\.0/);
    expect(readout).not.toHaveClass("crop-amber");
    expect(readout).toHaveTextContent("Both cuts are on section boundaries.");
    expect(screen.getByRole("button", { name: "Create cropped map" })).toBeEnabled();
  });

  test("the end steps to allowed points and the readout turns amber off a section end", async () => {
    const { user } = setup();
    await openPanel(user);
    screen.getByRole("slider", { name: "Crop end" }).focus();
    await user.keyboard("{ArrowLeft}");
    const readout = screen.getByText(/^Length 0:58\.0/);
    expect(readout).toHaveClass("crop-amber");
    expect(readout).toHaveTextContent("Ends on a bar line, not a section boundary.");
    await user.keyboard("{Shift>}{ArrowRight}{/Shift}");
    expect(screen.getByText(/^Length 1:04\.0/)).not.toHaveClass("crop-amber");
  });

  test("moving the start re-picks the end and Create posts the chosen beats", async () => {
    const { user, posts } = setup();
    await openPanel(user);
    screen.getByRole("slider", { name: "Crop start" }).focus();
    await user.keyboard("{ArrowRight}");
    const readout = screen.getByText(/^Length 1:04\.0/);
    expect(readout).toHaveTextContent("Ends on a phrase line, not a section boundary.");
    await user.click(screen.getByRole("button", { name: "Create cropped map" }));
    await waitFor(() =>
      expect(posts).toEqual([
        { path: "/api/maps/id0000000001/crop", body: { start_beat: 128, end_beat: 256 } },
      ]),
    );
  });

  test("Reset to suggestion appears after an edit and restores the suggestion", async () => {
    const { user } = setup();
    await openPanel(user);
    expect(screen.queryByRole("button", { name: /Reset to suggestion/ })).toBeNull();
    screen.getByRole("slider", { name: "Crop end" }).focus();
    await user.keyboard("{ArrowLeft}");
    await user.click(screen.getByRole("button", { name: /Reset to suggestion/ }));
    expect(screen.getByText(/^Length 1:04\.0/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Reset to suggestion/ })).toBeNull();
  });

  test("switching to 2 min keeps the start when it exists and re-picks the end", async () => {
    const { user } = setup();
    await openPanel(user);
    await user.click(screen.getByRole("radio", { name: "2 min" }));
    expect(screen.getByRole("radio", { name: "2 min" })).toBeChecked();
    expect(screen.getByText(/^Length 1:52\.0/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Reset to suggestion/ })).toBeNull();
  });

  test("switching to a length without the chosen start falls back to its suggestion", async () => {
    const { user } = setup();
    await openPanel(user);
    screen.getByRole("slider", { name: "Crop start" }).focus();
    await user.keyboard("{ArrowRight}");
    await user.click(screen.getByRole("radio", { name: "2 min" }));
    expect(screen.getByText(/^Length 1:52\.0/)).toBeInTheDocument();
  });

  test("a map without analysis says its sections come from the map only", async () => {
    const { user } = setup({ timeline: { ...TIMELINE, map_only: true } });
    await openPanel(user);
    expect(screen.getByText("Sections from map only")).toBeInTheDocument();
  });

  test("a length the song is too short for is disabled with the reason", async () => {
    const reason = "The song is 90 s long; a 2 min crop needs at least 132 s.";
    const short = {
      ...TIMELINE,
      lengths: { ...TIMELINE.lengths, "120": { ...P120, enabled: false, reason } },
    };
    const { user } = setup({ timeline: short });
    await openPanel(user);
    expect(screen.getByRole("radio", { name: "2 min" })).toBeDisabled();
    expect(screen.getByText(reason)).toBeInTheDocument();
  });

  test("a timeline that cannot be built shows a danger alert and nothing else breaks", async () => {
    const failing = new Response(JSON.stringify({ error: "no Standard difficulty has notes" }), {
      status: 422,
      headers: { "Content-Type": "application/json" },
    });
    const { user } = setup({ timeline: failing });
    await user.click(screen.getByRole("button", { name: /Crop to 1 or 2 minutes/ }));
    expect(await screen.findByText("Could not build the crop timeline")).toBeInTheDocument();
    expect(screen.getByText(/no Standard difficulty has notes/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Crop to 1 or 2 minutes/ })).toBeEnabled();
  });

  test("a finished job links to the new folder", async () => {
    const { user } = setup();
    await openPanel(user);
    await user.click(screen.getByRole("button", { name: "Create cropped map" }));
    const link = await screen.findByRole("link", { name: "Open cropped map" });
    expect(link).toHaveAttribute("href", "/maps/id0000000099");
    expect(screen.getByText(/Written to Folder 1 \[1 min\]/)).toBeInTheDocument();
  });

  test("a failed job shows the reason", async () => {
    const { user } = setup({ jobStatus: "failed", jobError: "ffmpeg failed: bad input" });
    await openPanel(user);
    await user.click(screen.getByRole("button", { name: "Create cropped map" }));
    expect(await screen.findByText("Crop failed")).toBeInTheDocument();
    expect(screen.getAllByText(/ffmpeg failed: bad input/).length).toBeGreaterThan(0);
  });

  test("Create is disabled while a job runs on the map", async () => {
    const { user } = setup({}, true);
    await openPanel(user);
    expect(screen.getByRole("button", { name: "Create cropped map" })).toBeDisabled();
  });
});
