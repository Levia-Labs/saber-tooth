import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { vi } from "vitest";
import { makeQueryClient, routes } from "../src/App";
import { TipProvider } from "../src/components/Tip";
import type { Facets, MapItem } from "../src/api/types";

export function item(n: number, patch: Partial<MapItem> = {}): MapItem {
  return {
    id: `id${String(n).padStart(10, "0")}`,
    folder: `Folder ${n}`,
    title: `Song ${n}`,
    mapper: `Mapper ${n}`,
    environment: n % 2 ? "Origins" : "BigMirrorEnvironment",
    parse_error: null,
    errors: 0,
    warnings: 0,
    scanned_at: null,
    status: "unscanned",
    cover_url: null,
    difficulties: ["Easy", "Expert", "ExpertPlus"],
    approved: 0,
    pending: 0,
    bpm: 128,
    duration_s: 201,
    job: null,
    ...patch,
  };
}

export const FACETS: Facets = {
  status: {
    error: 2,
    warn: 1,
    ok: 0,
    unscanned: 3,
    unreadable: 0,
    scanning: 1,
    applying: 0,
    fixing: 0,
    queued: 0,
  },
  environments: [
    { name: "Origins", count: 4 },
    { name: "BigMirrorEnvironment", count: 3 },
  ],
  mappers: [
    { name: "Mapper 1", count: 4 },
    { name: "Mapper 2, Jr", count: 3 },
  ],
  levels: { Easy: 5, Normal: 1, Hard: 2, Expert: 6, ExpertPlus: 4 },
  total: 7,
};

type Handler = (url: URL, init?: RequestInit) => unknown;

/** Stub fetch: handlers get the parsed URL and return a JSON body (or a Response). */
export function mockFetch(handler: Handler) {
  const calls: URL[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://localhost");
    calls.push(url);
    const body = await handler(url, init);
    if (body instanceof Response) return body;
    return new Response(JSON.stringify(body ?? {}), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fn);
  return { fn, calls };
}

export function renderApp(url: string) {
  const router = createMemoryRouter(routes, { initialEntries: [url] });
  const view = render(
    <QueryClientProvider client={makeQueryClient()}>
      <TipProvider delayDuration={0}>
        <RouterProvider router={router} />
      </TipProvider>
    </QueryClientProvider>,
  );
  return { router, ...view };
}
