// Tooltip copy, one place so every button explains itself the same way.
export const TIPS = {
  scan: "Check this map for impossible patterns, empty sections and missing difficulties. Creates fix proposals for you to review. Nothing is written yet.",
  review: "Open this map's page to see what was found and approve or reject each proposed fix.",
  apply:
    "Write the fixes you approved into a new folder named '<map> [saber-tooth]'. The original map is never changed.",
  learn:
    "Study the lighting in the maps you have installed. saber-tooth reuses those patterns to light maps that still use the default environment. Run it once, and again after adding new maps.",
  generate:
    "Create a new map with all five difficulties from a YouTube link or an audio file. You review it before anything is written.",
  resetColumns: "Reset column widths to their defaults.",
  approve: "Accept this fix. It is written when you click Apply.",
  reject: "Discard this fix.",
  approveAll: "Accept every proposed fix for this map. They are written when you click Apply.",
} as const;

export function applyTip(mapName: string): string {
  return TIPS.apply.replace("<map>", mapName);
}
