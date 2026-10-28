// The map page tabs: which exist, which one the URL names, and where an arrow key moves.
import type { IconName } from "../components/icons";

export type MapTab = "status" | "crop" | "delete";

export const MAP_TABS: readonly { key: MapTab; label: string; icon: IconName }[] = [
  { key: "status", label: "Status", icon: "info" },
  { key: "crop", label: "Crop", icon: "scissors" },
  { key: "delete", label: "Delete", icon: "trash" },
];

/** The tabs on offer; Crop is left out when the map cannot be cropped. */
export const tabsFor = (canCrop: boolean): readonly MapTab[] =>
  MAP_TABS.map((t) => t.key).filter((k) => canCrop || k !== "crop");

/** The tab a `?tab=` value names, among the tabs on offer; anything else is Status. */
export function parseTab(raw: string | null, available: readonly MapTab[]): MapTab {
  return available.find((k) => k === raw) ?? "status";
}

/** The tab a key moves to from `current` (wrapping, Home, End), or null for any other key. */
export function tabForKey(
  key: string,
  current: MapTab,
  available: readonly MapTab[],
): MapTab | null {
  const at = available.indexOf(current);
  const n = available.length;
  if (at === -1 || n === 0) return null;
  if (key === "ArrowRight") return available[(at + 1) % n] ?? null;
  if (key === "ArrowLeft") return available[(at + n - 1) % n] ?? null;
  if (key === "Home") return available[0] ?? null;
  if (key === "End") return available[n - 1] ?? null;
  return null;
}
