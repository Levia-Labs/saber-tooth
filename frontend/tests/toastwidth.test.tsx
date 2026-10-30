import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { act, render } from "@testing-library/react";
import fc from "fast-check";
import { afterEach, describe, expect, test, vi } from "vitest";
import { Alert } from "../src/components/Alert";
import { ToastRow } from "../src/components/ToastRow";
import { quantize } from "../src/lib/quantize";

describe("quantize", () => {
  test("rounds up to a whole step, never by a full step", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 500_000 }).map((n) => n / 100),
        fc.constantFrom(50, 100, 150),
        (width, step) => {
          const r = quantize(width, step);
          expect(r).toBeGreaterThanOrEqual(width);
          expect(r - width).toBeLessThan(step);
          expect(r % step).toBe(0);
        },
      ),
    );
  });
});

describe("toast width", () => {
  let callbacks: (() => void)[] = [];
  let natural = 0;
  class Observer {
    constructor(cb: () => void) {
      callbacks.push(cb);
    }
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  const setup = () => {
    callbacks = [];
    vi.stubGlobal("ResizeObserver", Observer);
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(
      () => ({ width: natural }) as DOMRect,
    );
  };
  afterEach(() => vi.restoreAllMocks());

  const banner = { key: "k", variant: "progress", title: "Fix Song", onOpen: () => undefined };

  test("a job toast is set to the next multiple of 50 px and follows a resize", () => {
    setup();
    natural = 231;
    const { container } = render(
      <ToastRow banner={{ ...banner, expiresAt: null } as never} onClose={() => undefined} />,
    );
    const el = container.querySelector(".toast") as HTMLElement;
    expect(el.style.width).toBe("250px");
    natural = 251;
    act(() => callbacks.forEach((cb) => cb()));
    expect(el.style.width).toBe("300px");
  });

  test("a toast alert is quantized and re-measured when its content changes", () => {
    setup();
    natural = 120;
    const { container, rerender } = render(
      <Alert variant="info" title="Hi" className="toast" quantized fitKey="a" />,
    );
    const el = container.querySelector(".toast") as HTMLElement;
    expect(el.style.width).toBe("150px");
    natural = 400;
    rerender(<Alert variant="info" title="Hi there" className="toast" quantized fitKey="b" />);
    expect(el.style.width).toBe("400px");
  });

  test("a plain alert keeps its width", () => {
    setup();
    natural = 120;
    const { container } = render(<Alert variant="info" title="Hi" />);
    expect((container.querySelector(".alert") as HTMLElement).style.width).toBe("");
  });

  test("on the mobile breakpoint no width is set and the css makes the toast full width", () => {
    setup();
    natural = 120;
    vi.stubGlobal("matchMedia", (q: string) => ({ matches: q.includes("1299.98px") }));
    const { container } = render(<Alert variant="info" title="Hi" className="toast" quantized />);
    expect((container.querySelector(".toast") as HTMLElement).style.width).toBe("");
    const css = readFileSync(resolve(__dirname, "../src/styles/alerts.css"), "utf-8");
    const mobile = /@media \(max-width: 1299.98px\) \{([\s\S]*?)\n\}/.exec(css)?.[1] ?? "";
    expect(mobile).toMatch(/\.toast-stack \.toast\s*\{[^}]*width:\s*100%/);
  });
});
