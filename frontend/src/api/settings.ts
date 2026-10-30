// Settings, system resources and the PlaylistManager mod: types, calls and shared queries.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { request } from "./client";

export interface SystemInfo {
  cores: number;
  memory: { total: number | null; available: number | null; source: "cgroup" | "host" };
  recommended_max: number;
  fix_job_peak_mb: number;
  workers: { configured: number; running: number };
}

export interface SettingsView {
  max_concurrent_jobs: number;
  recommended_max: number;
  game_dir: string | null;
}

export type DepState = "missing" | "current" | "other";

export interface ModStatus {
  game: {
    state: "ready" | "not_mounted";
    path: string | null;
    source: "setting" | "env" | "levels" | null;
    version: string | null;
    running: boolean | null;
  };
  mount_help?: { env: string; compose: string[]; then: string };
  catalog: { state: "idle" | "loading" | "ready" | "failed" | "unsupported"; error: string | null };
  mod: {
    name: string;
    github: string;
    state: "unknown" | "missing" | "current" | "other" | "unsupported";
    installed: boolean;
    installed_version?: string | null;
    available_version?: string | null;
    dependencies?: { name: string; version: string; state: DepState }[];
    can_install: boolean;
    reason?: string | null;
  };
  install: { state: "idle" | "running" | "done" | "failed"; message: string | null };
}

export const settingsKeys = {
  system: ["system"] as const,
  settings: ["settings"] as const,
  mod: ["mods", "playlistmanager"] as const,
};

export const SYSTEM_POLL_MS = 3000;
export const MOD_POLL_MS = 1500;

export function useSystem() {
  return useQuery({
    queryKey: settingsKeys.system,
    queryFn: ({ signal }) => request<SystemInfo>("GET", "/api/system", undefined, signal),
    refetchInterval: SYSTEM_POLL_MS,
    refetchIntervalInBackground: false,
    retry: false,
  });
}

export function useSettings() {
  return useQuery({
    queryKey: settingsKeys.settings,
    queryFn: ({ signal }) => request<SettingsView>("GET", "/api/settings", undefined, signal),
    retry: false,
  });
}

/** Polls while the BeatMods list is being fetched or an install runs, then rests. */
export function useModStatus() {
  return useQuery({
    queryKey: settingsKeys.mod,
    queryFn: ({ signal }) =>
      request<ModStatus>("GET", "/api/mods/playlistmanager", undefined, signal),
    refetchInterval: (q) =>
      q.state.data?.catalog.state === "loading" || q.state.data?.install.state === "running"
        ? MOD_POLL_MS
        : false,
    retry: false,
  });
}

export function useSaveSettings() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Pick<SettingsView, "max_concurrent_jobs" | "game_dir">>) =>
      request<SettingsView>("POST", "/api/settings", body),
    onSuccess: (saved) => {
      client.setQueryData(settingsKeys.settings, saved);
      void client.invalidateQueries({ queryKey: settingsKeys.system });
      void client.invalidateQueries({ queryKey: settingsKeys.mod });
    },
  });
}

export function useInstallMod() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () =>
      request<ModStatus["install"]>("POST", "/api/mods/playlistmanager/install", {
        confirm: true,
      }),
    onSettled: () => void client.invalidateQueries({ queryKey: settingsKeys.mod }),
  });
}
