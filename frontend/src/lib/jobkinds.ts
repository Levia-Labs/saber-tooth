// Labels and icons of the job kinds, shared by the Jobs table and the job toasts.
import type { JobKind } from "../api/types";
import type { IconName } from "../components/icons";

export const KIND_LABEL: Record<JobKind, string> = {
  scan: "Scan",
  fix: "Fix",
  apply: "Apply",
  crop: "Crop",
  generate: "Generate",
  learn: "Learn lightshows",
  "bs-download": "Download maps",
};

export const KIND_ICON: Record<JobKind, IconName> = {
  scan: "scan",
  fix: "fix",
  apply: "apply",
  crop: "crop",
  generate: "generate",
  learn: "learn",
  "bs-download": "download",
};

export const KIND_ORDER: readonly JobKind[] = [
  "fix",
  "scan",
  "apply",
  "crop",
  "generate",
  "learn",
  "bs-download",
];
