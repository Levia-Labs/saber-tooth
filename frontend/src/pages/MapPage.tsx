import { useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";
import {
  ApiError,
  type Started,
  applyMap,
  approveAll,
  relightMap,
  scanMap,
  deleteMap,
} from "../api/client";
import { Alert, SpecAlert } from "../components/Alert";
import { useAnnounce } from "../components/Announcer";
import { FixesSkeleton, MapHeadSkeleton } from "../components/Skeletons";
import { errorToAlert } from "../lib/alerts";
import { specToInput } from "../lib/announcements";
import { FixedCopyLink, FixedCopyOf } from "../components/FixedCopyLink";
import { CropPanel } from "../components/CropPanel";
import { EnvironmentPicker } from "../components/EnvironmentPicker";
import { DeletePanel } from "../components/DeletePanel";
import { FixToolbar } from "../components/FixToolbar";
import { MapFooter } from "../components/MapFooter";
import { MapTabList, MapTabPanel } from "../components/MapTabs";
import { parseTab, tabsFor, type MapTab } from "../lib/mapTabs";
import { stopPreview } from "../lib/previewPlayer";
import { errorText } from "../lib/jobtoasts";
import { useJobRunner } from "../api/jobs";
import { approvePending, decideOptimistically, useFindings } from "../api/review";
import { keys, useLiveRows, useMap, useProposals } from "../api/queries";
import { Cover, LevelChips, StatusChip, Tempo } from "../components/Chips";
import { PreviewButton } from "../components/PreviewButton";
import { JobOutcome } from "../components/JobOutcome";
import { ProposalGroups } from "../components/ProposalGroups";
import { BackLink } from "../components/BackLink";
import { PageShell } from "../components/PageShell";
import { backHref, originTab, tabOfHref } from "../lib/backlink";
import { useDocumentTitle } from "../lib/hooks";
import { useOrigin } from "../lib/useBacklink";
import { TIPS } from "../lib/tips";
import { isCleanCopy, mapName, statusHref } from "../lib/status";
import { NotFoundPage } from "./NotFoundPage";

/** The tab a status chip opens: its findings or crop, otherwise Status. */
const chipTab = (href: string): MapTab => (tabOfHref(href) === "crop" ? "crop" : "status");

export function MapPage() {
  const { id = "" } = useParams();
  const client = useQueryClient();
  const navigate = useNavigate();
  const announce = useAnnounce();
  const map = useMap(id);
  const proposals = useProposals(id);
  const found = useFindings(id);
  const [params, setParams] = useSearchParams();
  const { origin, back } = useOrigin();
  const [cropSeen, setCropSeen] = useState(false);
  const deleting = useRef(false);
  const [deletePending, setDeletePending] = useState(false);
  const [openIds, setOpenIds] = useState<ReadonlySet<string>>(new Set());
  const toggleOne = (pid: string, on: boolean) =>
    setOpenIds((prev) => {
      const next = new Set(prev);
      if (on) next.add(pid);
      else next.delete(pid);
      return next;
    });
  const scan = useJobRunner("Scan", `Scan:${id}`);
  const apply = useJobRunner("Apply", `Apply:${id}`);
  const relight = useJobRunner("Relight", `Relight:${id}`);
  useLiveRows(map.data ? [map.data] : []);
  const name = map.data ? mapName(map.data) : "Map";
  useDocumentTitle(map.isError ? "Map not found" : name);

  if (map.isError && map.error instanceof ApiError && map.error.status === 404) {
    return <NotFoundPage title="Map not found" detail={`No map with id ${id}.`} />;
  }
  const refresh = async () => {
    await client.invalidateQueries({ queryKey: keys.map(id) });
    await client.invalidateQueries({ queryKey: keys.proposals(id) });
    await client.invalidateQueries({ queryKey: ["maps", "library"] });
  };
  // The job now shows on the library rows: refetch the list with its current filters.
  const queued = async (start: Promise<Started>): Promise<Started> => {
    const started = await start;
    void client.invalidateQueries({ queryKey: ["maps", "library"] });
    return started;
  };
  const list = proposals.data ?? [];
  const pendingCount = list.filter((p) => p.status === "pending").length;
  const approveEverything = async () => {
    try {
      await decideOptimistically(client, id, approvePending, () => approveAll(id));
    } catch (err) {
      announce(
        specToInput(`Approve all:${id}`, errorToAlert(err, "Approve all failed"), {
          onRetry: () => void approveEverything(),
        }),
      );
    }
  };
  const remove = async () => {
    if (deleting.current) return;
    deleting.current = true;
    setDeletePending(true);
    try {
      const out = await deleteMap(id);
      await navigate(backHref(origin, back), { replace: true });
      client.removeQueries({ queryKey: keys.map(id) });
      client.removeQueries({ queryKey: keys.proposals(id) });
      void client.invalidateQueries({ queryKey: keys.maps });
      void client.invalidateQueries({ queryKey: keys.jobs });
      announce({ variant: "success", title: "Deleted", message: out.deleted });
    } catch (err) {
      deleting.current = false;
      setDeletePending(false);
      announce({
        variant: "danger",
        title: "Could not delete the map",
        message: errorText(err),
      });
    }
  };
  const approved = list.filter((p) => p.status === "approved").length;
  const clean = map.data ? isCleanCopy(map.data) : false;
  const canCrop = map.data != null && map.data.status !== "unreadable";
  const running = map.data?.job != null || scan.busy || apply.busy || relight.busy;
  const available = tabsFor(canCrop);
  const tab = parseTab(params.get("tab"), available);
  if (tab === "crop" && !cropSeen) setCropSeen(true);
  const select = (next: MapTab) => {
    if (next !== "crop") stopPreview();
    setParams(
      (prev) => {
        const out = new URLSearchParams(prev);
        if (next === "status") out.delete("tab");
        else out.set("tab", next);
        return out;
      },
      { replace: true },
    );
  };

  const statusTab = map.data ? chipTab(statusHref(id, map.data)) : "status";

  return (
    <PageShell active={originTab(origin)} sectionClass="map-page" className="map-bar">
      <BackLink to={backHref(origin, back)} />
      {map.isPending ? (
        <MapHeadSkeleton />
      ) : map.isError ? (
        <SpecAlert
          spec={errorToAlert(map.error, "Could not load the map")}
          onRetry={() => void map.refetch()}
        />
      ) : (
        <div className="maphead">
          <Cover url={map.data.cover_url} big />
          <div className="mapmeta">
            <h1 tabIndex={-1} data-page-heading>
              {name}
            </h1>
            <p className="sub">
              {map.data.mapper || "Unknown mapper"}
              {map.data.status !== "unreadable" && (
                <EnvironmentPicker
                  current={map.data.environment}
                  busy={running}
                  onPick={(env) =>
                    void relight.run(() => queued(relightMap(id, env))).then(refresh)
                  }
                />
              )}
            </p>
            <div className="metarow">
              <StatusChip item={map.data} onSelect={() => select(statusTab)} />
              <LevelChips names={map.data.difficulties} />
              <Tempo item={map.data} />
              <PreviewButton src={map.data.audio_url} start={map.data.preview_start} title={name} />
            </div>
          </div>
        </div>
      )}
      {map.data && <MapTabList available={available} active={tab} onSelect={select} />}
      <div className="map-scroll">
        <MapTabPanel tab="status" active={tab === "status"}>
          {map.data && <FixedCopyLink item={map.data} />}
          {map.data && <FixedCopyOf item={map.data} />}
          <JobOutcome
            toastKey={`Apply:${id}`}
            job={apply.job}
            error={apply.error}
            onRetry={() => void apply.run(() => queued(applyMap(id))).then(refresh)}
            onReview={() => document.getElementById("fixes-top")?.scrollIntoView?.()}
          />
          <JobOutcome
            toastKey={`Scan:${id}`}
            job={scan.job}
            error={scan.error}
            onRetry={() => void scan.run(() => queued(scanMap(id))).then(refresh)}
          />
          <JobOutcome toastKey={`Relight:${id}`} job={relight.job} error={relight.error} />
          {approved === 0 && pendingCount > 0 && (
            <Alert
              variant="info"
              title="No fixes approved yet"
              message="Approve the fixes you want, then choose Apply approved."
            />
          )}
          <span id="fixes-top" />
          {map.data && !clean && (
            <FixToolbar
              item={map.data}
              name={name}
              running={running}
              pendingCount={pendingCount}
              approved={approved}
              proposalCount={list.length}
              onScan={() => void scan.run(() => queued(scanMap(id))).then(refresh)}
              onApproveAll={() => void approveEverything()}
              onApply={() => void apply.run(() => queued(applyMap(id))).then(refresh)}
              onExpandAll={() => setOpenIds(new Set(list.map((p) => String(p.id))))}
              onCollapseAll={() => setOpenIds(new Set())}
            />
          )}
          {proposals.isPending || found.isPending ? (
            <FixesSkeleton />
          ) : proposals.isError ? (
            <SpecAlert
              spec={errorToAlert(proposals.error, "Could not load proposals")}
              onRetry={() => void proposals.refetch()}
            />
          ) : (
            <ProposalGroups
              proposals={list}
              mapId={id}
              open={openIds}
              onToggle={toggleOne}
              findings={found.data?.findings}
              scanned={found.data?.scanned ?? false}
              clean={clean}
            />
          )}
        </MapTabPanel>
        {canCrop && (
          <MapTabPanel tab="crop" active={tab === "crop"}>
            {cropSeen && (
              <CropPanel
                key={id}
                mapId={id}
                folder={map.data?.folder ?? name}
                busy={running}
                audioUrl={map.data?.audio_url}
              />
            )}
          </MapTabPanel>
        )}
        {map.data && (
          <MapTabPanel tab="delete" active={tab === "delete"}>
            <DeletePanel
              folder={map.data.folder ?? name}
              disabled={running}
              pending={deletePending}
              tip={TIPS.delete}
              onDelete={() => void remove()}
              onBack={() => select("status")}
            />
          </MapTabPanel>
        )}
      </div>
      <MapFooter id={id} />
    </PageShell>
  );
}
