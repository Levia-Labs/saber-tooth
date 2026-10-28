import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { levelColor } from "../src/lib/levels";
import { chart, mockAudio } from "./charthelpers";

mockAudio();

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

describe("move arrows", () => {
  test("the left and right selection arrows are gone", () => {
    chart();
    expect(screen.queryByRole("button", { name: /Move selection/ })).toBeNull();
    expect(document.querySelector(".nps-move")).toBeNull();
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
