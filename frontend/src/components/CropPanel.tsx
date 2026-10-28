import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { cropMap } from "../api/client";
import { useJobRunner } from "../api/jobs";
import { keys, useTimeline } from "../api/queries";
import type { CropLength, CropResult, Job, Timeline } from "../api/types";
import { errorToAlert, toAlert } from "../lib/alerts";
import {
  CROP_TIPS,
  MIN_LENGTH_S,
  keepStart,
  moveEdge,
  nudgeEdge,
  sameSpan,
  shiftWindow,
  suggestion,
  type Span,
} from "../lib/crop";
import { Alert, SpecAlert } from "./Alert";
import { useAnnounce } from "./Announcer";
import { ActionButton } from "./Buttons";
import { CropSave } from "./CropSave";
import { NpsChart, type Edge } from "./NpsChart";

type Choice = CropLength | "unlimited";

const LENGTHS: { key: Choice; label: string }[] = [
  { key: "60", label: "1 min" },
  { key: "120", label: "2 min" },
  { key: "unlimited", label: "Unlimited" },
];

function CropSkeleton() {
  return (
    <div className="crop-skeleton" aria-busy="true" data-skeleton="true">
      <span className="sk sk-bar short" />
      <span className="sk crop-skeleton-chart" />
      <span className="sr-only">Loading</span>
    </div>
  );
}

function LengthSwitch(props: { value: Choice; data: Timeline; onChange: (next: Choice) => void }) {
  return (
    <div className="mode-switch crop-switch" role="radiogroup" aria-label="Crop length">
      {LENGTHS.map(({ key, label }) => (
        <button
          key={key}
          type="button"
          role="radio"
          className="pill"
          aria-checked={props.value === key}
          disabled={key !== "unlimited" && !props.data.lengths[key].enabled}
          onClick={() => props.onChange(key)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function CropOutcome({ job, error }: { job: Job | null; error: string | null }) {
  if (error !== null) return <SpecAlert spec={toAlert(job, error)} />;
  const result = job?.result as Partial<CropResult> | null | undefined;
  if (!result?.cropped_id || result.replaced) return null;
  return (
    <Alert
      variant="success"
      title="Cropped map written"
      message={`Written to ${result.folder ?? "a new folder"}.`}
      actions={
        <Link className="btn plain" to={`/maps/${encodeURIComponent(result.cropped_id)}`}>
          Open cropped map
        </Link>
      }
    />
  );
}

interface EditorProps {
  mapId: string;
  data: Timeline;
  folder: string;
  busy: boolean;
  audioUrl?: string | null;
}

function CropEditor({ mapId, folder, data, busy, audioUrl }: EditorProps) {
  const client = useQueryClient();
  const announce = useAnnounce();
  const crop = useJobRunner("Crop");
  const [length, setLength] = useState<Choice>(
    data.lengths["60"].enabled ? "60" : data.lengths["120"].enabled ? "120" : "unlimited",
  );
  const [picked, setPicked] = useState<Span | null>(null);
  const min = data.min_length_s ?? MIN_LENGTH_S;
  const whole: Span = { start_s: 0, end_s: data.duration_s };
  const plan = length === "unlimited" ? null : data.lengths[length];
  const best = plan ? suggestion(plan) : whole;
  const selection = picked ?? best;
  const edited = picked !== null && !(best && sameSpan(picked, best));

  const onMove = (edge: Edge, at: number) =>
    selection && setPicked(moveEdge(selection, edge, at, min, data.duration_s));
  const onStep = (edge: Edge, dir: 1 | -1, big: boolean) =>
    selection && setPicked(nudgeEdge(selection, edge, dir, big, min, data.duration_s));
  /** Move the whole window to a start, keeping its length. */
  const onShift = (at: number) =>
    selection && setPicked(shiftWindow(selection, at, data.duration_s));
  const choose = (next: Choice) => {
    if (next === length) return;
    if (next === "unlimited") setPicked(selection ?? whole);
    else setPicked(keepStart(data.lengths[next], selection));
    setLength(next);
  };
  const save = (replace: boolean) => {
    if (!selection) return;
    void crop
      .run(() => cropMap(mapId, selection.start_s, selection.end_s, replace))
      .then((job) => {
        if (job && replace) {
          announce({ variant: "success", title: "Map replaced", message: folder });
          void client.invalidateQueries({ queryKey: keys.timeline(mapId) });
          void client.invalidateQueries({ queryKey: keys.proposals(mapId) });
          void client.invalidateQueries({ queryKey: keys.map(mapId) });
        }
        return client.invalidateQueries({ queryKey: keys.maps });
      });
  };

  return (
    <div className="crop-editor">
      {data.map_only && (
        <Alert
          variant="info"
          title="Sections from map only"
          message="This song has no audio analysis, so section edges come from the notes and lights alone."
        />
      )}
      {LENGTHS.filter(({ key }) => key !== "unlimited" && !data.lengths[key].enabled).map(
        ({ key, label }) => (
          <Alert
            key={key}
            variant="info"
            title={`${label} crop unavailable`}
            message={data.lengths[key as CropLength].reason ?? ""}
          />
        ),
      )}
      <div className="crop-bar">
        <LengthSwitch value={length} data={data} onChange={choose} />
        <div className="crop-actions">
          {edited && (
            <ActionButton
              icon="reset"
              label="Reset to suggestion"
              tip={CROP_TIPS.reset}
              text
              onClick={() => setPicked(null)}
            />
          )}
          <CropSave
            folder={folder}
            disabled={!selection || busy || crop.busy}
            busy={busy || crop.busy}
            onSave={save}
          />
        </div>
      </div>
      <NpsChart
        nps={data.nps}
        hardest={data.hardest}
        sections={data.sections}
        duration={data.duration_s}
        selection={selection}
        faint={
          plan ? plan.suggestions.slice(1).map((w) => ({ start_s: w.start_s, end_s: w.end_s })) : []
        }
        onMove={onMove}
        onStep={onStep}
        onShift={onShift}
        onJump={onShift}
        audioUrl={audioUrl}
      />
      <CropOutcome job={crop.job} error={crop.error} />
    </div>
  );
}

function CropBody({
  mapId,
  folder,
  busy,
  audioUrl,
}: {
  mapId: string;
  folder: string;
  busy: boolean;
  audioUrl?: string | null;
}) {
  const timeline = useTimeline(mapId);
  if (timeline.isPending) return <CropSkeleton />;
  if (timeline.isError) {
    return (
      <SpecAlert
        spec={errorToAlert(timeline.error, "Could not build the crop timeline")}
        onRetry={() => void timeline.refetch()}
      />
    );
  }
  return (
    <CropEditor
      mapId={mapId}
      folder={folder}
      data={timeline.data}
      busy={busy}
      audioUrl={audioUrl}
    />
  );
}

/** Crop to a 1 or 2 minute highlight; mount it when the Crop tab first shows, it loads the timeline. */
export function CropPanel({
  mapId,
  folder,
  busy,
  audioUrl,
}: {
  mapId: string;
  folder: string;
  busy: boolean;
  audioUrl?: string | null;
}) {
  return (
    <section className="crop-panel" aria-label="Crop to a highlight">
      <div id="crop-body">
        <CropBody key={mapId} mapId={mapId} folder={folder} busy={busy} audioUrl={audioUrl} />
      </div>
    </section>
  );
}
