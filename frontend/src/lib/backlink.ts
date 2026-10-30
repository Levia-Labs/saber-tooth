// Where a map or playlist page was opened from, so "Back to list" returns there.
//
// Scheme: the page URL carries `from=<origin>` and, for origins whose filter and sort live in the
// URL (jobs, BeatSaver playlist), `back=<that page's query string without "?">`. The library's
// own query is kept in sessionStorage (see hooks.ts) and the playlists table's in lpstate.ts, so
// they need no `back`. A missing or malformed `from` means the library.
import { libraryHref } from "./hooks";

export type Origin =
  { kind: "library" | "jobs" | "playlists" } | { kind: "playlist" | "bs-playlist"; id: string };

export const FROM_PARAM = "from";
export const BACK_PARAM = "back";
export const LIBRARY: Origin = { kind: "library" };

const ID = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/;
const SIMPLE = new Set(["library", "jobs", "playlists"]);

/** Wire form of an origin: `library`, `jobs`, `playlists`, `playlist:<id>`, `bs-playlist:<id>`. */
export function formatOrigin(o: Origin): string {
  return "id" in o ? `${o.kind}:${o.id}` : o.kind;
}

/** Reads `from`; anything unknown (including a bad id) is the library. */
export function parseOrigin(raw: string | null | undefined): Origin {
  if (!raw) return LIBRARY;
  if (SIMPLE.has(raw)) return { kind: raw as "library" | "jobs" | "playlists" };
  const at = raw.indexOf(":");
  const kind = raw.slice(0, at);
  const id = raw.slice(at + 1);
  if (at > 0 && (kind === "playlist" || kind === "bs-playlist") && ID.test(id)) {
    return { kind, id };
  }
  return LIBRARY;
}

/** The section tab that stays active on the page opened from `o`. */
export function originTab(o: Origin): "library" | "jobs" | "playlists" | "beatsaver" {
  if (o.kind === "bs-playlist") return "beatsaver";
  if (o.kind === "playlist") return "playlists";
  return o.kind;
}

const withQuery = (path: string, back: string | undefined) => {
  const q = (back ?? "").replace(/^\?/, "");
  return q ? `${path}?${q}` : path;
};

/** The list page to return to, with its filters and sort. */
export function backHref(o: Origin, back?: string): string {
  switch (o.kind) {
    case "library":
      return back ? withQuery("/", back) : libraryHref();
    case "jobs":
      return withQuery("/jobs", back);
    case "playlists":
      return withQuery("/playlists", back);
    case "playlist":
      return `/playlists/${encodeURIComponent(o.id)}`;
    case "bs-playlist":
      return withQuery(`/beatsaver/playlists/${encodeURIComponent(o.id)}`, back);
  }
}

interface MapLinkOpts {
  tab?: string | undefined;
  from: Origin | string;
  back?: string | undefined;
}

/** Address of a map page opened from `from`; keeps `tab` and the origin's `back` query. */
export function mapHref(id: string, { tab, from, back }: MapLinkOpts): string {
  const origin = typeof from === "string" ? parseOrigin(from) : from;
  const params = new URLSearchParams();
  if (tab) params.set("tab", tab);
  params.set(FROM_PARAM, formatOrigin(origin));
  if (back) params.set(BACK_PARAM, back.replace(/^\?/, ""));
  return `/maps/${encodeURIComponent(id)}?${params.toString()}`;
}

/** Address of a playlist page opened from the Playlists list; `query` is that list's query. */
export function playlistHref(id: string, { query }: { query: string }): string {
  const params = new URLSearchParams({ [FROM_PARAM]: "playlists" });
  const back = query.replace(/^\?/, "");
  if (back) params.set(BACK_PARAM, back);
  return `/playlists/${encodeURIComponent(id)}?${params.toString()}`;
}

/** Address of a BeatSaver playlist page opened from the BeatSaver playlists list (`query` is the list's). */
export function bsPlaylistHref(id: string, query: string): string {
  const params = new URLSearchParams({ [FROM_PARAM]: "bs-playlists" });
  const back = query.replace(/^\?/, "");
  if (back) params.set(BACK_PARAM, back);
  return `/beatsaver/playlists/${encodeURIComponent(id)}?${params.toString()}`;
}

/** The BeatSaver playlists list, with the query it had when the playlist was opened. */
export function allPlaylistsHref(back: string | undefined): string {
  return withQuery("/beatsaver/playlists", back);
}

/** The `tab` of a map page address, when it names one. */
export function tabOfHref(href: string): string | undefined {
  const at = href.indexOf("?");
  return (at < 0 ? null : new URLSearchParams(href.slice(at + 1)).get("tab")) ?? undefined;
}

/** The `from` and `back` params of a page URL as a query suffix (`?from=...`), "" when absent. */
export function originSearch(params: URLSearchParams): string {
  const out = new URLSearchParams();
  const from = params.get(FROM_PARAM);
  const back = params.get(BACK_PARAM);
  if (from) out.set(FROM_PARAM, from);
  if (back) out.set(BACK_PARAM, back);
  const text = out.toString();
  return text ? `?${text}` : "";
}
