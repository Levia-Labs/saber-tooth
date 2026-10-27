import type { BsPlaylist } from "../src/api/beatsaver";

export function bsPlaylist(id: string, patch: Partial<BsPlaylist> = {}): BsPlaylist {
  return {
    id,
    name: `Playlist ${id}`,
    owner: `Owner ${id}`,
    cover_url: null,
    map_count: 10,
    mapper_count: 4,
    duration: 2400,
    upvotes: 120,
    downvotes: 6,
    rating: 0.95,
    min_nps: 1.2,
    max_nps: 6.4,
    created_at: "2024-03-01T10:00:00Z",
    curated: false,
    ...patch,
  };
}
