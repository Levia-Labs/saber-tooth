// Typed API client: every request the app makes goes through this module.
import { apiParams, type LibraryState } from "../lib/urlstate";
import type { Facets, Job, MapItem, MapPage, Proposal } from "./types";

export class ApiError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type Body = Record<string, unknown> | FormData | undefined;

export const TIMEOUT_STATUS = 408;
export const GET_TIMEOUT_MS = 15_000;
export const POST_TIMEOUT_MS = 120_000;

/** A signal that aborts when the caller's does or after `ms`; `timedOut` tells which. */
function withTimeout(ms: number, outer?: AbortSignal) {
  const ctl = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    ctl.abort();
  }, ms);
  const forward = () => ctl.abort();
  if (outer?.aborted) ctl.abort();
  outer?.addEventListener("abort", forward);
  return {
    signal: ctl.signal,
    timedOut: () => timedOut,
    done: () => {
      clearTimeout(timer);
      outer?.removeEventListener("abort", forward);
    },
  };
}

export async function request<T>(
  method: "GET" | "POST" | "DELETE",
  path: string,
  body?: Body,
  signal?: AbortSignal,
  timeoutMs: number = method === "GET" ? GET_TIMEOUT_MS : POST_TIMEOUT_MS,
): Promise<T> {
  const guard = withTimeout(timeoutMs, signal);
  const init: RequestInit = { method, headers: {}, signal: guard.signal };
  if (body instanceof FormData) {
    init.body = body;
  } else if (body !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(body);
  }
  let res: Response;
  let data: unknown;
  try {
    res = await fetch(path, init);
    data = await res.json().catch(() => null);
  } catch (err) {
    if (guard.timedOut()) throw new ApiError("Request timed out", TIMEOUT_STATUS);
    throw err;
  } finally {
    guard.done();
  }
  if (!res.ok) {
    const record = (data ?? {}) as { detail?: unknown; error?: unknown };
    const detail = record.error ?? record.detail;
    throw new ApiError(typeof detail === "string" ? detail : `HTTP ${res.status}`, res.status);
  }
  return data as T;
}

const seg = encodeURIComponent;

export function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : "unknown error";
}

export const LIBRARY_PAGE_SIZE = 40;

export function listMaps(
  state: LibraryState,
  offset: number,
  signal?: AbortSignal,
): Promise<MapPage> {
  const query = apiParams(state, offset, LIBRARY_PAGE_SIZE).toString();
  return request("GET", `/api/maps?${query}`, undefined, signal);
}

export const getFacets = (signal?: AbortSignal): Promise<Facets> =>
  request("GET", "/api/maps/facets", undefined, signal);

export const getMap = (id: string): Promise<MapItem> => request("GET", `/api/maps/${seg(id)}`);

export const getProposals = (id: string): Promise<Proposal[]> =>
  request("GET", `/api/maps/${seg(id)}/proposals`);

export const getJob = (id: string): Promise<Job> => request("GET", `/api/jobs/${seg(id)}`);

export interface Started {
  job: string;
}

export const scanMap = (id: string): Promise<Started> =>
  request("POST", `/api/maps/${seg(id)}/scan`);

export const applyMap = (id: string): Promise<Started> =>
  request("POST", `/api/maps/${seg(id)}/apply`);

export const fixMap = (id: string): Promise<Started> => request("POST", `/api/maps/${seg(id)}/fix`);

export const deleteMap = (id: string): Promise<{ deleted: string }> =>
  request("DELETE", `/api/maps/${seg(id)}`);

export const approveAll = (id: string): Promise<{ approved: number }> =>
  request("POST", `/api/maps/${seg(id)}/approve-all`);

export const approveProposal = (id: number | string): Promise<{ id: number | string }> =>
  request("POST", `/api/proposals/${seg(String(id))}/approve`);

export const rejectProposal = (id: number | string): Promise<{ id: number | string }> =>
  request("POST", `/api/proposals/${seg(String(id))}/reject`);

export const generateFromUrl = (url: string): Promise<Started> =>
  request("POST", "/api/generate", { url });

export function generateFromFile(file: File): Promise<Started> {
  const form = new FormData();
  form.append("file", file);
  return request("POST", "/api/generate", form);
}

export const learnLightshows = (): Promise<Started> => request("POST", "/api/lightshow/learn");

/** Network errors, 5xx and 429 are worth retrying; other 4xx surface at once. */
export function isRetryable(err: unknown): boolean {
  if (!(err instanceof ApiError)) return true;
  return err.status >= 500 || err.status === 429;
}
