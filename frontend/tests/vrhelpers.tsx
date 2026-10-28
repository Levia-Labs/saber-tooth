import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { vi } from "vitest";
import { makeQueryClient } from "../src/App";
import { AnnouncerProvider } from "../src/components/Announcer";
import { TipProvider } from "../src/components/Tip";

function Where() {
  const { pathname, search } = useLocation();
  return <span data-testid="where">{pathname + search}</span>;
}

/** Render a VR screen at `url`, mounted on the route pattern `route`. */
export function renderVr(url: string, route: string, element: ReactElement) {
  return render(
    <QueryClientProvider client={makeQueryClient()}>
      <TipProvider delayDuration={0}>
        <AnnouncerProvider>
          <MemoryRouter initialEntries={[url]}>
            <Routes>
              <Route path={route} element={element} />
              <Route path="*" element={<span>elsewhere</span>} />
            </Routes>
            <Where />
          </MemoryRouter>
        </AnnouncerProvider>
      </TipProvider>
    </QueryClientProvider>,
  );
}

/** Stand in for IntersectionObserver; `fire()` reports the newest observer's target as visible. */
export function stubObserver() {
  const callbacks: IntersectionObserverCallback[] = [];
  class Stub {
    constructor(callback: IntersectionObserverCallback) {
      callbacks.push(callback);
    }
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  vi.stubGlobal("IntersectionObserver", Stub);
  return {
    fire: () =>
      callbacks.at(-1)?.(
        [{ isIntersecting: true } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      ),
  };
}
