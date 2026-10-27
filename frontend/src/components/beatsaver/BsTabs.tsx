import { Link } from "react-router";
import { Tip } from "../Tip";

const TABS = [
  { key: "maps", label: "Maps", to: "/beatsaver", tip: "Search BeatSaver maps." },
  { key: "playlists", label: "Playlists", to: "/beatsaver/playlists", tip: "Search playlists." },
] as const;

interface Props {
  tab: "maps" | "playlists";
  heading: string;
  headingId: string;
  note?: string;
}

/** Title row of the BeatSaver pages: heading, optional note and the Maps | Playlists tabs. */
export function BsTabs({ tab, heading, headingId, note }: Props) {
  return (
    <div className="lib-bar">
      <div className="lib-title">
        <h1 id={headingId} tabIndex={-1} data-page-heading>
          {heading}
        </h1>
        {note && <span className="count">{note}</span>}
      </div>
      <nav className="bs-tabs" aria-label="BeatSaver sections">
        {TABS.map((t) => (
          <Tip key={t.key} text={t.tip}>
            <Link to={t.to} className="btn plain" aria-current={t.key === tab ? "page" : undefined}>
              {t.label}
            </Link>
          </Tip>
        ))}
      </nav>
    </div>
  );
}
