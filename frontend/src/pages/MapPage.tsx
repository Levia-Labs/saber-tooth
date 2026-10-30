import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
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
import { useJobRunner } from "../api/jobs";
import { keys, useLiveRows, useMap, useProposals } from "../api/queries";
import { Cover, LevelChips, StatusChip, Tempo } from "../components/Chips";
import { PreviewButton } from "../components/PreviewButton";
import { Icon } from "../components/icons";
import { JobOutcome } from "../components/JobOutcome";
import { ProposalGroups } from "../components/ProposalGroups";
import { useDocumentTitle, libraryHref } from "../lib/hooks";
import { TIPS } from "../lib/tips";
import { isCleanCopy, mapName } from "../lib/status";
import { NotFoundPage } from "./NotFoundPage";

export function MapPage() {
  const { id = "" } = useParams();
  const client = useQueryClient();
  const navigate = useNavigate();
  const announce = useAnnounce();
  const map = useMap(id);
  const proposals = useProposals(id);
  const [params, setParams] = useSearchParams();
  const [cropSeen, setCropSeen] = useState(false);
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
      await approveAll(id);
      await refresh();
    } catch (err) {
      announce(
        specToInput(`Approve all:${id}`, errorToAlert(err, "Approve all failed"), {
          onRetry: () => void approveEverything(),
        }),
      );
    }
  };
  const remove = async () => {
    try {
      const out = await deleteMap(id);
      client.removeQueries({ queryKey: keys.map(id) });
      client.removeQueries({ queryKey: keys.proposals(id) });
      await navigate("/");
      await client.invalidateQueries({ queryKey: ["maps"] });
      announce({ variant: "success", title: "Deleted", message: out.deleted });
    } catch (err) {
      announce({
        variant: "danger",
        title: "Could not delete the map",
        message: err instanceof Error ? err.message : "unknown error",
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

  return (
    <section className="page map-page">
      <Link className="back" to={libraryHref()}>
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
              <StatusChip item={map.data} />
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
          {proposals.isPending ? (
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
              tip={TIPS.delete}
              onDelete={() => void remove()}
              onBack={() => select("status")}
            />
          </MapTabPanel>
        )}
      </div>
      <MapFooter id={id} />
    </section>
  );
}
