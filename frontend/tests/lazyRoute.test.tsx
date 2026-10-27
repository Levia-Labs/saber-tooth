import { render, screen, waitFor } from "@testing-library/react";
import { Suspense } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { lazyRoute } from "../src/lib/lazyRoute";

const chunkError = () => new TypeError("Failed to fetch dynamically imported module: /assets/x.js");

describe("lazyRoute: a page chunk that vanished after a rebuild", () => {
  beforeEach(() => sessionStorage.clear());

  test("reloads once so the new build is fetched instead of crashing", async () => {
    const reload = vi.fn();
    const Page = lazyRoute(() => Promise.reject(chunkError()), reload);
    render(
      <Suspense fallback={<p>loading</p>}>
        <Page />
      </Suspense>,
    );
    await waitFor(() => expect(reload).toHaveBeenCalledTimes(1));
    expect(screen.getByText("loading")).toBeInTheDocument();
  });

  test("a second failure right after the reload is thrown to the error boundary", async () => {
    const reload = vi.fn();
    sessionStorage.setItem("st-chunk-reload", String(Date.now()));
    const Page = lazyRoute(() => Promise.reject(chunkError()), reload);
    const err = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const { container } = render(
      <Suspense fallback={<p>loading</p>}>
        <Page />
      </Suspense>,
    );
    await new Promise((r) => setTimeout(r, 30));
    expect(reload).not.toHaveBeenCalled();
    expect(container.textContent).toBe("loading");
    err.mockRestore();
  });

  test("other load errors are never retried by reloading", async () => {
    const reload = vi.fn();
    const Page = lazyRoute(() => Promise.reject(new Error("boom")), reload);
    const err = vi.spyOn(console, "error").mockImplementation(() => undefined);
    render(
      <Suspense fallback={<p>loading</p>}>
        <Page />
      </Suspense>,
    );
    await new Promise((r) => setTimeout(r, 30));
    expect(reload).not.toHaveBeenCalled();
    err.mockRestore();
  });
});
