import { Link } from "react-router";
import { Icon, type IconName } from "../icons";
import { Tip } from "../Tip";

const TABS = [
  {
    key: "maps",
    label: "Maps",
    icon: "maps" as IconName,
    to: "/beatsaver",
    tip: "Search BeatSaver maps.",
  },
  {
    key: "playlists",
    label: "Playlists",
    icon: "playlist" as IconName,
    to: "/beatsaver/playlists",
    tip: "Search playlists.",
  },
] as const;

export type BsTab = "maps" | "playlists";

/** The Maps | Playlists switch, the right end of the toolbar row. */
export function BsSectionTabs({ tab }: { tab: BsTab }) {
  return (
    <nav className="bs-tabs" aria-label="BeatSaver sections">
      {TABS.map((t) => (
        <Tip key={t.key} text={t.tip}>
          <Link to={t.to} className="btn plain" aria-current={t.key === tab ? "page" : undefined}>
            <Icon name={t.icon} />
            <span className="label-hide-mobile">{t.label}</span>
          </Link>
        </Tip>
      ))}
    </nav>
  );
}
