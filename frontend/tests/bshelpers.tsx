import type { BsMap, BsPage, BsPreset } from "../src/api/beatsaver";
import { mockFetch } from "./helpers";

export function bsMap(n: number, patch: Partial<BsMap> = {}): BsMap {
  return {
    id: `k${n}`,
    name: `Song ${n}`,
    song: `Song ${n}`,
    mapper: `Mapper ${n}`,
    cover_url: null,
    preview_url: n % 2 ? `https://cdn.beatsaver.com/k${n}.mp3` : null,
    bpm: 128,
    duration: 201,
    rating: 0.96,
    upvotes: 120,
    downvotes: 4,
    tags: ["electronic", "rock", "pop", "anime"],
    ranked: false,
    difficulties: [
      { difficulty: "Easy", nps: 1.2, njs: 10 },
      { difficulty: "Expert", nps: 5.5, njs: 16 },
    ],
    installed: false,
    library_id: null,
    ...patch,
  };
}

export const SEEDED: BsPreset = {
  id: 1,
  name: "Gentle full-spread hits",
  seeded: true,
  filters: {
    diffs: "Easy,Normal,Hard",
    min_rating: "0.95",
    nps_min: "1",
    nps_max: "2",
    tags: "electronic,rock",
    order: "Rating",
  },
};

export function page(items: BsMap[], patch: Partial<BsPage> = {}): BsPage {
  return {
    items,
    cursor: null,
    scanned: items.length,
    matched: items.length,
    ...patch,
  };
}

export interface BsApiOptions {
  search?: (url: URL) => BsPage;
  presets?: BsPreset[];
  playlistsEnabled?: boolean;
  job?: (n: number) => unknown;
}

/** Fetch stub for the /api/beatsaver routes; records POST bodies by path. */
export function bsApi(options: BsApiOptions = {}) {
  const posts: { path: string; body: unknown }[] = [];
  let polls = 0;
  const stub = mockFetch((url, init) => {
    const path = url.pathname;
    if (init?.method === "POST" || init?.method === "DELETE") {
      posts.push({ path, body: init.body ? JSON.parse(String(init.body)) : null });
    }
    if (path === "/api/beatsaver/search") {
      return (options.search ?? (() => page([bsMap(1), bsMap(2)])))(url);
    }
    if (path === "/api/beatsaver/config") {
      return { playlists_enabled: options.playlistsEnabled ?? false };
    }
    if (path === "/api/beatsaver/presets") {
      if (init?.method === "POST") return { id: 9, name: "Mine", filters: {} };
      return options.presets ?? [SEEDED];
    }
    if (path === "/api/beatsaver/download") return { job: "j1" };
    if (path.startsWith("/api/jobs/")) {
      polls += 1;
      return (
        options.job?.(polls) ?? { id: "j1", kind: "download", status: "running", result: null }
      );
    }
    return {};
  });
  return { ...stub, posts };
}
