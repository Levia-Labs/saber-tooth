import fc from "fast-check";
import { describe, expect, test } from "vitest";
import {
  backHref,
  formatOrigin,
  mapHref,
  originSearch,
  originTab,
  playlistHref,
  tabOfHref,
  parseOrigin,
  type Origin,
} from "../src/lib/backlink";

const id = fc.stringMatching(/^[A-Za-z0-9][A-Za-z0-9_.-]{0,40}$/);
const origin: fc.Arbitrary<Origin> = fc.oneof(
  fc.constantFrom<Origin>({ kind: "library" }, { kind: "jobs" }, { kind: "playlists" }),
  id.map((i): Origin => ({ kind: "playlist", id: i })),
  id.map((i): Origin => ({ kind: "bs-playlist", id: i })),
);

describe("backlink", () => {
  test("an origin survives format and parse", () => {
    fc.assert(
      fc.property(origin, (o) => {
        expect(parseOrigin(formatOrigin(o))).toEqual(o);
      }),
    );
  });

  test("any text parses to a valid origin and never throws", () => {
    fc.assert(
      fc.property(fc.string(), (raw) => {
        const o = parseOrigin(raw);
        expect(parseOrigin(formatOrigin(o))).toEqual(o);
      }),
    );
  });

  test("a missing or malformed origin is the library", () => {
    for (const raw of [null, undefined, "", "nope", "playlist:", "playlist:../x", "jobs:1"]) {
      expect(parseOrigin(raw)).toEqual({ kind: "library" });
    }
  });

  test("the map address round-trips the origin, back query and tab", () => {
    fc.assert(
      fc.property(origin, fc.string(), (o, back) => {
        const url = new URL(mapHref("id1", { from: o, back, tab: "crop" }), "http://x");
        expect(url.pathname).toBe("/maps/id1");
        expect(url.searchParams.get("tab")).toBe("crop");
        expect(parseOrigin(url.searchParams.get("from"))).toEqual(o);
        expect(url.searchParams.get("back") ?? "").toBe(back.replace(/^\?/, ""));
      }),
    );
  });

  test("each origin returns to its own list", () => {
    expect(backHref({ kind: "jobs" }, "status=failed&sort=time")).toBe(
      "/jobs?status=failed&sort=time",
    );
    expect(backHref({ kind: "jobs" })).toBe("/jobs");
    expect(backHref({ kind: "playlists" })).toBe("/playlists");
    expect(backHref({ kind: "playlist", id: "p1" })).toBe("/playlists/p1");
    expect(backHref({ kind: "bs-playlist", id: "ab1" }, "q=x")).toBe(
      "/beatsaver/playlists/ab1?q=x",
    );
    expect(backHref({ kind: "library" }, "q=x")).toBe("/?q=x");
  });

  test("the active section tab follows the origin", () => {
    expect(originTab({ kind: "jobs" })).toBe("jobs");
    expect(originTab({ kind: "playlist", id: "p" })).toBe("playlists");
    expect(originTab({ kind: "bs-playlist", id: "p" })).toBe("beatsaver");
  });

  test("originSearch keeps only from and back", () => {
    const p = new URLSearchParams("tab=crop&from=jobs&back=a%3Db");
    expect(originSearch(p)).toBe("?from=jobs&back=a%3Db");
    expect(originSearch(new URLSearchParams("tab=crop"))).toBe("");
  });
});

describe("playlist links", () => {
  test("a playlist opened from the Playlists list carries from and the list query", () => {
    expect(playlistHref("a", { query: "" })).toBe("/playlists/a?from=playlists");
    expect(playlistHref("a b", { query: "?x=1&y=2" })).toBe(
      "/playlists/a%20b?from=playlists&back=x%3D1%26y%3D2",
    );
  });

  test("Back to list from the Playlists origin returns its query", () => {
    expect(backHref({ kind: "playlists" })).toBe("/playlists");
    expect(backHref({ kind: "playlists" }, "x=1")).toBe("/playlists?x=1");
  });

  test("tabOfHref reads the tab of a map address", () => {
    expect(tabOfHref("/maps/m?tab=crop&from=library")).toBe("crop");
    expect(tabOfHref("/maps/m?from=library")).toBeUndefined();
  });
});
