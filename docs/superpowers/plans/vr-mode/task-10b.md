# Task 10: Mode decision, storage, path mapping and WebXR probe (pure) (part b)

Continues [task-10a.md](task-10a.md).

- [ ] **Step 3: Implement**

Create `frontend/src/vr/mode.ts`:

```ts
// Which layout to show: the pure decision, the remembered choice and the VR path mapping.
export type Mode = "vr" | "desktop";
export type ModeSource = "url" | "stored" | "device" | "default";
export interface Decision {
  mode: Mode;
  source: ModeSource;
}

export const STORAGE_KEY = "saber-tooth.ui-mode";
export const DISMISS_KEY = "saber-tooth.vr-banner-dismissed";

// Meta Quest Browser, Pico browser and Wolvic: standalone headsets that open the page directly.
const HEADSET_UA = /OculusBrowser|\bQuest\b|PicoBrowser|Wolvic/i;

export const isHeadsetBrowser = (userAgent: string): boolean => HEADSET_UA.test(userAgent);

/** `/vr` and below, or `?mode=vr`, is VR; `?mode=desktop` is desktop and beats the path. */
export function urlMode(pathname: string, search: string): Mode | null {
  const param = (new URLSearchParams(search).get("mode") ?? "").trim().toLowerCase();
  if (param === "vr" || param === "desktop") return param;
  const path = pathname.toLowerCase();
  return path === "/vr" || path.startsWith("/vr/") ? "vr" : null;
}

export function decideMode(input: {
  pathname: string;
  search: string;
  stored: Mode | null;
  userAgent: string;
}): Decision {
  const url = urlMode(input.pathname, input.search);
  if (url) return { mode: url, source: "url" };
  if (input.stored) return { mode: input.stored, source: "stored" };
  if (isHeadsetBrowser(input.userAgent)) return { mode: "vr", source: "device" };
  return { mode: "desktop", source: "default" };
}

function area(kind: "local" | "session"): Storage | null {
  try {
    return kind === "local" ? window.localStorage : window.sessionStorage;
  } catch {
    return null;
  }
}

export function readStored(storage: Storage | null = area("local")): Mode | null {
  try {
    const value = storage?.getItem(STORAGE_KEY);
    return value === "vr" || value === "desktop" ? value : null;
  } catch {
    return null;
  }
}

export function writeStored(mode: Mode, storage: Storage | null = area("local")): void {
  try {
    storage?.setItem(STORAGE_KEY, mode);
  } catch {
    /* storage blocked or full: the choice lasts for this page only */
  }
}

export function readDismissed(storage: Storage | null = area("session")): boolean {
  try {
    return storage?.getItem(DISMISS_KEY) === "1";
  } catch {
    return false;
  }
}

export function writeDismissed(storage: Storage | null = area("session")): void {
  try {
    storage?.setItem(DISMISS_KEY, "1");
  } catch {
    /* storage blocked: the banner returns on the next page load */
  }
}

/** The VR twin of a desktop path; paths without a VR screen are returned unchanged. */
export function vrPath(pathname: string): string {
  if (/^\/?$/.test(pathname)) return "/vr";
  if (/^\/beatsaver\/?$/i.test(pathname)) return "/vr/beatsaver";
  const map = /^\/maps\/([^/]+)\/?$/i.exec(pathname);
  return map ? `/vr/maps/${map[1]}` : pathname;
}

/** The desktop twin of a VR path; any other path is returned unchanged. */
export function desktopPath(pathname: string): string {
  if (/^\/vr\/?$/i.test(pathname)) return "/";
  if (/^\/vr\/beatsaver\/?$/i.test(pathname)) return "/beatsaver";
  const map = /^\/vr\/maps\/([^/]+)\/?$/i.exec(pathname);
  return map ? `/maps/${map[1]}` : pathname;
}

type XrApi = { isSessionSupported?: (mode: string) => Promise<boolean> };

/** Whether the browser reports an immersive VR session; any failure counts as unsupported. */
export async function supportsImmersiveVr(nav: Navigator = navigator): Promise<boolean> {
  try {
    const xr = (nav as Navigator & { xr?: XrApi }).xr;
    if (typeof xr?.isSessionSupported !== "function") return false;
    return (await xr.isSessionSupported("immersive-vr")) === true;
  } catch {
    return false;
  }
}
```

Append to `frontend/src/vr/README.md`:

```markdown
2. `mode.ts`: the pure mode decision (URL, remembered choice, headset browser, default), storage helpers, `/vr` path mapping and the WebXR probe.
```

- [ ] **Step 4: Run it to see it pass**

Run: `npx --prefix frontend vitest run --root frontend tests/vrmodepure.test.ts`
Expected: PASS, 42 passed.

- [ ] **Step 5: Type check**

Run: `npm --prefix frontend run typecheck`
Expected: exit 0. Formatting is applied by `task st:commit`.

- [ ] **Step 6: Commit**

Commit: main thread runs `task st:commit -- -m "feat(vr): pure mode decision, storage, path mapping and WebXR probe" frontend/src/vr frontend/tests/vrmodepure.test.ts`
