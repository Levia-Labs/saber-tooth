import { Link } from "react-router";
import { Tip } from "./Tip";

interface Props {
  /** Which section the page belongs to. */
  active: "library" | "beatsaver";
  /** Text of the page's h1, shown to screen readers only. */
  heading: string;
  headingId: string;
}

const ITEMS = [
  { key: "library", to: "/", label: "Library", tip: "Maps in your CustomLevels folder." },
  { key: "beatsaver", to: "/beatsaver", label: "BeatSaver", tip: "Search and download maps." },
] as const;

/** Library | BeatSaver tabs standing where the page title sits; the h1 stays for assistive tech. */
export function SectionTabs({ active, heading, headingId }: Props) {
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
            </Link>
          </Tip>
        ))}
      </nav>
    </>
  );
}
