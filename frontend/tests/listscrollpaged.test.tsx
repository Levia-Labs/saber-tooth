import { act, render, screen } from "@testing-library/react";
import { useState } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test } from "vitest";
import { useListScroll } from "../src/lib/listscroll";

const ROW = 100;
const KEY = "saber-tooth.scroll:/bs?q=1";
let loads = 0;

/** A scroll region whose height is `pages` pages of 10 rows; scrollTop clamps like a browser. */
function Harness({ total, cap }: { total: number; cap?: number }) {
  const [count, setCount] = useState(10);
  const hasMore = count < total;
  useListScroll(true, count, hasMore, {
    load: () => {
      loads += 1;
      setCount((c) => c + 10);
    },
    busy: false,
    ...(cap ? { cap } : {}),
  });
  return (
    <div
      className="lib-scroll"
      data-testid="s"
      ref={(el) => {
        if (!el) return;
        const held = el as HTMLElement & { __top?: number };
        Object.defineProperty(el, "scrollTop", {
          configurable: true,
          get: () => held.__top ?? 0,
          set: (v: number) => {
            held.__top = Math.max(0, Math.min(v, count * ROW));
          },
        });
      }}
    />
  );
}

const mount = (total: number, cap?: number) =>
  render(
    <MemoryRouter initialEntries={["/bs?q=1"]}>
      <Harness total={total} {...(cap ? { cap } : {})} />
    </MemoryRouter>,
  );

beforeEach(() => {
  sessionStorage.clear();
  loads = 0;
});
afterEach(() => sessionStorage.clear());

describe("paged list restore", () => {
  test("loads further pages until the saved offset is reachable, then scrolls", async () => {
    sessionStorage.setItem(KEY, "2500");
    await act(async () => void mount(100));
    expect(loads).toBe(2);
    expect(screen.getByTestId("s").scrollTop).toBe(2500);
  });

  test("stops at the cap and scrolls as far as it can", async () => {
    sessionStorage.setItem(KEY, "9000");
    await act(async () => void mount(1000, 3));
    expect(loads).toBe(3);
    expect(screen.getByTestId("s").scrollTop).toBe(4000);
  });

  test("a list that ends short scrolls to its end without more loads", async () => {
    sessionStorage.setItem(KEY, "9000");
    await act(async () => void mount(20));
    expect(loads).toBe(1);
    expect(screen.getByTestId("s").scrollTop).toBe(2000);
  });
});
