import { act, fireEvent, render, screen } from "@testing-library/react";
import fc from "fast-check";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { stepBound } from "../src/lib/stepRange";
import { useHoldRepeat } from "../src/lib/useHoldRepeat";

const calls: boolean[] = [];

function Probe() {
  const hold = useHoldRepeat((fast) => calls.push(fast));
  return <button {...hold}>go</button>;
}

beforeEach(() => {
  calls.length = 0;
  vi.useFakeTimers();
});
afterEach(() => vi.useRealTimers());

const press = () => fireEvent.pointerDown(screen.getByRole("button"), { button: 0 });
const run = (ms: number) => act(() => void vi.advanceTimersByTime(ms));

describe("useHoldRepeat", () => {
  test("steps on press, repeats after 400 ms, then every 60 ms", () => {
    render(<Probe />);
    press();
    expect(calls).toEqual([false]);
    run(399);
    expect(calls).toHaveLength(1);
    run(1);
    expect(calls).toHaveLength(2);
    run(120);
    expect(calls).toHaveLength(4);
  });

  test("speeds up after 1.5 s of holding", () => {
    render(<Probe />);
    press();
    run(1400);
    expect(calls.every((fast) => !fast)).toBe(true);
    run(200);
    expect(calls.at(-1)).toBe(true);
  });

  test.each(["pointerUp", "pointerCancel", "pointerLeave", "blur"] as const)(
    "%s stops the repeat",
    (event) => {
      render(<Probe />);
      press();
      run(500);
      fireEvent[event](screen.getByRole("button"));
      const n = calls.length;
      run(1000);
      expect(calls).toHaveLength(n);
    },
  );

  test("a keyboard click steps once; a pointer click does not step twice", () => {
    render(<Probe />);
    fireEvent.click(screen.getByRole("button"), { detail: 0 });
    expect(calls).toHaveLength(1);
    press();
    fireEvent.pointerUp(screen.getByRole("button"));
    fireEvent.click(screen.getByRole("button"), { detail: 1 });
    expect(calls).toHaveLength(2);
  });

  test("unmounting stops the repeat", () => {
    const { unmount } = render(<Probe />);
    press();
    unmount();
    run(1000);
    expect(calls).toHaveLength(1);
  });
});

describe("stepBound", () => {
  test("steps, clamps and starts from the fallback", () => {
    expect(stepBound(10, 1, 0, 20, 0)).toBe(11);
    expect(stepBound(0, -1, 0, 20, 0)).toBe(0);
    expect(stepBound(20, 5, 0, 20, 0)).toBe(20);
    expect(stepBound(null, 1, 0, 20, 90)).toBe(20);
    expect(stepBound(null, -1, 0, 500, 90)).toBe(89);
  });

  test("the result always stays within the bounds", () => {
    fc.assert(
      fc.property(
        fc.option(fc.integer({ min: 0, max: 7200 }), { nil: null }),
        fc.integer({ min: -5, max: 5 }),
        fc.integer({ min: 0, max: 7200 }),
        fc.integer({ min: 0, max: 7200 }),
        (cur, delta, lo, hi) => {
          const v = stepBound(cur, delta, lo, hi, 0);
          return v >= lo && v <= Math.max(lo, hi);
        },
      ),
    );
  });
});
