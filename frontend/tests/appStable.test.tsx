import { renderHook } from "@testing-library/react";
import { createMemoryRouter } from "react-router";
import { describe, expect, test, vi } from "vitest";
import { routes, useAppInstances } from "../src/App";

describe("useAppInstances", () => {
  test("a re-render keeps one router and one query client", () => {
    const add = vi.spyOn(window, "addEventListener");
    const view = renderHook(() => useAppInstances());
    const popstate = () => add.mock.calls.filter(([type]) => type === "popstate").length;
    const first = view.result.current;
    const listeners = popstate();
    expect(listeners).toBeGreaterThan(0);
    view.rerender();
    view.rerender();
    expect(view.result.current.router).toBe(first.router);
    expect(view.result.current.client).toBe(first.client);
    expect(popstate()).toBe(listeners);
    add.mockRestore();
  });

  test("an injected router is used as given and none is built", () => {
    const add = vi.spyOn(window, "addEventListener");
    const router = createMemoryRouter(routes, { initialEntries: ["/about"] });
    const view = renderHook(() => useAppInstances(router));
    expect(view.result.current.router).toBe(router);
    expect(add.mock.calls.filter(([type]) => type === "popstate")).toHaveLength(0);
    add.mockRestore();
  });
});
