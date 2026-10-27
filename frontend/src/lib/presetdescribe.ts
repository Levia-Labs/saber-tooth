// Plain-words description of a BeatSaver preset, generated from its filters. Pure.
import { stateFromPreset, type BsOrder } from "./bsfilters";
import type { LevelKey } from "../api/types";

const ORDER_PHRASES: Record<BsOrder, [string, string]> = {
  Latest: ["newest first", "oldest first"],
  Relevance: ["most relevant first", "least relevant first"],
  Rating: ["best rated first", "worst rated first"],
  Curated: ["most recently curated first", "least recently curated first"],
  Random: ["in random order", "in random order"],
  Duration: ["longest first", "shortest first"],
};

const DIFF_LABELS: Record<LevelKey, string> = {
  Easy: "Easy",
  Normal: "Normal",
  Hard: "Hard",
  Expert: "Expert",
  ExpertPlus: "Expert+",
};

function listWords(items: string[], joiner: "and" | "or"): string {
  if (items.length < 2) return items.join("");
  return `${items.slice(0, -1).join(", ")} ${joiner} ${items[items.length - 1]}`;
}

function range(min: number | null, max: number | null, unit: string): string | null {
  if (min !== null && max !== null) return `${min}-${max} ${unit}`;
  if (min !== null) return `${min} or more ${unit}`;
  if (max !== null) return `up to ${max} ${unit}`;
  return null;
}

/** Plain-words description of what a preset's filters show, generated from the filters. */
export function describePreset(filters: Record<string, string>): string {
  const s = stateFromPreset(filters);
  const parts: string[] = [];
  const q = s.q.trim();
  if (q) parts.push(`matching "${q}"`);
  if (s.diffs.length) {
    const names = s.diffs.map((d) => DIFF_LABELS[d]);
    parts.push(
      s.diffsMode === "all" ? `with ${listWords(names, "and")}` : `with ${listWords(names, "or")}`,
    );
  }
  if (s.minRating !== null) parts.push(`rated ${Math.round(s.minRating * 100)}% or higher`);
  if (s.minUpvotes !== null) parts.push(`with at least ${s.minUpvotes} upvotes`);
  const nps = range(s.npsMin, s.npsMax, "notes per second");
  if (nps)
    parts.push(
      `${s.npsScope === "all" ? "every difficulty" : "at least one difficulty"} at ${nps}`,
    );
  const bpm = range(s.bpmMin, s.bpmMax, "BPM");
  if (bpm) parts.push(`at ${bpm}`);
  const length = range(s.durationMin, s.durationMax, "seconds long");
  if (length) parts.push(length);
  if (s.from && s.to) parts.push(`uploaded from ${s.from} to ${s.to}`);
  else if (s.from) parts.push(`uploaded since ${s.from}`);
  else if (s.to) parts.push(`uploaded until ${s.to}`);
  if (s.ranked) parts.push("ranked");
  if (s.tags.length) parts.push(`tagged ${listWords(s.tags, "or")}`);
  const sort = s.localSort
    ? `${s.localSort === "upvotes" ? "most upvoted" : "highest BPM"} first among loaded maps`
    : ORDER_PHRASES[s.order][s.ascending ? 1 : 0];
  parts.push(sort);
  return `Shows maps ${parts.join(", ")}.`;
}
