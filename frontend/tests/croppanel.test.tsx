import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { CropPanel } from "../src/components/CropPanel";
import { TIMELINE, cropApi, endHandle, renderPanel, startHandle } from "./crophelpers";
import { inlineText, toasts } from "./helpers";

const P120 = TIMELINE.lengths["120"];

async function openPanel(_user?: ReturnType<typeof userEvent.setup>) {
  await screen.findByRole("slider", { name: "Crop end" });
}

function setup(options = {}, busy = false) {
  const api = cropApi(options);
  renderPanel(<CropPanel mapId="id0000000001" folder="Folder 1" busy={busy} />);
  return { ...api, user: userEvent.setup() };
}

describe("CropPanel", () => {
  test("fetches the timeline once when mounted and shows the chart", async () => {
    const { calls } = setup();
    await screen.findByRole("slider", { name: "Crop start" });
    expect(calls.filter((u) => u.pathname.endsWith("/timeline"))).toHaveLength(1);
  });

  test("shows a skeleton while the timeline loads", async () => {
    const slow = new Promise((resolve) => setTimeout(() => resolve(TIMELINE), 100));
    setup({ timeline: slow });
    expect(document.querySelector("[data-skeleton]")).not.toBeNull();
    await screen.findByRole("slider", { name: "Crop end" });
    expect(document.querySelector("[data-skeleton]")).toBeNull();
  });

  test("opens on the suggestion without any length or boundary text", async () => {
    const { user } = setup();
    await openPanel(user);
    expect(startHandle()).toHaveAttribute("aria-valuenow", "0");
    expect(endHandle()).toHaveAttribute("aria-valuenow", "64");
    expect(screen.queryByText(/Length \d/)).toBeNull();
    expect(screen.queryByText(/section boundar/)).toBeNull();
    expect(document.querySelector(".crop-readout, .crop-amber")).toBeNull();
    expect(screen.getByRole("button", { name: "Save as new map" })).toBeEnabled();
  });

  test("the length switch has Auto, 1 min, 2 min and Custom in the section-tab pill style", async () => {
    const { user } = setup();
    await openPanel(user);
    const group = screen.getByRole("radiogroup", { name: "Crop length" });
    expect(group).toHaveClass("mode-switch");
    expect(
      within(group)
        .getAllByRole("radio")
        .map((r) => r.textContent),
    ).toEqual(["Auto", "1 min", "2 min", "Custom"]);
    expect(screen.getByRole("radio", { name: "Auto" })).toBeChecked();
  });

  test("Save as new map and Reset to suggestion sit on the length row, to its right", async () => {
    const { user } = setup();
    await openPanel(user);
    startHandle().focus();
    await user.keyboard("{ArrowRight}");
    const group = screen.getByRole("radiogroup", { name: "Crop length" });
    const save = screen.getByRole("button", { name: "Save as new map" });
    const reset = screen.getByRole("button", { name: /Reset to suggestion/ });
    const row = group.closest(".crop-bar") as HTMLElement;
    expect(row).not.toBeNull();
    for (const button of [save, reset]) {
      expect(row).toContainElement(button);
      expect(group.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });

  test("arrow keys nudge a handle 0.1 s and Shift 1 s, and the end is not re-picked", async () => {
    const { user, posts } = setup();
    await openPanel(user);
    endHandle().focus();
    await user.keyboard("{ArrowLeft}");
    expect(endHandle()).toHaveAttribute("aria-valuetext", "1:03.9");
    await user.keyboard("{Shift>}{ArrowRight}{/Shift}");
    expect(endHandle()).toHaveAttribute("aria-valuetext", "1:04.9");
    startHandle().focus();
    await user.keyboard("{ArrowRight}");
    expect(startHandle()).toHaveAttribute("aria-valuetext", "0:00.1");
    expect(endHandle()).toHaveAttribute("aria-valuetext", "1:04.9");
    await user.click(screen.getByRole("button", { name: "Save as new map" }));
    await waitFor(() => expect(posts).toHaveLength(1));
    const body = posts[0]?.body as { start_s: number; end_s: number };
    expect(Object.keys(body).sort()).toEqual(["end_s", "start_s"]);
    expect(body.start_s).toBeCloseTo(0.1, 6);
    expect(body.end_s).toBeCloseTo(64.9, 6);
  });

  test("Reset to suggestion appears after an edit and restores the suggestion", async () => {
    const { user } = setup();
    await openPanel(user);
    expect(screen.queryByRole("button", { name: /Reset to suggestion/ })).toBeNull();
    endHandle().focus();
    await user.keyboard("{ArrowLeft}");
    await user.click(screen.getByRole("button", { name: /Reset to suggestion/ }));
    expect(endHandle()).toHaveAttribute("aria-valuenow", "64");
    expect(screen.queryByRole("button", { name: /Reset to suggestion/ })).toBeNull();
  });

  test("Custom keeps the current window", async () => {
    const { user, posts } = setup();
    await openPanel(user);
    endHandle().focus();
    await user.keyboard("{Shift>}{ArrowLeft}{/Shift}");
    await user.click(screen.getByRole("radio", { name: "Custom" }));
    expect(screen.getByRole("radio", { name: "Custom" })).toBeChecked();
    expect(startHandle()).toHaveAttribute("aria-valuenow", "0");
    expect(endHandle()).toHaveAttribute("aria-valuenow", "63");
    endHandle().focus();
    await user.keyboard("{Shift>}{ArrowRight}{ArrowRight}{/Shift}");
    expect(endHandle()).toHaveAttribute("aria-valuenow", "65");
    await user.click(screen.getByRole("button", { name: "Save as new map" }));
    await waitFor(() => expect(posts[0]?.body).toEqual({ start_s: 0, end_s: 65 }));
  });

  test("Custom with no suggestion keeps the shown window", async () => {
    const off = (reason: string) => ({ ...P120, enabled: false, reason });
    const none = { ...TIMELINE, lengths: { "60": off("short"), "120": off("short") } };
    const { user, posts } = setup({ timeline: none });
    await openPanel(user);
    await user.click(screen.getByRole("radio", { name: "Custom" }));
    expect(screen.getByRole("radio", { name: "Custom" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Custom" })).toBeEnabled();
    expect(startHandle()).toHaveAttribute("aria-valuenow", "0");
    expect(endHandle()).toHaveAttribute("aria-valuenow", "64");
    await user.click(screen.getByRole("button", { name: "Save as new map" }));
    await waitFor(() => expect(posts[0]?.body).toEqual({ start_s: 0, end_s: 64 }));
  });

  test("going from Custom to a length picks that length's suggestion", async () => {
    const { user } = setup();
    await openPanel(user);
    await user.click(screen.getByRole("radio", { name: "Custom" }));
    await user.click(screen.getByRole("radio", { name: "2 min" }));
    expect(startHandle()).toHaveAttribute("aria-valuenow", "0");
    expect(endHandle()).toHaveAttribute("aria-valuenow", "112");
  });

  test("switching to 2 min keeps the start when it exists and re-picks the end", async () => {
    const { user } = setup();
    await openPanel(user);
    await user.click(screen.getByRole("radio", { name: "2 min" }));
    expect(screen.getByRole("radio", { name: "2 min" })).toBeChecked();
    expect(endHandle()).toHaveAttribute("aria-valuenow", "112");
    expect(screen.queryByRole("button", { name: /Reset to suggestion/ })).toBeNull();
  });

  test("switching to a length without the chosen start falls back to its suggestion", async () => {
    const { user } = setup();
    await openPanel(user);
    startHandle().focus();
    await user.keyboard("{ArrowRight}");
    await user.click(screen.getByRole("radio", { name: "2 min" }));
    expect(startHandle()).toHaveAttribute("aria-valuenow", "0");
    expect(endHandle()).toHaveAttribute("aria-valuenow", "112");
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
    setup({ timeline: failing });
    expect(await screen.findByText("Could not build the crop timeline")).toBeInTheDocument();
    expect(screen.getByText(/no Standard difficulty has notes/)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Crop to a highlight" })).toBeInTheDocument();
  });

  test("a finished job links to the new folder", async () => {
    const { user } = setup();
    await openPanel(user);
    await user.click(screen.getByRole("button", { name: "Save as new map" }));
    const link = await toasts().findByRole("link", { name: "Open cropped map" });
    expect(link).toHaveAttribute("href", "/maps/id0000000099");
    expect(toasts().getByText(/Written to Folder 1 \[1 min\]/)).toBeInTheDocument();
    expect(inlineText(/Written to Folder 1/)).toBe(false);
  });

  test("a failed job shows the reason", async () => {
    const { user } = setup({ jobStatus: "failed", jobError: "ffmpeg failed: bad input" });
    await openPanel(user);
    await user.click(screen.getByRole("button", { name: "Save as new map" }));
    expect(await toasts().findByText("Crop failed")).toBeInTheDocument();
    expect(toasts().getAllByText(/ffmpeg failed: bad input/).length).toBeGreaterThan(0);
    expect(inlineText("Crop failed")).toBe(false);
  });

  test("Create is disabled while a job runs on the map", async () => {
    const { user } = setup({}, true);
    await openPanel(user);
    expect(screen.getByRole("button", { name: "Save as new map" })).toBeDisabled();
  });
});
