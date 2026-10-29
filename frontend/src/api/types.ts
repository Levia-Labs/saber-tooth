// Response shapes of the saber-tooth HTTP API (see docs/api.md). Field names live here only.
export const STATUS_KEYS = [
  "error",
  "warn",
  "ok",
  "incomplete",
  "unscanned",
  "unreadable",
  "scanning",
  "applying",
  "fixing",
  "queued",
] as const;
export type StatusKey = (typeof STATUS_KEYS)[number];

export const LEVEL_KEYS = ["Easy", "Normal", "Hard", "Expert", "ExpertPlus"] as const;
export type LevelKey = (typeof LEVEL_KEYS)[number];

export type JobState = "queued" | "running" | "done" | "failed" | "cancelled";
export type JobKind = "scan" | "apply" | "fix" | "generate" | "learn" | "crop" | "bs-download";

export type CropLength = "60" | "120";
export type EndKind = "section" | "phrase" | "bar4" | "bar";

export interface CropEnd {
  beat: number;
  seconds: number;
  kind: EndKind;
}

export interface CropStart {
  beat: number;
  seconds: number;
  ends: CropEnd[];
}

export interface CropWindow {
  start_beat: number;
  end_beat: number;
  start_s: number;
  end_s: number;
  length_s: number;
  end_kind: EndKind;
  score: number;
}

export interface CropPlan {
  enabled: boolean;
  /** Why this length is off, when it is. */
  reason: string | null;
  /** Allowed length in seconds: 54 to 66 or 108 to 132. */
  band: [number, number];
  /** The best window first, then the next two. */
  suggestions: CropWindow[];
  starts: CropStart[];
}

export interface CropSection {
  start_beat: number;
  end_beat: number;
  start_s: number;
  end_s: number;
  nps: number;
  intensity: number;
}

export interface Timeline {
  map_id: string;
  duration_s: number;
  /** Shortest crop in seconds; 1 when absent. */
  min_length_s?: number;
  bpm: number;
  hardest: string;
  /** True when the map has no audio analysis: sections come from the notes and lights only. */
  map_only: boolean;
  grid_drift_s: number | null;
  /** Notes per second in 1 s steps, per difficulty that has notes. */
  nps: Record<string, number[]>;
  sections: CropSection[];
  lengths: Record<CropLength, CropPlan>;
}

/** Result of a finished crop job. */
export interface CropResult {
  map_id: string;
  folder: string;
  cropped_id: string;
  label: string;
  start_beat: number;
  end_beat: number;
  length_s: number;
  /** Set when the crop replaced the original folder. */
  replaced?: boolean;
}

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
  /** Address of the map's song for the preview button; absent until the API provides it. */
  audio_url?: string | null;
  /** Second where the preview starts. */
  preview_start?: number | null;
  job: ActiveJob | null;
  /** Id and folder of the "[saber-tooth]" copy written by Fix, when one exists. */
  fixed_copy_id?: string | null;
  fixed_copy_folder?: string | null;
  /** Set on a fixed copy: the map it was made from. */
  original_id?: string | null;
  original_folder?: string | null;
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
  /** Smallest and largest known length (seconds) and tempo; absent on older servers. */
  duration?: { min: number | null; max: number | null };
  bpm?: { min: number | null; max: number | null };
  total: number;
}

export interface JobView {
  id: string;
  kind: JobKind;
  status: JobState;
  map_id: string | null;
  title: string;
  map_exists: boolean;
  created_at: string;
  started_at: string | null;
  updated_at: string;
  progress: string | null;
  progress_at: string | null;
  error: string | null;
  position: number | null;
}

export type Job = Pick<JobView, "id" | "kind" | "status" | "error"> &
  Partial<Omit<JobView, "id" | "kind" | "status" | "error">> & {
    result: Record<string, unknown> | null;
  };

export interface JobLists {
  running: JobView[];
  queued: JobView[];
  recent: JobView[];
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
  status: "pending" | "approved" | "rejected" | "applied" | "superseded";
  /** Id of the proposal this one replaced during an apply. */
  replaces?: number | null;
  /** Ids of open proposals that touch the same notes. */
  conflicts_with?: number[];
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
