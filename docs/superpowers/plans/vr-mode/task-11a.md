# Task 11: `VrMode` context, redirects and the `data-ui` attribute

The provider applies Task 10's decision to the running app. It reads the location, the remembered choice and the status poll (Task 9), exposes `{ mode, status, xrSupported, showBanner, choose, dismissBanner }`, sets `data-ui="vr"` on the root element (`document.documentElement`, so portals such as dialogs are covered) in VR mode, and keeps the address in step with the mode: in VR mode a desktop Library, BeatSaver or map path moves to its `/vr` twin; in desktop mode a `/vr` path (reachable only with `?mode=desktop`) moves back. Paths without a VR twin (`/about`, `/new`, playlists) stay put. The banner shows only when nothing decided the mode (source `default`) and the status reports a runtime. The provider mounts in `Shell` in Task 17, after the VR screens and routes exist.

**Files:**

- Create: `frontend/src/vr/VrMode.tsx`
- Modify: `frontend/src/vr/README.md` (append one list item)
- Test: `frontend/tests/vrmode.test.tsx`

**Interfaces:**

Consumes: `decideMode`, `desktopPath`, `vrPath`, `readStored`, `writeStored`, `readDismissed`, `writeDismissed`, `supportsImmersiveVr`, `Mode` (`vr/mode.ts`); `NO_VR`, `useVisible`, `useVrStatus`, `VrStatus` (`vr/status.ts`); `useLocation`, `useNavigate` (`react-router`).

Produces (`vr/VrMode.tsx`):

1. `interface VrModeValue { mode: Mode; status: VrStatus; xrSupported: boolean; showBanner: boolean; choose: (mode: Mode) => void; dismissBanner: () => void }`.
2. `VrModeProvider({ children }: { children: ReactNode }): JSX.Element`; it must sit inside a router and a `QueryClientProvider`.
3. `useVrMode(): VrModeValue`; outside a provider it returns the neutral value (desktop, no headset, `choose` and `dismissBanner` do nothing), so screens render in isolated tests.

`choose(next)` writes the remembered choice, drops any `mode` query from the address (an explicit query would otherwise outrank the choice), and navigates to `vrPath` or `desktopPath` of the current path. `dismissBanner()` writes the session dismissal.

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/vrmode.test.tsx`:

```tsx
import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, describe, expect, test, vi } from "vitest";
import { makeQueryClient } from "../src/App";
import { VrModeProvider, useVrMode } from "../src/vr/VrMode";
import { mockFetch } from "./helpers";

const QUEST_UA =
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) OculusBrowser/33.0.0.0.0 Chrome/126.0.0.0 VR Safari/537.36";
const RUNNING = {
  os: "windows",
  runtimes: ["SteamVR"],
  xr_runtime: null,
  worn: null,
  source: "agent",
};

function Probe() {
  const vr = useVrMode();
  const { pathname, search } = useLocation();
  return (
    <div>
      <span data-testid="mode">{vr.mode}</span>
      <span data-testid="where">{pathname + search}</span>
      <span data-testid="xr">{String(vr.xrSupported)}</span>
      <span data-testid="banner">{String(vr.showBanner)}</span>
      <span data-testid="runtime">{String(vr.status.runtime)}</span>
      <button onClick={() => vr.choose("vr")}>choose vr</button>
      <button onClick={() => vr.choose("desktop")}>choose desktop</button>
      <button onClick={vr.dismissBanner}>dismiss</button>
    </div>
  );
}

function mount(url: string, status: unknown = {}) {
  const api = mockFetch((u) => (u.pathname === "/api/vr/status" ? status : {}));
  const view = render(
    <QueryClientProvider client={makeQueryClient()}>
      <MemoryRouter initialEntries={[url]}>
        <VrModeProvider>
          <Probe />
        </VrModeProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { ...api, ...view };
}

const text = (id: string) => screen.getByTestId(id).textContent;

afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
  window.sessionStorage.clear();
  Reflect.deleteProperty(navigator, "xr");
});

describe("mode and data-ui", () => {
  test("the library path is desktop by default and sets no attribute", () => {
    mount("/");
    expect(text("mode")).toBe("desktop");
    expect(document.documentElement.dataset.ui).toBeUndefined();
  });

  test("a /vr path is VR and sets data-ui=vr on the root element", () => {
    mount("/vr/maps/abc");
    expect(text("mode")).toBe("vr");
    expect(document.documentElement.dataset.ui).toBe("vr");
  });

  test("?mode=vr on the library moves to /vr and keeps the query", async () => {
    mount("/?mode=vr");
    await waitFor(() => expect(text("where")).toBe("/vr?mode=vr"));
    expect(text("mode")).toBe("vr");
  });

  test("a remembered VR choice moves a desktop path to its VR twin", async () => {
    window.localStorage.setItem("saber-tooth.ui-mode", "vr");
    mount("/maps/abc");
    await waitFor(() => expect(text("where")).toBe("/vr/maps/abc"));
  });

  test("a path without a VR twin stays where it is in VR mode", async () => {
    window.localStorage.setItem("saber-tooth.ui-mode", "vr");
    mount("/about");
    expect(text("mode")).toBe("vr");
    expect(text("where")).toBe("/about");
    expect(document.documentElement.dataset.ui).toBe("vr");
  });

  test("a standalone headset browser gets VR on the library path", async () => {
    vi.spyOn(window.navigator, "userAgent", "get").mockReturnValue(QUEST_UA);
    mount("/beatsaver");
    await waitFor(() => expect(text("where")).toBe("/vr/beatsaver"));
  });

  test("a remembered desktop choice beats the headset browser", () => {
    window.localStorage.setItem("saber-tooth.ui-mode", "desktop");
    vi.spyOn(window.navigator, "userAgent", "get").mockReturnValue(QUEST_UA);
    mount("/");
    expect(text("mode")).toBe("desktop");
  });

  test("?mode=desktop on a /vr path returns to the desktop twin without the attribute", async () => {
    mount("/vr?mode=desktop");
    await waitFor(() => expect(text("where")).toBe("/?mode=desktop"));
    expect(text("mode")).toBe("desktop");
    expect(document.documentElement.dataset.ui).toBeUndefined();
  });
});

describe("choose", () => {
  test("choosing VR remembers it, drops ?mode and opens the VR twin", async () => {
    const user = userEvent.setup();
    mount("/maps/abc?mode=desktop&x=1");
    await user.click(screen.getByRole("button", { name: "choose vr" }));
    await waitFor(() => expect(text("where")).toBe("/vr/maps/abc?x=1"));
    expect(window.localStorage.getItem("saber-tooth.ui-mode")).toBe("vr");
    expect(text("mode")).toBe("vr");
  });

  test("choosing desktop on a VR screen remembers it and clears the attribute", async () => {
    const user = userEvent.setup();
    mount("/vr");
    await user.click(screen.getByRole("button", { name: "choose desktop" }));
    await waitFor(() => expect(text("where")).toBe("/"));
    expect(window.localStorage.getItem("saber-tooth.ui-mode")).toBe("desktop");
    expect(text("mode")).toBe("desktop");
    expect(document.documentElement.dataset.ui).toBeUndefined();
  });
});

describe("banner", () => {
  test("shows when nothing decided the mode and a runtime is active", async () => {
    mount("/", RUNNING);
    await waitFor(() => expect(text("banner")).toBe("true"));
    expect(text("runtime")).toBe("SteamVR");
  });

  test("stays hidden when the helper reports no runtime", async () => {
    const { calls } = mount("/", { ...RUNNING, runtimes: [] });
    await waitFor(() => expect(calls.some((u) => u.pathname === "/api/vr/status")).toBe(true));
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(text("runtime")).toBe("null");
    expect(text("banner")).toBe("false");
  });

  test("a remembered desktop choice or ?mode=desktop never shows the banner", async () => {
    window.localStorage.setItem("saber-tooth.ui-mode", "desktop");
    mount("/", RUNNING);
    await waitFor(() => expect(text("runtime")).toBe("SteamVR"));
    expect(text("banner")).toBe("false");
  });

  test("an explicit ?mode=desktop never shows the banner", async () => {
    mount("/?mode=desktop", RUNNING);
    await waitFor(() => expect(text("runtime")).toBe("SteamVR"));
    expect(text("banner")).toBe("false");
  });

  test("dismiss hides it for the session, also after a remount", async () => {
    const user = userEvent.setup();
    const first = mount("/", RUNNING);
    await waitFor(() => expect(text("banner")).toBe("true"));
    await user.click(screen.getByRole("button", { name: "dismiss" }));
    expect(text("banner")).toBe("false");
    first.unmount();
    mount("/", RUNNING);
    await waitFor(() => expect(text("runtime")).toBe("SteamVR"));
    expect(text("banner")).toBe("false");
  });

  test("accepting switches to VR and remembers it", async () => {
    const user = userEvent.setup();
    mount("/", RUNNING);
    await waitFor(() => expect(text("banner")).toBe("true"));
    await user.click(screen.getByRole("button", { name: "choose vr" }));
    await waitFor(() => expect(text("where")).toBe("/vr"));
    expect(window.localStorage.getItem("saber-tooth.ui-mode")).toBe("vr");
    expect(text("banner")).toBe("false");
  });
});

describe("WebXR support", () => {
  test("is read once and exposed", async () => {
    const isSessionSupported = vi.fn(async () => true);
    Object.defineProperty(navigator, "xr", { configurable: true, value: { isSessionSupported } });
    mount("/");
    await waitFor(() => expect(text("xr")).toBe("true"));
    expect(isSessionSupported).toHaveBeenCalledTimes(1);
    expect(isSessionSupported).toHaveBeenCalledWith("immersive-vr");
  });

  test("a missing API is unsupported without a console error", async () => {
    const errors = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const { calls } = mount("/");
    await waitFor(() => expect(calls.some((u) => u.pathname === "/api/vr/status")).toBe(true));
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(text("xr")).toBe("false");
    expect(errors).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx --prefix frontend vitest run --root frontend tests/vrmode.test.tsx`
Expected: FAIL: `Failed to resolve import "../src/vr/VrMode"`.

Continued in [task-11b.md](task-11b.md).
