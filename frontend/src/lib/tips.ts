// Tooltip copy, one place so every button explains itself the same way.
export const TIPS = {
  scan: "Check this map for impossible patterns, empty sections and missing difficulties. Creates fix proposals for you to review. Nothing is written yet.",
  fix: "Fix this map: adds missing difficulties and fixes every error, then writes a new '<map> [saber-tooth]' folder. The original is never changed.",
  review: "Open this map's page to see what was found and approve or reject each proposed fix.",
  apply:
    "Write the fixes you approved into a new folder named '<map> [saber-tooth]'. The original map is never changed.",
  learn:
    "Add the lighting styles of the maps you have installed to the built-in set. Optional: Saber Tooth already lights maps with its bundled set.",
  generate:
    "Create a new map with all five difficulties from a YouTube link or an audio file. The map is fixed and written to your library in one step.",
  resetColumns: "Reset column widths to their defaults.",
  approve: "Accept this fix. It is written when you click Apply.",
  reject: "Discard this fix.",
  overlaps:
    "Approving both is fine: Saber Tooth applies them in order and re-checks the later one.",
  delete: "Delete this map folder from disk for good. This cannot be undone.",
  approveAll: "Accept every proposed fix for this map. They are written when you click Apply.",
} as const;

export function applyTip(mapName: string): string {
  return TIPS.apply.replace("<map>", mapName);
}
