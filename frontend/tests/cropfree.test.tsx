import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { CropPanel } from "../src/components/CropPanel";
import { TIMELINE, chartSvg, cropApi, endHandle, renderPanel, startHandle } from "./crophelpers";

async function openPanel() {
  await screen.findByRole("slider", { name: "Crop end" });
}

function setup(options = {}) {
  const api = cropApi(options);
  renderPanel(<CropPanel mapId="id0000000001" folder="Folder 1" busy={false} />);
  return { ...api, user: userEvent.setup() };
}

describe("free cutting", () => {
  test("dragging a handle moves it continuously, not to a section or suggestion", async () => {
    setup();
    await openPanel();
    const svg = chartSvg();
    fireEvent.pointerDown(startHandle(), { pointerId: 1 });
    fireEvent.pointerMove(svg, { clientX: 123 });
    expect(startHandle()).toHaveAttribute("aria-valuetext", "0:17.2");
    fireEvent.pointerMove(svg, { clientX: 124 });
    expect(startHandle()).toHaveAttribute("aria-valuetext", "0:17.4");
    fireEvent.pointerUp(svg);
    fireEvent.pointerDown(endHandle(), { pointerId: 1 });
    fireEvent.pointerMove(svg, { clientX: 777 });
    expect(endHandle()).toHaveAttribute("aria-valuetext", "1:48.8");
    fireEvent.pointerUp(svg);
    expect(screen.getByRole("button", { name: /Reset to suggestion/ })).toBeInTheDocument();
  });

  test("a handle stops 1 s from the other one and at the song edges", async () => {
    setup();
    await openPanel();
    const svg = chartSvg();
    fireEvent.pointerDown(endHandle(), { pointerId: 1 });
    fireEvent.pointerMove(svg, { clientX: 0 });
    expect(endHandle()).toHaveAttribute("aria-valuenow", "1");
    fireEvent.pointerMove(svg, { clientX: 5000 });
    expect(endHandle()).toHaveAttribute("aria-valuenow", "140");
    fireEvent.pointerUp(svg);
    fireEvent.pointerDown(startHandle(), { pointerId: 1 });
    fireEvent.pointerMove(svg, { clientX: 1000 });
    expect(startHandle()).toHaveAttribute("aria-valuenow", "139");
    fireEvent.pointerMove(svg, { clientX: -50 });
    expect(startHandle()).toHaveAttribute("aria-valuenow", "0");
  });

  test("the minimum length comes from the timeline", async () => {
    setup({ timeline: { ...TIMELINE, min_length_s: 5 } });
    await openPanel();
    fireEvent.pointerDown(endHandle(), { pointerId: 1 });
    fireEvent.pointerMove(chartSvg(), { clientX: 0 });
    expect(endHandle()).toHaveAttribute("aria-valuenow", "5");
  });

  test("a window nudged to the minimum cannot get shorter", async () => {
    const { user } = setup({ timeline: { ...TIMELINE, min_length_s: 62 } });
    await openPanel();
    endHandle().focus();
    await user.keyboard("{Shift>}{ArrowLeft}{ArrowLeft}{ArrowLeft}{/Shift}");
    expect(endHandle()).toHaveAttribute("aria-valuenow", "62");
  });

  test("dragging the whole window is free and Save posts where it was dropped", async () => {
    const { user, posts } = setup();
    await openPanel();
    const svg = chartSvg();
    fireEvent.pointerDown(document.querySelector(".nps-selection") as Element, {
      pointerId: 1,
      clientX: 100,
    });
    fireEvent.pointerMove(svg, { clientX: 600 });
    fireEvent.pointerUp(svg);
    expect(startHandle()).toHaveAttribute("aria-valuenow", "70");
    expect(endHandle()).toHaveAttribute("aria-valuenow", "134");
    await user.click(screen.getByRole("button", { name: "Save as new map" }));
    await waitFor(() => expect(posts[0]?.body).toEqual({ start_s: 70, end_s: 134 }));
  });

  test("double-clicking a section moves the window there, keeping its length", async () => {
    const { user } = setup();
    await openPanel();
    endHandle().focus();
    await user.keyboard("{ArrowLeft}");
    fireEvent.doubleClick(chartSvg(), { clientX: 700 });
    expect(startHandle()).toHaveAttribute("aria-valuenow", "64");
    expect(endHandle()).toHaveAttribute("aria-valuenow", "127.9");
    fireEvent.doubleClick(chartSvg(), { clientX: 50 });
    expect(startHandle()).toHaveAttribute("aria-valuenow", "0");
    expect(endHandle()).toHaveAttribute("aria-valuenow", "63.9");
  });

  test("there are no Move selection arrows", async () => {
    setup();
    await openPanel();
    expect(screen.queryByRole("button", { name: /Move selection/ })).toBeNull();
  });
});
