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
