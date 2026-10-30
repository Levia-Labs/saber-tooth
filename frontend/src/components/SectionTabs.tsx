import { activeCount, useJobLists } from "../api/joblist";
import { PillTabs, type PillTab } from "./PillTabs";

interface Props {
  /** Which section the page belongs to. */
  active: SectionKey;
  /** Text of the page's h1, shown to screen readers only. */
  heading: string;
  headingId: string;
  /** The page shows its own visible h1 (map and playlist pages); leave the screen-reader one out. */
  noHeading?: boolean;
}

/** The tabs in order; a new section is one more entry here (About stays last). Playlists, when it joins, uses the `playlist` icon. */
const ITEMS = [
  {
    key: "library",
    path: "/",
    label: "Library",
    icon: "library",
    tip: "Maps in your CustomLevels folder.",
  },
  {
    key: "beatsaver",
    path: "/beatsaver",
    label: "BeatSaver",
    icon: "download",
    tip: "Search and download maps.",
  },
  {
    key: "jobs",
    path: "/jobs",
    label: "Jobs",
    icon: "queue",
    tip: "What the server is working on.",
  },
  {
    key: "playlists",
    path: "/playlists",
    label: "Playlists",
    icon: "playlist",
    tip: "Build and export Beat Saber playlists.",
  },
  {
    key: "settings",
    path: "/settings",
    label: "Settings",
    icon: "settings",
    tip: "Service controls and mods.",
  },
  {
    key: "about",
    path: "/about",
    label: "About",
    icon: "info",
    tip: "What Saber Tooth is and how to use it.",
  },
] as const satisfies readonly PillTab[];

type SectionKey = (typeof ITEMS)[number]["key"];

/** Library | BeatSaver | Jobs | About tabs standing where the page title sits, the Jobs tab with the active job count; the h1 stays for assistive tech. */
export function SectionTabs({ active, heading, headingId, noHeading }: Props) {
  const count = activeCount(useJobLists());
  const tabs: PillTab[] = ITEMS.map((i) => (i.key === "jobs" ? { ...i, badge: count } : i));
  return (
    <>
      {!noHeading && (
        <h1 id={headingId} className="sr" tabIndex={-1} data-page-heading>
          {heading}
        </h1>
      )}
      <PillTabs label="Section" tabs={tabs} active={active} className="section-tabs" />
    </>
  );
}
