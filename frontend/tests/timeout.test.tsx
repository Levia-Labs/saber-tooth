import { screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { ApiError, GET_TIMEOUT_MS, request } from "../src/api/client";
import { FACETS, mockFetch, renderApp } from "./helpers";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

/** A fetch that never answers but rejects when its signal aborts. */
function hangingFetch() {
  return vi.fn(
    (_input: RequestInfo | URL, init?: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () =>
          reject(new DOMException("aborted", "AbortError")),
        );
      }),
  );
}

describe("request timeout", () => {
  test("a GET that never answers fails with a 408 ApiError", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", hangingFetch());
    const result = request("GET", "/api/maps").catch((e: unknown) => e);
    await vi.advanceTimersByTimeAsync(GET_TIMEOUT_MS + 1);
    const err = await result;
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(408);
  });

  test("a caller abort stays an abort, not a timeout", async () => {
    vi.stubGlobal("fetch", hangingFetch());
    const ctl = new AbortController();
    const result = request("GET", "/api/maps", undefined, ctl.signal).catch((e: unknown) => e);
    ctl.abort();
    const err = await result;
    expect(err).not.toBeInstanceOf(ApiError);
  });

  test("the library shows a warning with Retry instead of endless skeletons", async () => {
    mockFetch((url) =>
      url.pathname === "/api/maps/facets"
        ? FACETS
        : new Response(JSON.stringify({ error: "Request timed out" }), { status: 408 }),
    );
    renderApp("/");
    expect(await screen.findByText(/the server is slow to answer/)).toBeTruthy();
    expect(screen.getByRole("button", { name: /try again/i })).toBeTruthy();
  });
});
