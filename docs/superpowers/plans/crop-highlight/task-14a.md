# Task 14: NpsChart SVG component

**Files:**

- Create: `frontend/src/components/NpsChart.tsx`
- Create: `frontend/src/styles/crop.css`
- Modify: `frontend/src/main.tsx` (one import)
- Test: `frontend/tests/cropchart.test.tsx`

**Interfaces:**

Consumes: `CropSection`, `EndKind` (`api/types.ts`); `KIND_LABEL`, `clock`, `secondsAt` (`lib/crop.ts`); `TIMELINE` (`tests/crophelpers.tsx`).

Produces (`components/NpsChart.tsx`):

```ts
export type Edge = "start" | "end";
export interface Span {
  start_s: number;
  end_s: number;
}
export interface EndMark {
  seconds: number;
  kind: EndKind;
}

export function NpsChart(props: {
  nps: Record<string, number[]>; // one line per difficulty
  hardest: string; // drawn emphasised
  sections: CropSection[]; // shaded bands
  duration: number; // song seconds; the x axis
  selection: Span | null; // the chosen window, with two slider handles
  faint: Span[]; // the next suggested windows
  endMarks: EndMark[]; // allowed ends of the current start, marked by kind
  onMove: (edge: Edge, seconds: number) => void; // while a handle is dragged
  onStep: (edge: Edge, dir: 1 | -1, jump: boolean) => void; // arrow keys on a focused handle
}): JSX.Element;
```

The SVG is 1000 by 160 units and stretches to its box; a pointer maps to seconds through `secondsAt(clientX, rect.left, rect.width, duration)`. Handles are `role="slider"` groups named "Crop start" and "Crop end" with `aria-valuenow` in seconds and `aria-valuetext` as `m:ss.s`. Arrow Right or Up steps forward, Left or Down back, Shift sets `jump`. Hovering shows time, section and notes per second per difficulty in a line under the chart.

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/cropchart.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
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
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx --prefix frontend vitest run --root frontend tests/cropchart.test.tsx`
Expected: FAIL: `Failed to resolve import "../src/components/NpsChart"`.

Continued in [task-14b.md](task-14b.md).
