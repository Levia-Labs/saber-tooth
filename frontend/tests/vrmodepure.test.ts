import fc from "fast-check";
import { afterEach, describe, expect, test, vi } from "vitest";
import {
  DISMISS_KEY,
  STORAGE_KEY,
  decideMode,
  desktopPath,
  isHeadsetBrowser,
  readDismissed,
  readStored,
  supportsImmersiveVr,
  urlMode,
  vrPath,
  writeDismissed,
  writeStored,
} from "../src/vr/mode";

const DESKTOP_UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";
const QUEST_UA =
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) OculusBrowser/33.0.0.0.0 SamsungBrowser/4.0 Chrome/126.0.0.0 VR Safari/537.36";
const PICO_UA =
  "Mozilla/5.0 (Linux; Android 12; PICO 4 Build/SQ3A) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.5195.136 Mobile Safari/537.36 PicoBrowser/3.0.2";
const WOLVIC_UA =
  "Mozilla/5.0 (Android 12; Mobile VR; rv:122.0) Gecko/122.0 Firefox/122.0 Wolvic/1.6.2";

afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
  window.sessionStorage.clear();
});

describe("urlMode", () => {
  test.each([
    ["/vr", "", "vr"],
    ["/vr/", "", "vr"],
    ["/vr/maps/abc", "", "vr"],
    ["/VR/beatsaver", "", "vr"],
    ["/", "?mode=vr", "vr"],
    ["/", "?mode=VR", "vr"],
    ["/", "?mode=desktop", "desktop"],
    ["/vr", "?mode=desktop", "desktop"],
    ["/vr/maps/abc", "?mode=desktop", "desktop"],
  ])("%s %s gives %s", (pathname, search, expected) => {
    expect(urlMode(pathname, search)).toBe(expected);
  });

  test("a lookalike path or an unknown mode value does not force a mode", () => {
    for (const path of ["/vrx", "/vr-maps", "/vrs/abc", "/", "/maps/vr", "/about", "/new"]) {
      expect(urlMode(path, "")).toBeNull();
    }
    for (const search of ["?mode=vr2", "?mode=", "?mode=xr", "?mode=%00", "?modes=vr", "?mode"]) {
      expect(urlMode("/", search)).toBeNull();
    }
    expect(urlMode("/vrx", "?mode=bogus")).toBeNull();
  });

  test("any word glued to /vr is not the VR path", () => {
    fc.assert(
      fc.property(fc.stringMatching(/^[a-z0-9_-]{1,10}$/), (tail) => {
        expect(urlMode(`/vr${tail}`, "")).toBeNull();
      }),
    );
  });

  test("never throws on arbitrary input", () => {
    fc.assert(
      fc.property(fc.string(), fc.string(), (path, search) => {
        expect([null, "vr", "desktop"]).toContain(urlMode(path, search));
      }),
    );
  });
});

describe("decideMode", () => {
  const base = { pathname: "/", search: "", stored: null, userAgent: DESKTOP_UA } as const;

  test.each([
    ["url beats stored", { pathname: "/vr", stored: "desktop" }, { mode: "vr", source: "url" }],
    [
      "url beats the device",
      { search: "?mode=desktop", userAgent: QUEST_UA },
      { mode: "desktop", source: "url" },
    ],
    [
      "stored beats the device",
      { stored: "desktop", userAgent: QUEST_UA },
      { mode: "desktop", source: "stored" },
    ],
    ["stored vr on a desktop browser", { stored: "vr" }, { mode: "vr", source: "stored" }],
    ["the device beats the default", { userAgent: QUEST_UA }, { mode: "vr", source: "device" }],
    ["otherwise desktop", {}, { mode: "desktop", source: "default" }],
  ] as const)("%s", (_name, patch, expected) => {
    expect(decideMode({ ...base, ...patch } as Parameters<typeof decideMode>[0])).toEqual(expected);
  });
});

describe("isHeadsetBrowser", () => {
  test("recognises the Quest, Pico and Wolvic browsers", () => {
    for (const ua of [QUEST_UA, PICO_UA, WOLVIC_UA]) expect(isHeadsetBrowser(ua)).toBe(true);
    expect(isHeadsetBrowser("Mozilla/5.0 (X11; Linux x86_64) Meta Quest 3 Chrome/120")).toBe(true);
  });

  test("ignores ordinary desktop and phone browsers", () => {
    for (const ua of [
      DESKTOP_UA,
      "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 Version/17.5 Safari/605.1.15",
      "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/126.0.0.0 Mobile Safari/537.36",
      "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
      "",
    ]) {
      expect(isHeadsetBrowser(ua)).toBe(false);
    }
  });
});

describe("stored choice", () => {
  test("round trips and treats garbage as nothing", () => {
    expect(readStored()).toBeNull();
    writeStored("vr");
    expect(readStored()).toBe("vr");
    writeStored("desktop");
    expect(readStored()).toBe("desktop");
    for (const junk of ["", "vr ", "1", "null", '{"mode":"vr"}']) {
      window.localStorage.setItem(STORAGE_KEY, junk);
      expect(readStored()).toBeNull();
    }
  });

  test("a stored value in any letter case is honoured as lower case", () => {
    for (const [raw, expected] of [
      ["VR", "vr"],
      ["Vr", "vr"],
      ["DESKTOP", "desktop"],
      ["Desktop", "desktop"],
    ] as const) {
      window.localStorage.setItem(STORAGE_KEY, raw);
      expect(readStored()).toBe(expected);
    }
  });

  test("storage that throws on read and write still decides a mode", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(readStored()).toBeNull();
    expect(() => writeStored("vr")).not.toThrow();
    expect(readDismissed()).toBe(false);
    expect(() => writeDismissed()).not.toThrow();
    const stored = readStored();
    expect(decideMode({ pathname: "/", search: "", stored, userAgent: QUEST_UA }).mode).toBe("vr");
    expect(decideMode({ pathname: "/", search: "", stored, userAgent: DESKTOP_UA }).mode).toBe(
      "desktop",
    );
  });

  test("a storage object that cannot be reached at all is treated as empty", () => {
    vi.spyOn(window, "localStorage", "get").mockImplementation(() => {
      throw new DOMException("denied", "SecurityError");
    });
    vi.spyOn(window, "sessionStorage", "get").mockImplementation(() => {
      throw new DOMException("denied", "SecurityError");
    });
    expect(readStored()).toBeNull();
    expect(() => writeStored("desktop")).not.toThrow();
    expect(readDismissed()).toBe(false);
    expect(() => writeDismissed()).not.toThrow();
  });

  test("the banner dismissal lives in session storage", () => {
    expect(readDismissed()).toBe(false);
    writeDismissed();
    expect(readDismissed()).toBe(true);
    expect(window.sessionStorage.getItem(DISMISS_KEY)).not.toBeNull();
    expect(window.localStorage.getItem(DISMISS_KEY)).toBeNull();
  });
});

describe("path mapping", () => {
  test.each([
    ["/", "/vr"],
    ["", "/vr"],
    ["/beatsaver", "/vr/beatsaver"],
    ["/beatsaver/", "/vr/beatsaver"],
    ["/maps/abc123", "/vr/maps/abc123"],
    ["/about", "/about"],
    ["/new", "/new"],
    ["/beatsaver/playlists", "/beatsaver/playlists"],
    ["/maps/a/b", "/maps/a/b"],
  ])("vrPath(%j) is %s", (from, to) => {
    expect(vrPath(from)).toBe(to);
  });

  test.each([
    ["/vr", "/"],
    ["/vr/", "/"],
    ["/vr/beatsaver", "/beatsaver"],
    ["/vr/maps/abc123", "/maps/abc123"],
    ["/about", "/about"],
    ["/vrx", "/vrx"],
  ])("desktopPath(%j) is %s", (from, to) => {
    expect(desktopPath(from)).toBe(to);
  });

  test("a map path survives the round trip and both mappings are idempotent", () => {
    fc.assert(
      fc.property(fc.stringMatching(/^[A-Za-z0-9_%-]{1,24}$/), fc.string(), (id, other) => {
        expect(desktopPath(vrPath(`/maps/${id}`))).toBe(`/maps/${id}`);
        expect(vrPath(desktopPath(`/vr/maps/${id}`))).toBe(`/vr/maps/${id}`);
        expect(vrPath(vrPath(`/${other}`))).toBe(vrPath(`/${other}`));
        expect(desktopPath(desktopPath(`/${other}`))).toBe(desktopPath(`/${other}`));
      }),
    );
  });
});

describe("supportsImmersiveVr", () => {
  const nav = (xr: unknown) => ({ xr }) as unknown as Navigator;

  test("is true only when the browser says immersive-vr is supported", async () => {
    const isSessionSupported = vi.fn(async (mode: string) => mode === "immersive-vr");
    await expect(supportsImmersiveVr(nav({ isSessionSupported }))).resolves.toBe(true);
    expect(isSessionSupported).toHaveBeenCalledWith("immersive-vr");
    await expect(supportsImmersiveVr(nav({ isSessionSupported: async () => false }))).resolves.toBe(
      false,
    );
    await expect(supportsImmersiveVr(nav({ isSessionSupported: async () => "yes" }))).resolves.toBe(
      false,
    );
  });

  test("a missing, blocked or throwing API is unsupported and logs no console error", async () => {
    const errors = vi.spyOn(console, "error").mockImplementation(() => undefined);
    await expect(supportsImmersiveVr(nav(undefined))).resolves.toBe(false);
    await expect(supportsImmersiveVr(nav({}))).resolves.toBe(false);
    await expect(
      supportsImmersiveVr(nav({ isSessionSupported: () => Promise.reject(new Error("blocked")) })),
    ).resolves.toBe(false);
    await expect(
      supportsImmersiveVr(
        nav({
          isSessionSupported: () => {
            throw new Error("sync throw");
          },
        }),
      ),
    ).resolves.toBe(false);
    await expect(supportsImmersiveVr()).resolves.toBe(false);
    expect(errors).not.toHaveBeenCalled();
  });
});
