import type { KeyboardEvent } from "react";
import { Link } from "react-router";
import { Icon, type IconName } from "./icons";
import { Tip } from "./Tip";

export interface PillTab {
  key: string;
  path: string;
  label: string;
  icon: IconName;
  tip: string;
  /** A count shown after the label when above zero. */
  badge?: number;
}

interface Props {
  /** Accessible name of the navigation. */
  label: string;
  tabs: readonly PillTab[];
  /** Key of the tab whose route is current. */
  active: string;
  /** Extra class on the nav, for its place in a toolbar. */
  className?: string;
}

/** Move focus along the links with the arrow keys, Home and End. */
function arrows(e: KeyboardEvent<HTMLElement>): void {
  const keys = ["ArrowLeft", "ArrowRight", "Home", "End"];
  if (!keys.includes(e.key)) return;
  const links = Array.from(e.currentTarget.querySelectorAll<HTMLAnchorElement>("a.pill"));
  const at = links.indexOf(document.activeElement as HTMLAnchorElement);
  if (at < 0) return;
  const last = links.length - 1;
  const to =
    e.key === "Home"
      ? 0
      : e.key === "End"
        ? last
        : e.key === "ArrowRight"
          ? Math.min(last, at + 1)
          : Math.max(0, at - 1);
  e.preventDefault();
  links[to]?.focus();
}

/** The segmented tab bar: the section tabs and the BeatSaver Maps | Playlists switch share it. */
export function PillTabs({ label, tabs, active, className }: Props) {
  return (
    // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions -- arrow keys only move focus between the links
    <nav
      className={["mode-switch", className].filter(Boolean).join(" ")}
      aria-label={label}
      onKeyDown={arrows}
    >
      {tabs.map((t) => (
        <Tip key={t.key} text={t.tip}>
          <Link
            className="pill"
            to={t.path}
            aria-current={t.key === active ? "page" : undefined}
            aria-label={t.label}
          >
            <Icon name={t.icon} />
            <span className="label-hide-mobile">{t.label}</span>
            {t.badge !== undefined && t.badge > 0 && (
              <span className="tab-count" aria-label={`${t.badge} active`}>
                {t.badge}
              </span>
            )}
          </Link>
        </Tip>
      ))}
    </nav>
  );
}
