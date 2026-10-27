// Response shapes of the saber-tooth HTTP API (see docs/api.md). Field names live here only.
export const STATUS_KEYS = [
  "error",
  "warn",
  "ok",
  "unscanned",
  "unreadable",
  "scanning",
  "applying",
  "queued",
] as const;
export type StatusKey = (typeof STATUS_KEYS)[number];

export const LEVEL_KEYS = ["Easy", "Normal", "Hard", "Expert", "ExpertPlus"] as const;
export type LevelKey = (typeof LEVEL_KEYS)[number];

export type JobState = "queued" | "running" | "done" | "failed";
export type JobKind = "scan" | "apply" | "generate" | "learn";

export interface ActiveJob {
  id: string;
  kind: JobKind;
  status: JobState;
}

export interface MapItem {
  id: string;
  folder: string;
  title: string;
  mapper: string;
  environment: string;
  parse_error: string | null;
  errors: number;
  warnings: number;
  scanned_at: string | null;
  status: StatusKey;
  cover_url: string | null;
  difficulties: string[];
  approved: number;
  pending: number;
  bpm: number | null;
  duration_s: number | null;
  job: ActiveJob | null;
}

export interface MapPage {
  items: MapItem[];
  total: number;
  offset: number;
  limit: number;
}

export interface Facets {
  status: Partial<Record<StatusKey, number>>;
  environments: { name: string; count: number }[];
  mappers: { name: string; count: number }[];
  levels: Record<LevelKey, number>;
  total: number;
}

export interface Job {
  id: string;
  kind: JobKind;
  status: JobState;
  error: string | null;
  result: Record<string, unknown> | null;
}

export interface Note {
  beat: number;
  x: number;
  y: number;
  color: number;
  cut: number;
}

export interface Wall {
  beat: number;
  duration: number;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Proposal {
  id: number | string;
  rule: string;
  difficulty: string;
  severity: string;
  summary: string;
  status: "pending" | "approved" | "rejected" | "applied";
  before: Note[];
  after: Note[];
  walls_before: Wall[];
  walls_after: Wall[];
  walls_context: Wall[];
}

export type SortKey =
  | "title"
  | "mapper"
  | "environment"
  | "status"
  | "errors"
  | "warnings"
  | "scanned_at"
  | "duration"
  | "bpm"
  | "levels";
export type SortOrder = "asc" | "desc";
