# Task 14: VR Map screen (part b)

Continues [task-14a.md](task-14a.md).

- [ ] **Step 4: Implement the step buttons**

Create `frontend/src/vr/CropSteps.tsx`:

```tsx
import type { Edge } from "../components/NpsChart";

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
    help: "Move the start to the next section; the end follows.",
  },
  {
    edge: "end",
    dir: -1,
    label: "End earlier",
    help: "Move the end to the previous allowed point.",
  },
  { edge: "end", dir: 1, label: "End later", help: "Move the end to the next allowed point." },
] as const;

/** Large buttons that move the crop window without dragging: one allowed point per press. */
export function CropSteps({
  onStep,
}: {
  onStep: (edge: Edge, dir: 1 | -1, jump: boolean) => void;
}) {
  return (
    <div className="vr-steps" role="group" aria-label="Move the crop">
      {STEPS.map((s) => (
        <div key={s.label} className="vr-step">
          <button type="button" className="btn plain" onClick={() => onStep(s.edge, s.dir, false)}>
            {s.label}
          </button>
          <small className="vr-help">{s.help}</small>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Add the `steps` prop to the crop panel**

Four anchored edits in `frontend/src/components/CropPanel.tsx`; change nothing else. Add this import with the other component imports:

```tsx
import { CropSteps } from "../vr/CropSteps";
```

Edit 1: the editor signature.

```tsx
function CropEditor({
  mapId,
  data,
  busy,
  steps,
}: {
  mapId: string;
  data: Timeline;
  busy: boolean;
  steps: boolean;
}) {
```

replaces

```tsx
function CropEditor({ mapId, data, busy }: { mapId: string; data: Timeline; busy: boolean }) {
```

Edit 2: after the chart. Replace

```tsx
        onStep={onStep}
      />
      {end && seconds !== null && (
```

with

```tsx
        onStep={onStep}
      />
      {steps && <CropSteps onStep={onStep} />}
      {end && seconds !== null && (
```

Edit 3: the body. Replace

```tsx
function CropBody({ mapId, busy }: { mapId: string; busy: boolean }) {
```

with

```tsx
function CropBody({ mapId, busy, steps }: { mapId: string; busy: boolean; steps: boolean }) {
```

and replace

```tsx
return <CropEditor mapId={mapId} data={timeline.data} busy={busy} />;
```

with

```tsx
return <CropEditor mapId={mapId} data={timeline.data} busy={busy} steps={steps} />;
```

Edit 4: the panel. Replace

```tsx
export function CropPanel({ mapId, busy }: { mapId: string; busy: boolean }) {
```

with

```tsx
export function CropPanel({
  mapId,
  busy,
  steps = false,
}: {
  mapId: string;
  busy: boolean;
  /** Show the large step buttons of the VR layout under the chart. */
  steps?: boolean;
}) {
```

and replace

```tsx
<CropBody key={mapId} mapId={mapId} busy={busy} />
```

with

```tsx
<CropBody key={mapId} mapId={mapId} busy={busy} steps={steps} />
```

Continued in [task-14c.md](task-14c.md).
