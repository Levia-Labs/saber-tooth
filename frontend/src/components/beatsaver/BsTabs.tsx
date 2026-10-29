import { Icon } from "../icons";
import { BarSlot } from "../BarSlot";
import { SectionTabs } from "../SectionTabs";
import { BsSectionTabs, type BsTab } from "./BsSectionTabs";
import { Tip } from "../Tip";

interface Props {
  heading: string;
  headingId: string;
  note?: string;
  /** beatsaver.com address the website button opens. */
  siteUrl?: string;
  /** Which of the Maps | Playlists tabs is current. */
  tab?: BsTab;
}

/** Title row of the BeatSaver pages: heading, optional note and the website button and, at the right end, the toolbar. */
export function BsTabs({
  heading,
  headingId,
  note,
  siteUrl = "https://beatsaver.com",
  tab = "maps",
}: Props) {
  return (
    <div className="lib-bar">
      <div className="lib-title">
        <SectionTabs active="beatsaver" heading={heading} headingId={headingId} />
        <BsSectionTabs tab={tab} />
        {note && <span className="count">{note}</span>}
        <Tip text="Open beatsaver.com in a new tab">
          <a className="btn icon" href={siteUrl} target="_blank" rel="noopener noreferrer">
            <Icon name="external" />
            <span className="sr">Open BeatSaver website</span>
          </a>
        </Tip>
      </div>
      <BarSlot />
    </div>
  );
}
