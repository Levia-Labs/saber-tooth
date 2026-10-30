import type { ReactNode } from "react";
import { SectionTabs, type SectionKey } from "./SectionTabs";

interface BarProps {
  active: SectionKey;
  /** Text of the screen-reader h1; leave out when the page shows its own visible h1. */
  title?: string;
  className?: string;
  /** Inside the title block, after the tabs. */
  barExtra?: ReactNode;
  /** After the title block, at the bar's right end. */
  barEnd?: ReactNode;
}

/** The title row every page opens with: section tabs, then optional extras. */
export function PageBar({ active, title, className, barExtra, barEnd }: BarProps) {
  return (
    <div className={className ? `lib-bar ${className}` : "lib-bar"}>
      <div className="lib-title">
        <SectionTabs active={active} {...(title ? { heading: title } : {})} />
        {barExtra}
      </div>
      {barEnd}
    </div>
  );
}

interface Props extends BarProps {
  /** Extra classes on the page's section. */
  sectionClass?: string;
  /** Wrap the children in a focusable, labelled scroll region (Settings, About). */
  scroll?: string;
  children: ReactNode;
}

/** One page: its section, the title row, and the content, optionally in a scroll region. */
export function PageShell({ sectionClass, scroll, children, ...bar }: Props) {
  const titled = Boolean(bar.title);
  const cls = [titled ? "library" : "page", sectionClass].filter(Boolean).join(" ");
  return (
    <section className={cls} {...(titled ? { "aria-labelledby": `${bar.active}-heading` } : {})}>
      <PageBar {...bar} />
      {scroll ? (
        <div
          className="lib-scroll about-scroll"
          role="region"
          aria-label={scroll}
          // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- a scroll region must take focus so the keyboard can scroll it
          tabIndex={0}
        >
          {children}
        </div>
      ) : (
        children
      )}
    </section>
  );
}
