import { Link } from "react-router";
import { activeCount, useJobLists } from "../api/joblist";
import { Tip } from "./Tip";

interface Props {
  /** Which section the page belongs to. */
  active: "library" | "beatsaver" | "jobs";
  /** Text of the page's h1, shown to screen readers only. */
  heading: string;
  headingId: string;
}

const ITEMS = [
  { key: "library", to: "/", label: "Library", tip: "Maps in your CustomLevels folder." },
  { key: "beatsaver", to: "/beatsaver", label: "BeatSaver", tip: "Search and download maps." },
  { key: "jobs", to: "/jobs", label: "Jobs", tip: "What the server is working on." },
] as const;

/** Library | BeatSaver | Jobs tabs standing where the page title sits, the Jobs tab with the active job count; the h1 stays for assistive tech. */
export function SectionTabs({ active, heading, headingId }: Props) {
  const count = activeCount(useJobLists());
  return (
    <>
      <h1 id={headingId} className="sr" tabIndex={-1} data-page-heading>
        {heading}
      </h1>
      <nav className="mode-switch" aria-label="Section">
        {ITEMS.map((i) => (
          <Tip key={i.key} text={i.tip}>
            <Link className="pill" to={i.to} aria-current={i.key === active ? "page" : undefined}>
              {i.label}
              {i.key === "jobs" && count > 0 && (
                <span className="tab-count" aria-label={`${count} active`}>
                  {count}
                </span>
              )}
            </Link>
          </Tip>
        ))}
      </nav>
    </>
  );
}
