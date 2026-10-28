import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { NpsChart } from "../src/components/NpsChart";
import { TIMELINE } from "./crophelpers";

const MARKS = [
  { seconds: 56, kind: "bar4" as const },
  { seconds: 58, kind: "bar" as const },
  { seconds: 64, kind: "section" as const },
  { seconds: 66, kind: "bar" as const },
];

function chart(patch: Partial<Parameters<typeof NpsChart>[0]> = {}) {
  const onMove = vi.fn();
  const onStep = vi.fn();
  const view = render(
    <NpsChart
      nps={TIMELINE.nps}
      hardest="ExpertPlus"
      sections={TIMELINE.sections}
      duration={TIMELINE.duration_s}
      selection={{ start_s: 0, end_s: 64 }}
      faint={[{ start_s: 64, end_s: 128 }]}
      endMarks={MARKS}
      onMove={onMove}
      onStep={onStep}
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
  return { ...view, svg, onMove, onStep };
}

describe("NpsChart", () => {
  test("draws section bands, the selection, faint windows, lines and end marks", () => {
    const { container } = chart();
    expect(container.querySelectorAll(".nps-section")).toHaveLength(3);
    expect(container.querySelectorAll(".nps-selection")).toHaveLength(1);
    expect(container.querySelectorAll(".nps-faint")).toHaveLength(1);
    expect(container.querySelectorAll("path[data-difficulty]")).toHaveLength(2);
    expect(container.querySelector(".nps-line-hardest")).toHaveAttribute(
      "data-difficulty",
      "ExpertPlus",
    );
    expect(container.querySelectorAll('[data-kind="section"]')).toHaveLength(1);
    expect(container.querySelectorAll('[data-kind="bar"]')).toHaveLength(2);
  });

  test("the handles are sliders with the time as their value", () => {
    chart();
    const start = screen.getByRole("slider", { name: "Crop start" });
    const end = screen.getByRole("slider", { name: "Crop end" });
    expect(start).toHaveAttribute("aria-valuenow", "0");
    expect(end).toHaveAttribute("aria-valuenow", "64");
    expect(end).toHaveAttribute("aria-valuetext", "1:04.0");
  });

  test("without a selection there are no handles", () => {
    chart({ selection: null, endMarks: [] });
    expect(screen.queryByRole("slider")).toBeNull();
  });

  test("arrow keys step, Shift jumps, other keys do nothing", async () => {
    const { onStep } = chart();
    const user = userEvent.setup();
    screen.getByRole("slider", { name: "Crop start" }).focus();
    await user.keyboard("{ArrowRight}");
    expect(onStep).toHaveBeenLastCalledWith("start", 1, false);
    await user.keyboard("{Shift>}{ArrowLeft}{/Shift}");
    expect(onStep).toHaveBeenLastCalledWith("start", -1, true);
    screen.getByRole("slider", { name: "Crop end" }).focus();
    await user.keyboard("{ArrowDown}");
    expect(onStep).toHaveBeenLastCalledWith("end", -1, false);
    await user.keyboard("a");
    expect(onStep).toHaveBeenCalledTimes(3);
  });

  test("dragging a handle reports seconds until the pointer is released", () => {
    const { svg, onMove } = chart();
    fireEvent.pointerDown(screen.getByRole("slider", { name: "Crop start" }), { pointerId: 1 });
    fireEvent.pointerMove(svg, { clientX: 500 });
    expect(onMove).toHaveBeenCalledWith("start", 70);
    fireEvent.pointerUp(svg);
    fireEvent.pointerMove(svg, { clientX: 700 });
    expect(onMove).toHaveBeenCalledTimes(1);
  });

  test("hovering shows time, section and notes per second", () => {
    const { svg } = chart();
    fireEvent.pointerMove(svg, { clientX: 500 });
    expect(screen.getByText(/^1:10\.0, section 2 of 3, notes per second: Expert/)).toBeVisible();
    fireEvent.pointerLeave(svg);
    expect(screen.getByText(/Hover the chart/)).toBeVisible();
  });
});

describe("NpsChart keyboard readout", () => {
  test("a focused handle shows time, section and each difficulty's notes per second", async () => {
    const { onStep, rerender } = chart();
    const user = userEvent.setup();
    act(() => screen.getByRole("slider", { name: "Crop start" }).focus());
    expect(
      screen.getByText("0:00.0, section 1 of 3, notes per second: Expert 0, ExpertPlus 0"),
    ).toBeVisible();
    await user.keyboard("{ArrowRight}");
    expect(onStep).toHaveBeenLastCalledWith("start", 1, false);
    rerender(
      <NpsChart
        nps={TIMELINE.nps}
        hardest="ExpertPlus"
        sections={TIMELINE.sections}
        duration={TIMELINE.duration_s}
        selection={{ start_s: 70, end_s: 120 }}
        faint={[]}
        endMarks={[]}
        onMove={vi.fn()}
        onStep={onStep}
      />,
    );
    const readout = screen.getByText(/^1:10\.0, section 2 of 3, notes per second: /);
    expect(readout).toHaveTextContent("Expert 2, ExpertPlus 3");
    expect(readout).toHaveAttribute("aria-live", "polite");
  });
});
