import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { fitRow, installLabelCollapse } from "../src/lib/labelCollapse";

/** A row of buttons whose measured content width is 40 px per button plus 80 px per open label. */
function makeRow(names: string[], opts: { primary?: string; keep?: string } = {}) {
  const row = document.createElement("div");
  row.setAttribute("data-label-row", "");
  for (const name of names) {
    const btn = document.createElement("button");
    btn.className = `btn${name === opts.primary ? " primary" : ""}${name === opts.keep ? " keep-label" : ""}`;
    const label = document.createElement("span");
    label.className = "label-collapsible";
    label.textContent = name;
    btn.append(label);
    row.append(btn);
  }
  const box = { width: 1000 };
  const open = () => row.querySelectorAll(".label-collapsible:not([data-collapsed])").length;
  Object.defineProperty(row, "clientWidth", { get: () => box.width });
  Object.defineProperty(row, "scrollWidth", { get: () => 40 * names.length + 80 * open() });
  document.body.append(row);
  return {
    row,
    box,
    collapsed: () => names.filter((_, i) => labelAt(row, i).hasAttribute("data-collapsed")),
  };
}
const labelAt = (row: HTMLElement, i: number) =>
  row.querySelectorAll<HTMLElement>(".label-collapsible")[i]!;

afterEach(() => {
  document.body.innerHTML = "";
  vi.unstubAllGlobals();
});

test("labels collapse last button first as the room shrinks, and return as it grows", () => {
  const { row, box, collapsed } = makeRow(["A", "B", "C", "D"]);
  // Full: 4 * 40 + 4 * 80 = 480.
  box.width = 500;
  fitRow(row);
  expect(collapsed()).toEqual([]);
  box.width = 400; // 480 -> 400 needs one label gone
  fitRow(row);
  expect(collapsed()).toEqual(["D"]);
  box.width = 320;
  fitRow(row);
  expect(collapsed()).toEqual(["C", "D"]);
  box.width = 250;
  fitRow(row);
  expect(collapsed()).toEqual(["B", "C", "D"]);
  box.width = 100;
  fitRow(row);
  expect(collapsed()).toEqual(["A", "B", "C", "D"]);
  box.width = 330;
  fitRow(row);
  expect(collapsed()).toEqual(["C", "D"]);
  box.width = 500;
  fitRow(row);
  expect(collapsed()).toEqual([]);
});

test("the primary button keeps its label longest and a keep-label button never collapses", () => {
  const { row, box, collapsed } = makeRow(["A", "B", "C"], { primary: "C", keep: "A" });
  box.width = 300; // full: 120 + 160 (A keeps its label out of the count below)
  fitRow(row);
  // Collapsible labels are B and C; B goes first, C (primary) last.
  expect(collapsed()).toEqual(["B"]);
  box.width = 100;
  fitRow(row);
  expect(collapsed()).toEqual(["B", "C"]);
  expect(labelAt(row, 0).hasAttribute("data-collapsed")).toBe(false);
});

test("a hysteresis-free pass is stable: fitting twice gives the same result", () => {
  const { row, box, collapsed } = makeRow(["A", "B", "C"]);
  box.width = 250;
  fitRow(row);
  const once = collapsed();
  fitRow(row);
  expect(collapsed()).toEqual(once);
});

let callbacks: ResizeObserverCallback[] = [];
beforeEach(() => {
  callbacks = [];
  vi.stubGlobal(
    "ResizeObserver",
    class {
      constructor(cb: ResizeObserverCallback) {
        callbacks.push(cb);
      }
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
});

test("the observer refits a row when it is resized", () => {
  const { row, box, collapsed } = makeRow(["A", "B"]);
  const stop = installLabelCollapse();
  box.width = 1000;
  expect(collapsed()).toEqual([]);
  box.width = 150; // full: 80 + 160 = 240
  for (const cb of callbacks) {
    cb([{ target: row } as unknown as ResizeObserverEntry], {} as ResizeObserver);
  }
  expect(collapsed()).toEqual(["A", "B"]);
  box.width = 1000;
  for (const cb of callbacks) {
    cb([{ target: row } as unknown as ResizeObserverEntry], {} as ResizeObserver);
  }
  expect(collapsed()).toEqual([]);
  stop();
});
