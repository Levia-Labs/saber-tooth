import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test } from "vitest";
import { FACETS, item, mockFetch, renderApp } from "./helpers";

const RUNNING = {
  os: "windows",
  runtimes: ["SteamVR"],
  xr_runtime: null,
  worn: null,
  source: "agent",
};
const BANNER = "Headset in use: switch to VR layout?";

function api(status: unknown = {}) {
  return mockFetch((url) => {
    if (url.pathname === "/api/vr/status") return status;
    if (url.pathname === "/api/maps") return { items: [item(1)], total: 1, offset: 0, limit: 40 };
    if (url.pathname === "/api/maps/facets") return FACETS;
    if (url.pathname === "/api/maps/id0000000001") return item(1);
    if (url.pathname === "/api/maps/id0000000001/proposals") return [];
    return {};
  });
}

const ui = () => document.documentElement.dataset.ui;

afterEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
});

describe("suggestion toast", () => {
  test("appears when a headset runtime is active and nothing chose a mode", async () => {
    api(RUNNING);
    renderApp("/");
    expect(await screen.findByText(BANNER)).toBeInTheDocument();
    expect(screen.getByText(/SteamVR/)).toBeInTheDocument();
    expect(screen.getByText(BANNER).closest(".toast")).not.toBeNull();
    expect(screen.getByRole("banner")).not.toHaveTextContent(BANNER);
  });

  test("accepting switches to the VR layout and remembers it", async () => {
    api(RUNNING);
    const user = userEvent.setup();
    const { router } = renderApp("/");
    await screen.findByText(BANNER);
    await user.click(screen.getByRole("button", { name: "Switch" }));
    expect(await screen.findByRole("heading", { name: "Library", level: 1 })).toBeInTheDocument();
    await waitFor(() => expect(router.state.location.pathname).toBe("/vr"));
    expect(ui()).toBe("vr");
    expect(window.localStorage.getItem("saber-tooth.ui-mode")).toBe("vr");
    expect(screen.queryByText(BANNER)).toBeNull();
  });

  test("dismissing hides it for the session", async () => {
    api(RUNNING);
    const user = userEvent.setup();
    renderApp("/");
    await screen.findByText(BANNER);
    await user.click(screen.getByRole("button", { name: "Not now" }));
    expect(screen.queryByText(BANNER)).toBeNull();
    expect(window.sessionStorage.getItem("saber-tooth.vr-banner-dismissed")).toBe("1");
    expect(ui()).toBeUndefined();
  });

  test("closing it with X counts as Not now and it does not return on later polls", async () => {
    api(RUNNING);
    const user = userEvent.setup();
    renderApp("/");
    await screen.findByText(BANNER);
    const toast = screen.getByText(BANNER).closest<HTMLElement>(".toast");
    await user.click(within(toast!).getByRole("button", { name: "Dismiss" }));
    expect(screen.queryByText(BANNER)).toBeNull();
    expect(window.sessionStorage.getItem("saber-tooth.vr-banner-dismissed")).toBe("1");
    await new Promise((resolve) => setTimeout(resolve, 5200));
    expect(screen.queryByText(BANNER)).toBeNull();
  }, 15_000);

  test("switching the layout from the masthead withdraws it", async () => {
    api(RUNNING);
    const user = userEvent.setup();
    renderApp("/");
    await screen.findByText(BANNER);
    await user.click(within(screen.getByRole("banner")).getByRole("button", { name: "VR" }));
    await waitFor(() => expect(screen.queryByText(BANNER)).toBeNull());
  });

  test("does not appear when the helper reports no runtime", async () => {
    const { calls } = api({ ...RUNNING, runtimes: [] });
    renderApp("/");
    await waitFor(() => expect(calls.some((u) => u.pathname === "/api/vr/status")).toBe(true));
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(screen.queryByText(BANNER)).toBeNull();
  });

  test("does not appear on a /vr address", async () => {
    const { calls } = api(RUNNING);
    renderApp("/vr");
    await waitFor(() => expect(calls.some((u) => u.pathname === "/api/vr/status")).toBe(true));
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(screen.queryByText(BANNER)).toBeNull();
  });
});

describe("masthead switch", () => {
  test("sits in the header as a Layout group of two toggles, with no navigation or extra links", async () => {
    api();
    renderApp("/");
    const header = await screen.findByRole("banner");
    const group = within(header).getByRole("group", { name: "Layout" });
    expect(within(group).getByRole("button", { name: "Desktop" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(within(group).getByRole("button", { name: "VR" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(within(header).queryByRole("navigation")).toBeNull();
    expect(within(header).getAllByRole("link")).toHaveLength(2);
  });

  test("VR opens the VR twin of a map page and Desktop comes back to it", async () => {
    api();
    const user = userEvent.setup();
    const { router } = renderApp("/maps/id0000000001");
    await screen.findByRole("heading", { name: "Song 1" });
    await user.click(screen.getByRole("button", { name: "VR" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/vr/maps/id0000000001"));
    expect(ui()).toBe("vr");
    expect(screen.getByRole("button", { name: "VR" })).toHaveAttribute("aria-pressed", "true");
    await user.click(screen.getByRole("button", { name: "Desktop" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/maps/id0000000001"));
    expect(ui()).toBeUndefined();
    expect(window.localStorage.getItem("saber-tooth.ui-mode")).toBe("desktop");
  });

  test("a page without a VR twin stays put but gets the VR styling", async () => {
    api();
    const user = userEvent.setup();
    const { router } = renderApp("/about");
    await screen.findByRole("heading", { name: "About saber-tooth" });
    await user.click(screen.getByRole("button", { name: "VR" }));
    await waitFor(() => expect(ui()).toBe("vr"));
    expect(router.state.location.pathname).toBe("/about");
  });

  test("a remembered VR choice opens the VR library from the plain address", async () => {
    window.localStorage.setItem("saber-tooth.ui-mode", "vr");
    api();
    const { router } = renderApp("/");
    await waitFor(() => expect(router.state.location.pathname).toBe("/vr"));
    expect(await screen.findByRole("heading", { name: "Song 1" })).toBeInTheDocument();
    expect(ui()).toBe("vr");
  });

  test("?mode=desktop wins over a remembered VR choice", async () => {
    window.localStorage.setItem("saber-tooth.ui-mode", "vr");
    api();
    const { router } = renderApp("/?mode=desktop");
    await screen.findByRole("banner");
    expect(router.state.location.pathname).toBe("/");
    expect(ui()).toBeUndefined();
  });
});
