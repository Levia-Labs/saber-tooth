import type { MapItem } from "../api/types";
import { applyTip, TIPS } from "../lib/tips";
import { ActionButton } from "./Buttons";
import { ConfirmDialog } from "./ConfirmDialog";
import { FixButton } from "./FixButton";

interface Props {
  item: MapItem;
  name: string;
  running: boolean;
  pendingCount: number;
  approved: number;
  proposalCount: number;
  onScan: () => void;
  onApproveAll: () => void;
  onApply: () => void;
  onExpandAll: () => void;
  onCollapseAll: () => void;
}

/** The Fix actions on the Status tab; not shown on a clean fixed copy. */
export function FixToolbar(p: Props) {
  return (
    <div className="map-toolbar" role="toolbar" aria-label="Fix actions">
      <FixButton item={p.item} text />
      <ActionButton
        icon="scan"
        label="Scan"
        tip={TIPS.scan}
        text
        disabled={p.running || p.item.status === "unreadable"}
        onClick={p.onScan}
      />
      <ConfirmDialog
        title="Approve all fixes"
        description={`Approve every pending proposal for "${p.name}"?`}
        confirmLabel="Approve all"
        onConfirm={p.onApproveAll}
      >
        <ActionButton
          icon="approve-all"
          label="Approve all"
          tip={TIPS.approveAll}
          text
          disabled={p.pendingCount === 0}
        />
      </ConfirmDialog>
      <ActionButton
        icon="apply"
        label="Apply approved"
        tip={applyTip(p.name)}
        text
        variant="primary"
        disabled={p.running || p.approved === 0}
        onClick={p.onApply}
      />
      <span className="spacer" />
      <ActionButton
        icon="expand"
        label="Expand all"
        tip="Open every fix."
        text
        disabled={p.proposalCount === 0}
        onClick={p.onExpandAll}
      />
      <ActionButton
        icon="collapse"
        label="Collapse all"
        tip="Close every fix."
        text
        disabled={p.proposalCount === 0}
        onClick={p.onCollapseAll}
      />
    </div>
  );
}
