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
