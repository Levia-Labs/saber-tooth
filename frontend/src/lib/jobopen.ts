// Where a job toast leads: the Jobs page, or its read-only VR twin in the VR shell.
import { useCallback } from "react";
import { useNavigate } from "react-router";
import { vrPath } from "../vr/mode";
import { useVrMode } from "../vr/VrMode";

/** Returns a stable function that opens the Jobs page for the current UI mode. */
export function useOpenJobs(): () => void {
  const navigate = useNavigate();
  const { mode } = useVrMode();
  return useCallback(
    () => void navigate(mode === "vr" ? vrPath("/jobs") : "/jobs"),
    [navigate, mode],
  );
}
