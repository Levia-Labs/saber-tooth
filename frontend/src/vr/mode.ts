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

/** `/vr` and below, or `?mode=vr`, is VR; `?mode=desktop` is desktop and beats the path. Case-insensitive. */
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
    const value = storage?.getItem(STORAGE_KEY)?.toLowerCase();
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
  if (/^\/jobs\/?$/i.test(pathname)) return "/vr/jobs";
  const map = /^\/maps\/([^/]+)\/?$/i.exec(pathname);
  return map ? `/vr/maps/${map[1]}` : pathname;
}

/** The desktop twin of a VR path; any other path is returned unchanged. */
export function desktopPath(pathname: string): string {
  if (/^\/vr\/?$/i.test(pathname)) return "/";
  if (/^\/vr\/beatsaver\/?$/i.test(pathname)) return "/beatsaver";
  if (/^\/vr\/jobs\/?$/i.test(pathname)) return "/jobs";
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
