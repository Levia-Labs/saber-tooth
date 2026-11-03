import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import type { SettingsView } from "../src/api/settings";
import { mockFetch, renderApp } from "./helpers";

const SETTINGS: SettingsView = {
  max_concurrent_jobs: 1,
  recommended_max: 4,
  game_dir: null,
  crop_min_length_s: 150,
};

function serve() {
  const puts: unknown[] = [];
  mockFetch((url, init) => {
    if (url.pathname === "/api/settings") {
      if (init?.method === "POST") {
        const body = JSON.parse(String(init.body));
        puts.push(body);
        return { ...SETTINGS, ...body };
      }
      return SETTINGS;
    }
    if (url.pathname === "/api/system") {
      return {
        cores: 4,
        memory: { total: null, available: null, source: "host" },
        recommended_max: 4,
        fix_job_peak_mb: 512,
        workers: { configured: 1, running: 0 },
      };
    }
    if (url.pathname === "/api/mods/playlistmanager") {
      return {
        game: { state: "not_mounted", path: null, source: null, version: null, running: null },
        catalog: { state: "idle", error: null },
        mod: {
          name: "PlaylistManager",
          github: "https://github.com/x/y",
          state: "unknown",
          installed: false,
          can_install: false,
        },
        install: { state: "idle", message: null },
      };
    }
    return {};
  });
  return { puts };
}

describe("Qualified for crop", () => {
  test("is an mm:ss input that saves the length in seconds", async () => {
    const api = serve();
    renderApp("/settings");
    const input = await screen.findByRole("textbox", { name: "Qualified for crop" });
    expect(input).toHaveValue("2:30");
    await userEvent.clear(input);
    await userEvent.type(input, "3:05");
    await userEvent.click(screen.getByRole("button", { name: "Save length" }));
    await waitFor(() => expect(api.puts).toEqual([{ crop_min_length_s: 185 }]));
  });

  test("refuses a value that is not mm:ss", async () => {
    serve();
    renderApp("/settings");
    const input = await screen.findByRole("textbox", { name: "Qualified for crop" });
    await userEvent.clear(input);
    await userEvent.type(input, "2:75");
    expect(screen.getByRole("button", { name: "Save length" })).toBeDisabled();
  });
});
