import { formatEnvironment } from "../lib/environment";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router";
import { ApiError, applyMap, approveAll, scanMap } from "../api/client";
import { Alert, SpecAlert } from "../components/Alert";
import { FixesSkeleton, MapHeadSkeleton } from "../components/Skeletons";
import { errorToAlert } from "../lib/alerts";
import { FixButton } from "../components/FixButton";
import { FixOutcomes } from "../components/FixOutcomes";
import { useJobRunner } from "../api/jobs";
import { keys, useLiveRows, useMap, useProposals } from "../api/queries";
import { ActionButton } from "../components/Buttons";
import { Cover, LevelChips, StatusChip, Tempo } from "../components/Chips";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { Icon } from "../components/icons";
import { JobOutcome } from "../components/JobOutcome";
import { ProposalGroups } from "../components/ProposalGroups";
import { useDocumentTitle, libraryHref } from "../lib/hooks";
import { applyTip, TIPS } from "../lib/tips";
import { mapName } from "../lib/status";
import { NotFoundPage } from "./NotFoundPage";

export function MapPage() {
  const { id = "" } = useParams();
  const client = useQueryClient();
  const map = useMap(id);
  const proposals = useProposals(id);
  const [approveError, setApproveError] = useState<unknown>(null);
  const scan = useJobRunner("Scan");
  const apply = useJobRunner("Apply");
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
  const list = proposals.data ?? [];
  const pendingCount = list.filter((p) => p.status === "pending").length;
  const approveEverything = async () => {
    setApproveError(null);
    try {
      await approveAll(id);
      await refresh();
    } catch (err) {
      setApproveError(err);
    }
  };
  const approved = list.filter((p) => p.status === "approved").length;
  const running = map.data?.job != null || scan.busy || apply.busy;

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
              {map.data.environment ? ` - ${formatEnvironment(map.data.environment)}` : ""}
            </p>
            <div className="metarow">
              <StatusChip item={map.data} />
              <LevelChips names={map.data.difficulties} />
              <Tempo item={map.data} />
            </div>
          </div>
        </div>
      )}
      <FixOutcomes mapId={id} />
      <JobOutcome
        job={apply.job}
        error={apply.error}
        onRetry={() => void apply.run(() => applyMap(id)).then(refresh)}
        onReview={() => document.getElementById("fixes-top")?.scrollIntoView?.()}
      />
      <JobOutcome
        job={scan.job}
        error={scan.error}
        onRetry={() => void scan.run(() => scanMap(id)).then(refresh)}
      />
      {approveError !== null && (
        <SpecAlert
          spec={errorToAlert(approveError, "Approve all failed")}
          onRetry={() => void approveEverything()}
          onDismiss={() => setApproveError(null)}
        />
      )}
      {approved === 0 && pendingCount > 0 && (
        <Alert
          variant="info"
          title="No fixes approved yet"
          message="Approve the fixes you want, then choose Apply approved."
        />
      )}
      <span id="fixes-top" />
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
          actions={
            <>
              {map.data && <FixButton item={map.data} text />}
              <ActionButton
                icon="scan"
                label="Scan"
                tip={TIPS.scan}
                text
                disabled={running || map.data?.status === "unreadable"}
                onClick={() => void scan.run(() => scanMap(id)).then(refresh)}
              />
              <ConfirmDialog
                title="Approve all fixes"
                description={`Approve every pending proposal for "${name}"?`}
                confirmLabel="Approve all"
                onConfirm={() => void approveEverything()}
              >
                <ActionButton
                  icon="approve-all"
                  label="Approve all"
                  tip={TIPS.approveAll}
                  text
                  disabled={pendingCount === 0}
                />
              </ConfirmDialog>
              <ActionButton
                icon="apply"
                label="Apply approved"
                tip={applyTip(name)}
                text
                variant="primary"
                disabled={running || approved === 0}
                onClick={() => void apply.run(() => applyMap(id)).then(refresh)}
              />
            </>
          }
        />
      )}
    </section>
  );
}
