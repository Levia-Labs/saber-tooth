// Types and helpers for Auto crop: the three ranked windows the server proposes.
import type { Span } from "./crop";

/** One proposal from GET /api/maps/{id}/crop/suggestions. */
export interface CropProposal {
  rank: number;
  start_beat: number;
  end_beat: number;
  start_s: number;
  end_s: number;
  length_s: number;
  /** "1 min" or "2 min": the length it was cut for. */
  target: string;
  /** 0 to 1. */
  score: number;
  reason: string;
}

export interface CropSuggestions {
  map_id: string;
  duration_s: number;
  /** Why there is no proposal, when the list is empty. */
  reason: string | null;
  suggestions: CropProposal[];
}

export const spanOf = (p: CropProposal): Span => ({ start_s: p.start_s, end_s: p.end_s });

/** Score as a whole percentage for the bar and its label. */
export const percent = (score: number): number => Math.round(Math.max(0, Math.min(1, score)) * 100);
