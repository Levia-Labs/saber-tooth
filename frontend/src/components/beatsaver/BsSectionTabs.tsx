import { PillTabs, type PillTab } from "../PillTabs";

const TABS = [
  { key: "maps", label: "Maps", icon: "maps", path: "/beatsaver", tip: "Search BeatSaver maps." },
  {
    key: "playlists",
    label: "Playlists",
    icon: "playlist",
    path: "/beatsaver/playlists",
    tip: "Search playlists.",
  },
] as const satisfies readonly PillTab[];

export type BsTab = "maps" | "playlists";

/** The Maps | Playlists switch, the right end of the toolbar row: the section tab bar, reused. */
export function BsSectionTabs({ tab }: { tab: BsTab }) {
  return (
    <PillTabs
      label="BeatSaver sections"
      tabs={TABS}
      active={tab}
      className="bs-tabs"
      iconOnlyOnMobile
    />
  );
}
