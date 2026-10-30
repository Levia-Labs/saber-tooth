import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import type { ModStatus, SettingsView, SystemInfo } from "../src/api/settings";
import { mockFetch, renderApp } from "./helpers";

const GIB = 1024 ** 3;
const SYSTEM: SystemInfo = {
  cores: 8,
  memory: { total: 16 * GIB, available: 12 * GIB, source: "cgroup" },
  recommended_max: 4,
  fix_job_peak_mb: 512,
  workers: { configured: 1, running: 0 },
};
const SETTINGS: SettingsView = { max_concurrent_jobs: 1, recommended_max: 4, game_dir: null };

const NOT_MOUNTED: ModStatus = {
  game: { state: "not_mounted", path: null, source: null, version: null, running: null },
  mount_help: {
    env: "GAME_DIR_HOST=<path to your Beat Saber folder>  (in .env next to docker-compose.yml)",
    compose: ["environment:  GAME_DIR: ${GAME_DIR_HOST:+/game}"],
    then: "Run `docker compose up -d`.",
  },
  catalog: { state: "idle", error: null },
  mod: {
    name: "PlaylistManager",
    github: "https://github.com/rithik-b/PlaylistManager",
    state: "unknown",
    installed: false,
    can_install: false,
    reason: "The game folder is not mounted.",
  },
  install: { state: "idle", message: null },
};

const READY: ModStatus = {
  game: {
    state: "ready",
    path: "/game",
    source: "env",
    version: "1.40.8",
    running: false,
  },
  catalog: { state: "ready", error: null },
  mod: {
    name: "PlaylistManager",
    github: "https://github.com/rithik-b/PlaylistManager",
    state: "missing",
    installed: false,
    installed_version: null,
    available_version: "1.7.3",
    dependencies: [
      { name: "BSIPA", version: "4.3.6", state: "current" },
      { name: "SongCore", version: "3.15.3", state: "missing" },
    ],
    can_install: true,
    reason: null,
  },
  install: { state: "idle", message: null },
};

interface Served {
  system?: SystemInfo;
  settings?: SettingsView;
  mod?: ModStatus | (() => ModStatus);
}

function serve(s: Served = {}) {
  const puts: unknown[] = [];
  const installs: unknown[] = [];
  const api = mockFetch((url, init) => {
    if (url.pathname === "/api/system") return s.system ?? SYSTEM;
    if (url.pathname === "/api/settings") {
      if (init?.method === "POST") {
        const body = JSON.parse(String(init.body));
        puts.push(body);
        return { ...(s.settings ?? SETTINGS), ...body };
      }
      return s.settings ?? SETTINGS;
    }
    if (url.pathname === "/api/mods/playlistmanager/install") {
      installs.push(JSON.parse(String(init?.body)));
      return { state: "running", message: "Downloading" };
    }
    if (url.pathname === "/api/mods/playlistmanager") {
      const mod = s.mod ?? NOT_MOUNTED;
      return typeof mod === "function" ? mod() : mod;
    }
    return {};
  });
  return { ...api, puts, installs };
}

const card = (name: string) => screen.getByRole("region", { name });

describe("settings page", () => {
  test("the tab bar has a Settings tab before About and the page keeps one h1", async () => {
    serve();
    renderApp("/settings");
    const nav = await screen.findByRole("navigation", { name: "Section" });
    const links = within(nav).getAllByRole("link");
    expect(links.map((l) => l.textContent)).toContain("Settings");
    expect(links.at(-1)).toHaveAccessibleName("About");
    expect(within(nav).getByRole("link", { name: "Settings" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  test("the VR route renders the same page", async () => {
    serve();
    renderApp("/vr/settings");
    expect(await screen.findByRole("region", { name: "Service" })).toBeInTheDocument();
    expect(document.documentElement.dataset.ui).toBe("vr");
  });

  test("the service card shows the resources and the recommended maximum", async () => {
    serve();
    renderApp("/settings");
    const service = await screen.findByRole("region", { name: "Service" });
    expect(await within(service).findByText("8 cores")).toBeInTheDocument();
    expect(within(service).getByText(/12(\.0)? GB free of 16(\.0)? GB/)).toBeInTheDocument();
    expect(within(service).getByText(/recommended maximum: 4/i)).toBeInTheDocument();
    expect(within(service).getByRole("meter", { name: "Memory in use" })).toHaveAttribute(
      "aria-valuenow",
      "25",
    );
    expect(within(service).getByRole("meter", { name: "Jobs running" })).toBeInTheDocument();
  });

  test("pending data shows an animated spinner, never loading text", async () => {
    mockFetch(() => new Promise(() => undefined));
    renderApp("/settings");
    expect(await screen.findByRole("status", { name: "Reading resources" })).toBeInTheDocument();
    expect(
      await screen.findByRole("status", { name: "Checking PlaylistManager" }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/loading/i)).toBeNull();
  });

  test("the slider is bounded by the recommended maximum and saves the new value", async () => {
    const api = serve();
    renderApp("/settings");
    const slider = await screen.findByRole("slider", { name: "Concurrent fix and scan jobs" });
    expect(slider).toHaveAttribute("min", "1");
    expect(slider).toHaveAttribute("max", "4");
    expect(slider).toHaveValue("1");
    fireEvent.change(slider, { target: { value: "3" } });
    await waitFor(() => expect(api.puts).toEqual([{ max_concurrent_jobs: 3 }]));
  });

  test("the stepper buttons change the value by one and stop at the ends", async () => {
    const api = serve({ settings: { ...SETTINGS, max_concurrent_jobs: 4 } });
    renderApp("/settings");
    const more = await screen.findByRole("button", { name: "More jobs at once" });
    expect(more).toBeDisabled();
    const fewer = screen.getByRole("button", { name: "Fewer jobs at once" });
    await userEvent.click(fewer);
    await waitFor(() => expect(api.puts).toEqual([{ max_concurrent_jobs: 3 }]));
  });

  test("with a recommended maximum of one the control is disabled and says why", async () => {
    serve({
      system: { ...SYSTEM, recommended_max: 1 },
      settings: { ...SETTINGS, recommended_max: 1 },
    });
    renderApp("/settings");
    const slider = await screen.findByRole("slider", { name: "Concurrent fix and scan jobs" });
    expect(slider).toBeDisabled();
  });

  test("the mods card explains a game folder that is not mounted, with the exact change", async () => {
    serve();
    renderApp("/settings");
    const mods = await screen.findByRole("region", { name: "Mods" });
    expect(await within(mods).findByText(/game folder is not mounted/i)).toBeInTheDocument();
    expect(within(mods).getByText(/GAME_DIR_HOST=<path/)).toBeInTheDocument();
    expect(within(mods).getByText(/GAME_DIR: \$\{GAME_DIR_HOST:\+\/game\}/)).toBeInTheDocument();
    expect(within(mods).getByRole("link", { name: /PlaylistManager on GitHub/ })).toHaveAttribute(
      "href",
      "https://github.com/rithik-b/PlaylistManager",
    );
    expect(within(mods).getByRole("button", { name: "Install" })).toBeDisabled();
  });

  test("the game folder can be saved from the mods card", async () => {
    const api = serve();
    renderApp("/settings");
    const input = await screen.findByRole("textbox", { name: "Game folder" });
    await userEvent.type(input, "/game");
    await userEvent.click(screen.getByRole("button", { name: "Save folder" }));
    await waitFor(() => expect(api.puts).toEqual([{ game_dir: "/game" }]));
  });

  test("a ready game shows the version, installed state and the dependencies", async () => {
    serve({ mod: READY });
    renderApp("/settings");
    const mods = await screen.findByRole("region", { name: "Mods" });
    expect(await within(mods).findByText(/Beat Saber 1\.40\.8/)).toBeInTheDocument();
    expect(within(mods).getByText("Not installed")).toBeInTheDocument();
    expect(within(mods).getByText(/available 1\.7\.3/i)).toBeInTheDocument();
    const deps = within(mods).getByRole("list", { name: "Dependencies" });
    expect(within(deps).getByText("SongCore")).toBeInTheDocument();
    expect(within(deps).getByText("Missing")).toBeInTheDocument();
    expect(within(deps).getByText("Installed")).toBeInTheDocument();
    expect(within(mods).getByRole("button", { name: "Install" })).toBeEnabled();
  });

  test("Install asks first and sends the confirmation only after it is accepted", async () => {
    const api = serve({ mod: READY });
    renderApp("/settings");
    const install = await screen.findByRole("button", { name: "Install" });
    await waitFor(() => expect(install).toBeEnabled());
    await userEvent.click(install);
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/close Beat Saber/i)).toBeInTheDocument();
    expect(api.installs).toEqual([]);
    await userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(api.installs).toEqual([]);
    await userEvent.click(screen.getByRole("button", { name: "Install" }));
    await userEvent.click(
      within(await screen.findByRole("dialog")).getByRole("button", { name: "Install" }),
    );
    await waitFor(() => expect(api.installs).toEqual([{ confirm: true }]));
  });

  test("a running install shows a spinner and disables the button", async () => {
    serve({ mod: { ...READY, install: { state: "running", message: "Downloading" } } });
    renderApp("/settings");
    const mods = await screen.findByRole("region", { name: "Mods" });
    await within(mods).findByText("Downloading");
    expect(within(mods).getByRole("button", { name: "Install" })).toBeDisabled();
    expect(within(mods).getAllByRole("status").length).toBeGreaterThan(0);
  });

  test("a failed install shows its message in an alert", async () => {
    serve({ mod: { ...READY, install: { state: "failed", message: "hash mismatch" } } });
    renderApp("/settings");
    expect(await screen.findByRole("alert")).toHaveTextContent("hash mismatch");
  });

  test("a blocked install shows the reason", async () => {
    serve({
      mod: {
        ...READY,
        mod: { ...READY.mod, can_install: false, reason: "Beat Saber is running; close it first." },
      },
    });
    renderApp("/settings");
    const mods = await screen.findByRole("region", { name: "Mods" });
    expect(await within(mods).findByText(/Beat Saber is running/)).toBeInTheDocument();
    expect(within(mods).getByRole("button", { name: "Install" })).toBeDisabled();
  });

  test("a catalogue that is still being fetched shows a spinner", async () => {
    serve({ mod: { ...READY, catalog: { state: "loading", error: null } } });
    renderApp("/settings");
    const mods = await screen.findByRole("region", { name: "Mods" });
    await waitFor(() =>
      expect(within(mods).getByRole("status", { name: "Checking BeatMods" })).toBeInTheDocument(),
    );
  });

  test("an unsupported game version is stated", async () => {
    serve({
      mod: {
        ...READY,
        catalog: { state: "unsupported", error: "no build" },
        mod: {
          ...READY.mod,
          state: "unsupported",
          can_install: false,
          reason: "No verified PlaylistManager build for Beat Saber 1.40.8.",
        },
      },
    });
    renderApp("/settings");
    expect(await screen.findByText(/No verified PlaylistManager build/)).toBeInTheDocument();
    expect(card("Mods")).toBeInTheDocument();
  });
});
