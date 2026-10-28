# Task 9: Frontend status client and query

New files only, in a new folder `frontend/src/vr/`, so the shared `api/client.ts` and `api/queries.ts` stay untouched. The client reuses `request` from `api/client.ts` and `retry` is not needed (no retries: a missing helper is the normal case). The answer is read tolerantly: any wrong shape becomes the "no headset" status. Polling runs every 5 s while the tab is visible and not at all while it is hidden, including a tab that starts hidden.

**Files:**

- Create: `frontend/src/vr/status.ts`
- Create: `frontend/src/vr/README.md`
- Test: `frontend/tests/vrstatus.test.tsx`

**Interfaces:**

Consumes: `request<T>(method, path, body?, signal?)` (`api/client.ts`), `makeQueryClient` (`App.tsx`), `mockFetch` (`tests/helpers.tsx`).

Produces (`vr/status.ts`):

1. `VR_POLL_MS = 5000`.
2. `interface VrStatus { os: string; runtime: string | null; runtimes: string[]; xr_runtime: string | null; worn: boolean | null; source: "agent" | "local" | "none" }`.
3. `NO_VR: VrStatus` (`os: "unknown"`, everything else empty, `source: "none"`).
4. `readVrStatus(raw: unknown): VrStatus`: tolerant parse; `runtime` is the first of `runtimes`.
5. `getVrStatus(signal?: AbortSignal): Promise<VrStatus>`: `GET /api/vr/status`.
6. `vrKeys.status`: `["vr", "status"]`.
7. `vrStatusOptions(visible: boolean)`: `{ queryKey, queryFn, enabled: visible, refetchInterval: visible ? VR_POLL_MS : false, staleTime: VR_POLL_MS, retry: false }`.
8. `useVrStatus(visible: boolean)`: `useQuery(vrStatusOptions(visible))`.
9. `useVisible(): boolean`: `document.visibilityState !== "hidden"`, updated on `visibilitychange`.

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/vrstatus.test.tsx`:

```tsx
import { QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, test } from "vitest";
import { makeQueryClient } from "../src/App";
import {
  NO_VR,
  VR_POLL_MS,
  getVrStatus,
  readVrStatus,
  useVisible,
  useVrStatus,
  vrStatusOptions,
} from "../src/vr/status";
import { mockFetch } from "./helpers";

const ANSWER = {
  os: "windows",
  runtime: "SteamVR",
  runtimes: ["SteamVR", "Oculus"],
  xr_runtime: "SteamVR",
  worn: true,
  source: "agent",
};

function clientWrapper() {
  const client = makeQueryClient();
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

function setVisibility(state: "visible" | "hidden") {
  Object.defineProperty(document, "visibilityState", { configurable: true, get: () => state });
  document.dispatchEvent(new Event("visibilitychange"));
}

afterEach(() => setVisibility("visible"));

describe("readVrStatus", () => {
  test("keeps a well formed answer", () => {
    expect(readVrStatus(ANSWER)).toEqual(ANSWER);
  });

  test.each([null, undefined, 7, "x", [], {}, { runtimes: "SteamVR" }, { runtimes: [1, null] }])(
    "treats %j as no headset",
    (raw) => {
      expect(readVrStatus(raw)).toEqual(NO_VR);
    },
  );

  test("drops wrong typed fields one by one", () => {
    expect(readVrStatus({ ...ANSWER, worn: "yes", xr_runtime: 3, source: "other", os: 1 })).toEqual(
      {
        os: "unknown",
        runtime: "SteamVR",
        runtimes: ["SteamVR", "Oculus"],
        xr_runtime: null,
        worn: null,
        source: "none",
      },
    );
  });
});

describe("getVrStatus", () => {
  test("asks /api/vr/status and reads the answer", async () => {
    const { calls } = mockFetch(() => ANSWER);
    await expect(getVrStatus()).resolves.toEqual(ANSWER);
    expect(calls.map((u) => u.pathname)).toEqual(["/api/vr/status"]);
  });
});

describe("polling", () => {
  test("polls every 5 seconds while visible and never while hidden", () => {
    expect(VR_POLL_MS).toBe(5000);
    expect(vrStatusOptions(true)).toMatchObject({ enabled: true, refetchInterval: 5000 });
    expect(vrStatusOptions(false)).toMatchObject({ enabled: false, refetchInterval: false });
  });

  test("a tab that starts hidden does not fetch until it becomes visible", async () => {
    const { calls } = mockFetch(() => ANSWER);
    setVisibility("hidden");
    const { result } = renderHook(() => useVrStatus(useVisible()), { wrapper: clientWrapper() });
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });
    expect(calls).toHaveLength(0);
    act(() => setVisibility("visible"));
    await waitFor(() => expect(result.current.data?.runtime).toBe("SteamVR"));
    expect(calls.map((u) => u.pathname)).toEqual(["/api/vr/status"]);
  });

  test("useVisible follows the visibility events", () => {
    const { result } = renderHook(() => useVisible());
    expect(result.current).toBe(true);
    act(() => setVisibility("hidden"));
    expect(result.current).toBe(false);
    act(() => setVisibility("visible"));
    expect(result.current).toBe(true);
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx --prefix frontend vitest run --root frontend tests/vrstatus.test.tsx`
Expected: FAIL: `Failed to resolve import "../src/vr/status"`.

- [ ] **Step 3: Implement**

Create `frontend/src/vr/status.ts`:

```ts
// The headset runtime status from GET /api/vr/status, polled while the tab is visible.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { request } from "../api/client";

export const VR_POLL_MS = 5000;

export interface VrStatus {
  os: string;
  runtime: string | null;
  runtimes: string[];
  xr_runtime: string | null;
  worn: boolean | null;
  source: "agent" | "local" | "none";
}

export const NO_VR: VrStatus = {
  os: "unknown",
  runtime: null,
  runtimes: [],
  xr_runtime: null,
  worn: null,
  source: "none",
};

/** Tolerant parse: any field of the wrong type falls back to its "no headset" value. */
export function readVrStatus(raw: unknown): VrStatus {
  const r = (typeof raw === "object" && raw !== null ? raw : {}) as Record<string, unknown>;
  const runtimes = Array.isArray(r.runtimes) ? r.runtimes : [];
  if (!runtimes.every((x) => typeof x === "string")) return NO_VR;
  const source = r.source === "agent" || r.source === "local" ? r.source : "none";
  return {
    os: typeof r.os === "string" ? r.os : "unknown",
    runtime: (runtimes[0] as string | undefined) ?? null,
    runtimes: runtimes as string[],
    xr_runtime: typeof r.xr_runtime === "string" ? r.xr_runtime : null,
    worn: typeof r.worn === "boolean" ? r.worn : null,
    source,
  };
}

export const getVrStatus = (signal?: AbortSignal): Promise<VrStatus> =>
  request<unknown>("GET", "/api/vr/status", undefined, signal).then(readVrStatus);

export const vrKeys = { status: ["vr", "status"] as const };

export function vrStatusOptions(visible: boolean) {
  return {
    queryKey: vrKeys.status,
    queryFn: ({ signal }: { signal: AbortSignal }) => getVrStatus(signal),
    enabled: visible,
    refetchInterval: visible ? VR_POLL_MS : (false as const),
    staleTime: VR_POLL_MS,
    retry: false,
  };
}

export function useVrStatus(visible: boolean) {
  return useQuery(vrStatusOptions(visible));
}

/** True while the tab is in view; the status poll stops while it is hidden. */
export function useVisible(): boolean {
  const [visible, setVisible] = useState(() => document.visibilityState !== "hidden");
  useEffect(() => {
    const update = () => setVisible(document.visibilityState !== "hidden");
    document.addEventListener("visibilitychange", update);
    return () => document.removeEventListener("visibilitychange", update);
  }, []);
  return visible;
}
```

Create `frontend/src/vr/README.md`:

```markdown
# vr

The VR layout: mode decision, headset status, screens and the CSS hooks they use. See [the VR mode design](../../../docs/superpowers/specs/2026-10-28-vr-mode-design.md).

1. `status.ts`: `GET /api/vr/status` client, query options and the 5 s visibility-aware poll.
```

- [ ] **Step 4: Run it to see it pass**

Run: `npx --prefix frontend vitest run --root frontend tests/vrstatus.test.tsx`
Expected: PASS, 14 passed.

- [ ] **Step 5: Type check and lint the new files**

Run: `npm --prefix frontend run typecheck`
Expected: exit 0.

- [ ] **Step 6: Commit**

Commit: main thread runs `task st:commit -- -m "feat(vr): frontend headset status client and visibility-aware poll" frontend/src/vr frontend/tests/vrstatus.test.tsx`
