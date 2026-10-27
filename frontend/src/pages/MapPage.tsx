import { formatEnvironment } from "../lib/environment";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router";
import { ApiError, applyMap, approveAll, errorMessage, scanMap } from "../api/client";
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
  const [approveError, setApproveError] = useState<string | null>(null);
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
      setApproveError(errorMessage(err));
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
        <p className="muted" role="status">
          Loading map
        </p>
      ) : map.isError ? (
        <p className="err">Could not load the map: {errorMessage(map.error)}</p>
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
      <JobOutcome job={apply.job} error={apply.error} />
      {approveError && <p className="err">Approve all failed: {approveError}</p>}
      {scan.error && <p className="err">Scan failed: {scan.error}</p>}
      {proposals.isPending ? null : proposals.isError ? (
        <p className="err">Could not load proposals: {errorMessage(proposals.error)}</p>
      ) : (
        <ProposalGroups
          proposals={list}
          mapId={id}
          actions={
            <>
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
