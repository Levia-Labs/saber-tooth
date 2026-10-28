const STEPS = [
  {
    edge: "start",
    dir: -1,
    label: "Previous section",
    help: "Move the start to the previous section.",
  },
  {
    edge: "start",
    dir: 1,
    label: "Next section",
    help: "Move the start to the next section.",
  },
  { edge: "end", dir: -1, label: "End 1 s earlier", help: "Move the end one second earlier." },
  { edge: "end", dir: 1, label: "End 1 s later", help: "Move the end one second later." },
] as const;

/** Large buttons that move the crop window without dragging; the help sits under each as text. */
export function CropSteps({ onStep }: { onStep: (edge: "start" | "end", dir: 1 | -1) => void }) {
  return (
    <div className="vr-steps" role="group" aria-label="Move the crop">
      {STEPS.map((s) => (
        <div key={s.label} className="vr-step">
          <button type="button" className="btn plain" onClick={() => onStep(s.edge, s.dir)}>
            {s.label}
          </button>
          <small className="vr-help">{s.help}</small>
        </div>
      ))}
    </div>
  );
}
