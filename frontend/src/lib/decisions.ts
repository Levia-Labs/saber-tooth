// Which decisions the API still accepts for a proposal, so the buttons never offer a refused one.
const SETTLED: readonly string[] = ["applied", "applying", "superseded"];

/** Approve is offered only while the proposal is open: pending or rejected. */
export function canApprove(status: string): boolean {
  return !SETTLED.includes(status) && status !== "approved";
}

/** Reject stays available on an approved proposal so the user can undo it. */
export function canReject(status: string): boolean {
  return !SETTLED.includes(status) && status !== "rejected";
}
