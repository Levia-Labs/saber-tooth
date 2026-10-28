import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { NpsChart } from "../src/components/NpsChart";
import { levelColor } from "../src/lib/levels";
import { togglePreview } from "../src/lib/previewPlayer";
import { TIMELINE } from "./crophelpers";

const audio = new (class extends EventTarget {
  src = "";
  paused = true;
  duration = 200;
  currentTime = 0;
  pause() {
    this.paused = true;
  }
  play() {
    this.paused = false;
    return Promise.resolve();
  }
})();
// The setup file unstubs globals after each test, so stub before each.
beforeEach(() => {
  vi.stubGlobal("Audio", function () {
    return audio;
  });
});

type Props = Parameters<typeof NpsChart>[0];

function chart(patch: Partial<Props> = {}) {
  const fns = {
    onMove: vi.fn(),
    onStep: vi.fn(),
    onShift: vi.fn(),
    onJump: vi.fn(),
    onShiftStep: vi.fn(),
  };
  const view = render(
    <NpsChart
      nps={TIMELINE.nps}
      hardest="ExpertPlus"
      sections={TIMELINE.sections}
      duration={TIMELINE.duration_s}
      selection={{ start_s: 0, end_s: 64 }}
      faint={[]}
      endMarks={[]}
      canShift={{ earlier: true, later: true }}
      audioUrl="/api/maps/x/audio"
      {...fns}
      {...patch}
    />,
  );
  const svg = view.container.querySelector("svg") as SVGSVGElement;
  vi.spyOn(svg, "getBoundingClientRect").mockReturnValue({
    left: 0,
    top: 0,
    right: 1000,
    bottom: 160,
    width: 1000,
    height: 160,
    x: 0,
    y: 0,
    toJSON: () => ({}),
  });
  return { ...view, svg, ...fns };
}

const selectionRect = (c: HTMLElement) => c.querySelector(".nps-selection") as SVGRectElement;

describe("dragging the whole window", () => {
  test("the window follows the pointer and the start is reported on release", () => {
    const { svg, container, onShift, onMove } = chart();
    fireEvent.pointerDown(selectionRect(container), { pointerId: 1, clientX: 100 });
    fireEvent.pointerMove(svg, { clientX: 600 });
    expect(Number(selectionRect(container).getAttribute("x"))).toBeCloseTo(500, 0);
    expect(onShift).not.toHaveBeenCalled();
    fireEvent.pointerUp(svg);
    expect(onShift).toHaveBeenCalledTimes(1);
    expect(onShift.mock.calls[0]?.[0]).toBeCloseTo(70, 0);
    expect(onMove).not.toHaveBeenCalled();
  });

  test("the window cannot leave the song", () => {
    const { svg, container, onShift } = chart();
    fireEvent.pointerDown(selectionRect(container), { pointerId: 1, clientX: 100 });
    fireEvent.pointerMove(svg, { clientX: 1000 });
    fireEvent.pointerUp(svg);
    expect(onShift.mock.calls[0]?.[0]).toBeCloseTo(76, 0);
    fireEvent.pointerDown(selectionRect(container), { pointerId: 1, clientX: 600 });
    fireEvent.pointerMove(svg, { clientX: 0 });
    fireEvent.pointerUp(svg);
    expect(onShift.mock.calls[1]?.[0]).toBe(0);
  });

  test("a click without movement reports nothing", () => {
    const { svg, container, onShift } = chart();
    fireEvent.pointerDown(selectionRect(container), { pointerId: 1, clientX: 100 });
    fireEvent.pointerUp(svg);
    expect(onShift).not.toHaveBeenCalled();
  });

  test("a cancelled drag reports nothing and the window returns", () => {
    const { svg, container, onShift } = chart();
    fireEvent.pointerDown(selectionRect(container), { pointerId: 1, clientX: 100 });
    fireEvent.pointerMove(svg, { clientX: 600 });
    fireEvent.pointerCancel(svg);
    expect(onShift).not.toHaveBeenCalled();
    expect(Number(selectionRect(container).getAttribute("x"))).toBe(0);
  });

  test("a handle still resizes", () => {
    const { svg, onMove, onShift } = chart();
    fireEvent.pointerDown(screen.getByRole("slider", { name: "Crop end" }), { pointerId: 1 });
    fireEvent.pointerMove(svg, { clientX: 500 });
    expect(onMove).toHaveBeenCalledWith("end", 70);
    fireEvent.pointerUp(svg);
    expect(onShift).not.toHaveBeenCalled();
  });
});

describe("double-click", () => {
  test("on another section reports that section's start", () => {
    const { svg, onJump } = chart();
    fireEvent.doubleClick(svg, { clientX: 700 });
    expect(onJump).toHaveBeenCalledWith(64);
    fireEvent.doubleClick(svg, { clientX: 900 });
    expect(onJump).toHaveBeenLastCalledWith(112);
  });

  test("inside the selection does nothing", () => {
    const { svg, onJump } = chart();
    fireEvent.doubleClick(svg, { clientX: 200 });
    expect(onJump).not.toHaveBeenCalled();
  });
});

describe("move buttons", () => {
  test("step the whole window and are named for it", async () => {
    const { onShiftStep } = chart();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Move selection later" }));
    expect(onShiftStep).toHaveBeenLastCalledWith(1);
    await user.click(screen.getByRole("button", { name: "Move selection earlier" }));
    expect(onShiftStep).toHaveBeenLastCalledWith(-1);
  });

  test("are disabled at the ends", () => {
    chart({ canShift: { earlier: false, later: true } });
    expect(screen.getByRole("button", { name: "Move selection earlier" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Move selection later" })).toBeEnabled();
  });

  test("are absent without a selection", () => {
    chart({ selection: null });
    expect(screen.queryByRole("button", { name: /Move selection/ })).toBeNull();
  });
});

describe("axes", () => {
  test("a time axis with mm:ss ticks replaces the idle hint", () => {
    chart();
    const axis = screen.getByTestId("time-axis");
    for (const t of ["00:00", "00:30", "01:00", "01:30", "02:00"]) {
      expect(within(axis).getByText(t)).toBeInTheDocument();
    }
    expect(screen.queryByText(/Hover the chart/)).toBeNull();
  });

  test("a y axis with notes-per-second values", () => {
    chart();
    const axis = screen.getByTestId("y-axis");
    for (const v of ["0", "2", "4", "6"]) expect(within(axis).getByText(v)).toBeInTheDocument();
  });

  test("the readout shows only while hovering or a handle has focus", () => {
    const { svg } = chart();
    const readout = document.querySelector(".nps-hover") as HTMLElement;
    expect(readout).toHaveAttribute("aria-live", "polite");
    expect(readout).toBeEmptyDOMElement();
    fireEvent.pointerMove(svg, { clientX: 500 });
    expect(readout).not.toBeEmptyDOMElement();
    fireEvent.pointerLeave(svg);
    expect(readout).toBeEmptyDOMElement();
  });
});

describe("line colours", () => {
  test("lines and legend use the level colours", () => {
    const { container } = chart();
    for (const [name, label] of [
      ["Expert", "Expert"],
      ["ExpertPlus", "Expert+"],
    ] as const) {
      const colour = levelColor(name) as string;
      expect(container.querySelector(`path[data-difficulty="${name}"]`)).toHaveAttribute(
        "stroke",
        colour,
      );
      const item = screen.getByText(label).closest("li");
      expect(item?.querySelector("line")).toHaveAttribute("stroke", colour);
    }
  });
});

describe("playing the selection", () => {
  const play = () => screen.getByRole("button", { name: "Play selected section" });

  test("plays from the start, moves the playhead, pauses and stops at the end", async () => {
    const { container } = chart({ selection: { start_s: 14, end_s: 78 } });
    const user = userEvent.setup();
    await user.click(play());
    expect(audio.src).toBe("/api/maps/x/audio");
    audio.dispatchEvent(new Event("loadedmetadata"));
    expect(audio.currentTime).toBe(14);
    audio.currentTime = 46;
    act(() => void audio.dispatchEvent(new Event("timeupdate")));
    const head = container.querySelector(".nps-playhead") as SVGLineElement;
    expect(Number(head.getAttribute("x1"))).toBeCloseTo((46 / 140) * 1000, 0);
    await user.click(screen.getByRole("button", { name: "Pause selected section" }));
    expect(audio.paused).toBe(true);
    expect(container.querySelector(".nps-playhead")).toBeNull();
    await user.click(play());
    audio.currentTime = 78.2;
    act(() => void audio.dispatchEvent(new Event("timeupdate")));
    expect(play()).toBeInTheDocument();
    expect(audio.paused).toBe(true);
  });

  test("starting another audio stops this one", async () => {
    chart();
    await userEvent.click(play());
    expect(screen.getByRole("button", { name: "Pause selected section" })).toBeInTheDocument();
    act(() => togglePreview("/api/other"));
    expect(play()).toBeInTheDocument();
  });

  test("there is no play button without audio", () => {
    chart({ audioUrl: null });
    expect(screen.queryByRole("button", { name: /selected section/ })).toBeNull();
  });
});
