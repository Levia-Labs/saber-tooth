import { act, renderHook } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { MemoryRouter, useLocation } from "react-router";
import { describe, expect, test } from "vitest";
import { useJobsState } from "../src/lib/useJobsState";
import { useLibraryState } from "../src/lib/hooks";
import { usePlState } from "../src/lib/usePlState";

const wrap = ({ children }: { children: ReactNode }) =>
  createElement(MemoryRouter, { initialEntries: ["/?from=lib&back=q%3Drock"] }, children);

describe("every list hook keeps from and back", () => {
  test.each([
    ["library", useLibraryState],
    ["playlists", usePlState],
    ["jobs", useJobsState],
  ] as const)("%s: update and clearFilters keep the origin", (_name, hook) => {
    const { result } = renderHook(() => ({ c: hook(), l: useLocation() }), { wrapper: wrap });
    act(() => result.current.c.update({ q: "x" } as never));
    let p = new URLSearchParams(result.current.l.search);
    expect(p.get("from")).toBe("lib");
    expect(p.get("back")).toBe("q=rock");
    act(() => result.current.c.clearFilters());
    p = new URLSearchParams(result.current.l.search);
    expect(p.get("from")).toBe("lib");
    expect(p.get("back")).toBe("q=rock");
  });
});
