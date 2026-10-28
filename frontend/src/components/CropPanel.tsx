import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { cropMap } from "../api/client";
import { useJobRunner } from "../api/jobs";
import { keys, useTimeline } from "../api/queries";
import type { CropLength, CropResult, CropStart, Job, Timeline } from "../api/types";
import { errorToAlert, toAlert } from "../lib/alerts";
import {
  CROP_TIPS,
  KIND_LABEL,
  clock,
  endFor,
  keepStart,
  same,
  snapEnd,
  snapStart,
  stepEnd,
  stepStart,
  suggestion,
  type Choice,
} from "../lib/crop";
import { Alert, SpecAlert } from "./Alert";
import { ActionButton } from "./Buttons";
import { Icon } from "./icons";
import { NpsChart, type Edge } from "./NpsChart";

const LENGTHS: { key: CropLength; label: string }[] = [
  { key: "60", label: "1 min" },
  { key: "120", label: "2 min" },
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

function LengthSwitch(props: {
  value: CropLength;
  data: Timeline;
  onChange: (next: CropLength) => void;
}) {
  return (
    <div className="crop-switch" role="radiogroup" aria-label="Crop length">
      {LENGTHS.map(({ key, label }) => (
        <button
          key={key}
          type="button"
          role="radio"
          aria-checked={props.value === key}
          disabled={!props.data.lengths[key].enabled}
          className={props.value === key ? "btn accent" : "btn plain"}
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
  if (!result?.cropped_id) return null;
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

function CropEditor({ mapId, data, busy }: { mapId: string; data: Timeline; busy: boolean }) {
  const client = useQueryClient();
  const crop = useJobRunner("Crop");
  const [length, setLength] = useState<CropLength>(data.lengths["60"].enabled ? "60" : "120");
  const [picked, setPicked] = useState<Choice | null>(null);
  const plan = data.lengths[length];
  const best = suggestion(plan);
  const selection = picked ?? best;
  const start = selection ? plan.starts.find((s) => same(s.beat, selection.start)) : undefined;
  const end = start && selection ? start.ends.find((e) => same(e.beat, selection.end)) : undefined;
  const seconds = start && end ? end.seconds - start.seconds : null;
  const amber = end !== undefined && end.kind !== "section";
  const edited =
    picked !== null && !(best && same(picked.start, best.start) && same(picked.end, best.end));

  const moveStart = (next: CropStart) =>
    setPicked({ start: next.beat, end: endFor(next, selection?.end ?? null, plan.band).beat });
  const onMove = (edge: Edge, at: number) => {
    if (edge === "start") moveStart(snapStart(plan, at));
    else if (start) setPicked({ start: start.beat, end: snapEnd(start, at).beat });
  };
  const onStep = (edge: Edge, dir: 1 | -1, jump: boolean) => {
    if (!start || !end) return;
    if (edge === "start") moveStart(stepStart(plan, start.beat, dir));
    else setPicked({ start: start.beat, end: stepEnd(start, end.beat, dir, jump).beat });
  };
  const choose = (next: CropLength) => {
    if (next === length) return;
    setPicked(keepStart(data.lengths[next], selection));
    setLength(next);
  };
  const create = () => {
    if (!start || !end) return;
    void crop
      .run(() => cropMap(mapId, start.beat, end.beat))
      .then(() => client.invalidateQueries({ queryKey: keys.maps }));
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
      {LENGTHS.filter(({ key }) => !data.lengths[key].enabled).map(({ key, label }) => (
        <Alert
          key={key}
          variant="info"
          title={`${label} crop unavailable`}
          message={data.lengths[key].reason ?? ""}
        />
      ))}
      <LengthSwitch value={length} data={data} onChange={choose} />
      <NpsChart
        nps={data.nps}
        hardest={data.hardest}
        sections={data.sections}
        duration={data.duration_s}
        selection={start && end ? { start_s: start.seconds, end_s: end.seconds } : null}
        faint={plan.suggestions.slice(1).map((w) => ({ start_s: w.start_s, end_s: w.end_s }))}
        endMarks={start ? start.ends.map((e) => ({ seconds: e.seconds, kind: e.kind })) : []}
        onMove={onMove}
        onStep={onStep}
      />
      {end && seconds !== null && (
        <p className={amber ? "crop-readout crop-amber" : "crop-readout"} aria-live="polite">
          {`Length ${clock(seconds)}. ${
            amber
              ? `Ends on a ${KIND_LABEL[end.kind]}, not a section boundary.`
              : "Both cuts are on section boundaries."
          }`}
        </p>
      )}
      <div className="crop-actions">
        <ActionButton
          icon="apply"
          label="Create cropped map"
          tip={CROP_TIPS.create}
          text
          variant="accent"
          disabled={!start || !end || busy || crop.busy}
          onClick={create}
        />
        {edited && (
          <ActionButton
            icon="reset"
            label="Reset to suggestion"
            tip={CROP_TIPS.reset}
            text
            onClick={() => setPicked(null)}
          />
        )}
      </div>
      <CropOutcome job={crop.job} error={crop.error} />
    </div>
  );
}

function CropBody({ mapId, busy }: { mapId: string; busy: boolean }) {
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
  return <CropEditor mapId={mapId} data={timeline.data} busy={busy} />;
}

/** Crop to a 1 or 2 minute highlight: a disclosure that loads the timeline when opened. */
export function CropPanel({ mapId, busy }: { mapId: string; busy: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <section className="crop-panel" aria-label="Crop to a highlight">
      <button
        type="button"
        className="btn plain crop-toggle"
        aria-expanded={open}
        aria-controls="crop-body"
        onClick={() => setOpen((o) => !o)}
      >
        <Icon name={open ? "collapse" : "expand"} />
        <span>Crop to 1 or 2 minutes</span>
      </button>
      {open && (
        <div id="crop-body">
          <CropBody key={mapId} mapId={mapId} busy={busy} />
        </div>
      )}
    </section>
  );
}
