import { Link } from "react-router";
import { Icon, type IconName } from "../icons";
import { SectionTabs } from "../SectionTabs";
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

interface Props {
  tab: "maps" | "playlists";
  heading: string;
  headingId: string;
  note?: string;
  /** beatsaver.com address the website button opens. */
  siteUrl?: string;
}

/** Title row of the BeatSaver pages: heading, optional note and the Maps | Playlists tabs. */
export function BsTabs({
  tab,
  heading,
  headingId,
  note,
  siteUrl = "https://beatsaver.com",
}: Props) {
  return (
    <div className="lib-bar">
      <div className="lib-title">
        <SectionTabs active="beatsaver" heading={heading} headingId={headingId} />
        {note && <span className="count">{note}</span>}
      </div>
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
      <Tip text="Open beatsaver.com in a new tab">
        <a className="btn icon" href={siteUrl} target="_blank" rel="noopener noreferrer">
          <Icon name="external" />
          <span className="sr">Open BeatSaver website</span>
        </a>
      </Tip>
    </div>
  );
}
