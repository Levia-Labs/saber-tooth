import { act, renderHook } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { MemoryRouter, useLocation } from "react-router";
import { describe, expect, test } from "vitest";
import { allPlaylistsHref } from "../src/lib/backlink";
import { useBsState } from "../src/lib/useBsState";

const wrap = ({ children }: { children: ReactNode }) =>
  createElement(
    MemoryRouter,
    { initialEntries: ["/beatsaver/playlists/p1?from=bs-playlists&back=q%3Drock"] },
    children,
  );

describe("BeatSaver filters keep the origin", () => {
  test("changing and clearing a filter keeps from and back, so Back to list still works", () => {
    const { result } = renderHook(() => ({ c: useBsState(), l: useLocation() }), { wrapper: wrap });
    act(() => result.current.c.update({ q: "x" }));
    let p = new URLSearchParams(result.current.l.search);
    expect(p.get("q")).toBe("x");
    expect(p.get("from")).toBe("bs-playlists");
    expect(allPlaylistsHref(p.get("back") ?? undefined)).toBe("/beatsaver/playlists?q=rock");
    act(() => result.current.c.clearFilters());
    p = new URLSearchParams(result.current.l.search);
    expect(p.get("from")).toBe("bs-playlists");
    expect(p.get("back")).toBe("q=rock");
  });
});
