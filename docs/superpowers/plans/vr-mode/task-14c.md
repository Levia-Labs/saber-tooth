# Task 14: VR Map screen (part c)

Continues [task-14b.md](task-14b.md).

- [ ] **Step 6: Implement the screen**

Create `frontend/src/vr/VrMapPage.tsx`:

```tsx
import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router";
import { ApiError, deleteMap, errorMessage } from "../api/client";
import { useFix } from "../api/fix";
import { keys, useLiveRows, useMap } from "../api/queries";
import type { MapItem } from "../api/types";
import { SpecAlert } from "../components/Alert";
import { useAnnounce } from "../components/Announcer";
import { Cover, LevelChips, StatusChip, Tempo } from "../components/Chips";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { CropPanel } from "../components/CropPanel";
import { FixedCopyLink, FixedCopyOf } from "../components/FixedCopyLink";
import { FixOutcomes } from "../components/FixOutcomes";
import { Icon } from "../components/icons";
import { MapHeadSkeleton } from "../components/Skeletons";
import { errorToAlert } from "../lib/alerts";
import { formatEnvironment } from "../lib/environment";
import { useDocumentTitle } from "../lib/hooks";
import { isCleanCopy, mapName } from "../lib/status";
import { TIPS } from "../lib/tips";
import { NotFoundPage } from "../pages/NotFoundPage";

function VrMapView({ item }: { item: MapItem }) {
  const client = useQueryClient();
  const navigate = useNavigate();
  const announce = useAnnounce();
  const name = mapName(item);
  const fix = useFix(item, name);
  const clean = isCleanCopy(item);
  const running = item.job !== null;

  const remove = async () => {
    try {
      const out = await deleteMap(item.id);
      client.removeQueries({ queryKey: keys.map(item.id) });
      await navigate("/vr");
      await client.invalidateQueries({ queryKey: ["maps"] });
      announce({ variant: "success", title: "Deleted", message: out.deleted });
    } catch (err) {
      announce({
        variant: "danger",
        title: "Could not delete the map",
        message: errorMessage(err),
      });
    }
  };

  return (
    <>
      <div className="vr-head">
        <Cover url={item.cover_url} big />
        <div className="vr-head-text">
          <h1 className="vr-heading" tabIndex={-1} data-page-heading>
            {name}
          </h1>
          <p className="vr-help">
            {item.mapper || "Unknown mapper"}
            {item.environment ? ` - ${formatEnvironment(item.environment)}` : ""}
          </p>
          <div className="vr-card-meta">
            <StatusChip item={item} />
            <LevelChips names={item.difficulties} />
            <Tempo item={item} />
          </div>
        </div>
      </div>
      <FixedCopyLink item={item} />
      <FixedCopyOf item={item} />
      <FixOutcomes mapId={item.id} />
      <div className="vr-actions">
        {!clean && (
          <div className="vr-act">
            <button
              type="button"
              className="btn accent vr-big"
              disabled={running || item.status === "unreadable"}
              onClick={() => void fix()}
            >
              Fix
            </button>
            <small className="vr-help">{TIPS.fix}</small>
          </div>
        )}
        <div className="vr-act">
          <ConfirmDialog
            title="Delete permanently?"
            description={`"${item.folder}" is removed from disk and cannot be undone.`}
            confirmLabel="Delete"
            danger
            onConfirm={() => void remove()}
          >
            <button type="button" className="btn danger vr-big" disabled={running}>
              Delete
            </button>
          </ConfirmDialog>
          <small className="vr-help">{TIPS.delete}</small>
        </div>
      </div>
      <CropPanel mapId={item.id} busy={running} steps />
    </>
  );
}

export function VrMapPage() {
  const { id = "" } = useParams();
  const map = useMap(id);
  useLiveRows(map.data ? [map.data] : []);
  useDocumentTitle(map.isError ? "Map not found" : map.data ? mapName(map.data) : "Map");

  if (map.isError && map.error instanceof ApiError && map.error.status === 404) {
    return <NotFoundPage title="Map not found" detail={`No map with id ${id}.`} />;
  }
  return (
    <section className="vr-screen">
      <Link className="btn plain vr-back" to="/vr">
        <Icon name="back" />
        Library
      </Link>
      {map.isPending ? (
        <MapHeadSkeleton />
      ) : map.isError ? (
        <SpecAlert
          spec={errorToAlert(map.error, "Could not load the map")}
          onRetry={() => void map.refetch()}
        />
      ) : (
        <VrMapView item={map.data} />
      )}
    </section>
  );
}
```

Append to `frontend/src/styles/vr.css`:

```css
/* Map screen. */
[data-ui="vr"] .vr-head {
  display: flex;
  gap: var(--vr-gap);
  align-items: flex-start;
}
[data-ui="vr"] .vr-head-text {
  display: flex;
  flex-direction: column;
  gap: var(--vr-gap);
  min-width: 0;
}
[data-ui="vr"] .vr-back {
  align-self: flex-start;
}
[data-ui="vr"] .vr-act,
[data-ui="vr"] .vr-step {
  display: flex;
  flex-direction: column;
  gap: var(--vr-gap);
  max-width: 22rem;
}
[data-ui="vr"] .vr-steps {
  display: flex;
  flex-wrap: wrap;
  gap: var(--vr-gap);
  margin-block: var(--vr-gap);
}
```

Append to `frontend/src/vr/README.md`:

```markdown
5. `CropSteps.tsx`, `VrMapPage.tsx`: the `/vr/maps/:id` screen; `CropPanel` takes `steps` to show the four large step buttons.
```

- [ ] **Step 7: Run the tests to see them pass**

Run: `npx --prefix frontend vitest run --root frontend tests/vrcrop.test.tsx tests/vrmap.test.tsx tests/croppanel.test.tsx tests/vrcss.test.ts`
Expected: PASS. `vrcrop.test.tsx` adds 6 tests, `vrmap.test.tsx` adds 9; `croppanel.test.tsx` (crop-highlight Task 15) stays green because `steps` defaults to `false`.

- [ ] **Step 8: Type check and lint**

Run: `npm --prefix frontend run typecheck` then `npm --prefix frontend run lint`
Expected: both exit 0.

- [ ] **Step 9: Commit**

Commit: main thread runs `task st:commit -- -m "feat(vr): VR map screen with Fix, Delete and crop step buttons" frontend/src/vr frontend/src/components/CropPanel.tsx frontend/src/styles/vr.css frontend/tests/vrcrop.test.tsx frontend/tests/vrmap.test.tsx`
