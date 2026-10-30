// Own icon set: 24px grid, 1.75px stroke, round caps and joins, currentColor.
import type { ReactNode, SVGProps } from "react";

const ICONS = {
  search: (
    <>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="M15.5 15.5L20.5 20.5" />
    </>
  ),
  filter: <path d="M4 6h16M7 12h10M10 18h4" />,
  "filter-x": (
    <>
      <path d="M4 6h10M7 12h5M10 18h2" />
      <path d="M15 12l6 6M21 12l-6 6" />
    </>
  ),
  "sort-asc": <path d="M12 19V5M6 11l6-6 6 6" />,
  "sort-desc": <path d="M12 5v14M6 13l6 6 6-6" />,
  trash: <path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6" />,
  scan: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 12l5.5-5.5M12 7.5a4.5 4.5 0 0 1 4.5 4.5" />
      <circle cx="12" cy="12" r="1" />
    </>
  ),
  sweep: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path className="sweep-arm" d="M12 12V4.5" />
    </>
  ),
  review: (
    <>
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" />
      <circle cx="12" cy="12" r="2.8" />
    </>
  ),
  apply: (
    <>
      <path d="M3 7a2 2 0 0 1 2-2h4l2 2.5h8a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <path d="M12 10.5v5M9.5 13h5" />
    </>
  ),
  fix: (
    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
  ),
  approve: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  "approve-all": <path d="M1.5 12.5L6 17l9-9.5M10 16.5l1 .5 9.5-9.5" />,
  expand: <path d="M6 5l6 5 6-5M6 13l6 5 6-5" />,
  collapse: <path d="M6 11l6-5 6 5M6 19l6-5 6 5" />,
  reject: <path d="M6 6l12 12M18 6L6 18" />,
  learn: (
    <>
      <path d="M9 3.5h6l1.5 4h-9z" />
      <path d="M8 12l-2 8.5M12 11v9.5M16 12l2 8.5" />
    </>
  ),
  reset: (
    <>
      <path d="M4.5 12a7.5 7.5 0 1 0 2.3-5.4L4 9.2" />
      <path d="M4 4.5v5h5" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5.2l3.2 2" />
    </>
  ),
  bpm: (
    <>
      <path d="M8.5 21h7l-2-17h-3z" />
      <path d="M12 16l4-8M10.5 12h3" />
    </>
  ),
  more: (
    <>
      <circle cx="12" cy="5.5" r="1" />
      <circle cx="12" cy="12" r="1" />
      <circle cx="12" cy="18.5" r="1" />
    </>
  ),
  generate: (
    <>
      <circle cx="5.5" cy="16" r="2.5" />
      <circle cx="13.5" cy="10" r="2.5" />
      <path d="M8 16V5l8-1.5V10M19 15v6M16 18h6" />
    </>
  ),
  back: <path d="M19 12H5M11 6l-6 6 6 6" />,
  forward: <path d="M5 12h14M13 6l6 6-6 6" />,
  external: (
    <path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" />
  ),
  warning: (
    <>
      <path d="M12 3.5L21.5 20h-19z" />
      <path d="M12 10v4.5M12 17.2v.1" />
    </>
  ),
  error: (
    <>
      <path d="M8.5 3h7L21 8.5v7L15.5 21h-7L3 15.5v-7z" />
      <path d="M12 8v5M12 16.2v.1" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5.5M12 7.8v.1" />
    </>
  ),
  ok: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M7.8 12.4l3 3 5.4-6" />
    </>
  ),
  unscanned: <circle cx="12" cy="12" r="9" strokeDasharray="3 3.2" />,
  unreadable: (
    <>
      <path d="M6 3h8l4 4v14H6zM14 3v4h4" />
      <path d="M9.5 12l5 5M14.5 12l-5 5" />
    </>
  ),
  crop: <path d="M7 3v14h14M3 7h14v14" />,
  scissors: (
    <>
      <circle cx="6" cy="6.5" r="2.5" />
      <circle cx="6" cy="17.5" r="2.5" />
      <path d="M8 8l12 9M8 16l12-9" />
    </>
  ),
  spinner: <path d="M12 3a9 9 0 1 0 9 9" />,
  chevron: <path d="M6 9l6 6 6-6" />,
  upload: <path d="M12 16V4M7 9l5-5 5 5M4 17v3h16v-3" />,
  library: (
    <>
      <path d="M5 4v16M10 4v16" />
      <path d="M15 5.5l4-1 3.5 14.5-4 1z" />
    </>
  ),
  queue: (
    <>
      <path d="M9 6h12M9 12h12M9 18h12" />
      <path d="M3.5 6h.1M3.5 12h.1M3.5 18h.1" />
    </>
  ),
  headset: (
    <>
      <path d="M3 9.5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2h-3.5l-1.7-2.5h-3.6L8.5 17.5H5a2 2 0 0 1-2-2z" />
      <path d="M3 12.5H2M21 12.5h1" />
    </>
  ),
  monitor: (
    <>
      <rect x="3" y="4.5" width="18" height="12" rx="1.5" />
      <path d="M9 20h6M12 16.5V20" />
    </>
  ),
  download: <path d="M12 4v12M7 11l5 5 5-5M4 17v3h16v-3" />,
  play: <path d="M8 5l11 7-11 7z" />,
  stop: <rect x="6" y="6" width="12" height="12" rx="1.5" />,
  pause: <path d="M8 5v14M16 5v14" />,
  playlist: <path d="M4 6h12M4 11h12M4 16h7M17 14v6l5-3z" />,
  plus: <path d="M12 5v14M5 12h14" />,
  edit: <path d="M4 20h4L19.5 8.5l-4-4L4 16zM13.5 6.5l4 4" />,
  "tag-plus": (
    <>
      <path d="M3.5 12.5V4.5a1 1 0 0 1 1-1h8l8 8-8.5 8.5z" />
      <circle cx="8.5" cy="8.5" r="1.2" />
      <path d="M14.5 17v5M12 19.5h5" />
    </>
  ),
  maps: <path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" />,
  "thumb-up": (
    <path d="M7 11v9H4v-9zM7 11l4-7c1.7 0 2.5 1.2 2.2 2.8L12.8 9H19a2 2 0 0 1 2 2.3l-1 6.5A2 2 0 0 1 18 20H7" />
  ),
  bookmark: <path d="M7 4h10v16l-5-4-5 4z" />,
  "bookmark-plus": (
    <>
      <path d="M6.5 4.2h11v15.8l-5.5-4-5.5 4z" />
      <path d="M12 7.6v4.8M9.6 10h4.8" />
    </>
  ),
  "saved-filter": (
    <>
      <path d="M3.8 5.2c5.4-.4 10.8-.4 16.2 0l-6.2 7v6.6l-3.6 1.8v-8.4z" />
      <path d="M14.8 17.6l2 2 3.6-4" />
    </>
  ),
  github: (
    <path d="M9 19c-4.3 1.4-4.3-2.5-6-3m12 5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.2 4.2 0 0 0-.1-3.2s-1.1-.3-3.5 1.3a12.3 12.3 0 0 0-6.2 0C6.5 2.8 5.4 3.1 5.4 3.1a4.2 4.2 0 0 0-.1 3.2A4.6 4.6 0 0 0 4 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21" />
  ),
  docker: (
    <>
      <path d="M2.5 12.5h17.5c1-.3 2-.1 2.5.6-.7 1-1.7 1.2-2.6 1.1C18.5 18 15 20 11 20c-4.5 0-7.5-3-8.5-7.5z" />
      <path d="M5 9.5h3v3H5zM9 9.5h3v3H9zM13 9.5h3v3h-3zM9 6h3v3.5H9z" />
    </>
  ),
  book: <path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3zM5 17a3 3 0 0 1 3-3h11" />,
  plug: <path d="M9 3v5M15 3v5M6.5 8h11v3a5.5 5.5 0 0 1-11 0zM12 16.5V21" />,
  globe: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18" />
    </>
  ),
  wave: <path d="M3 12h2l2-6 3 12 3-9 2 5 2-2h4" />,
  layers: <path d="M12 3l9 5-9 5-9-5zM3 13l9 5 9-5" />,
  lock: (
    <>
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </>
  ),
  shield: <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" />,
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
    </>
  ),
} satisfies Record<string, ReactNode>;

export type IconName = keyof typeof ICONS;
export const ICON_NAMES = Object.keys(ICONS) as IconName[];

interface IconProps extends Omit<SVGProps<SVGSVGElement>, "name"> {
  name: IconName;
  filled?: boolean;
}

export function Icon({ name, filled = false, className, ...rest }: IconProps) {
  // A spinner always turns: callers passing it as a plain icon name once rendered it frozen.
  const spin = name === "spinner" && !className?.includes("alert-spin") ? "alert-spin" : "";
  const cls = ["ic", filled ? "ic-filled" : "", spin, className ?? ""].filter(Boolean).join(" ");
  return (
    <svg viewBox="0 0 24 24" className={cls} aria-hidden="true" focusable="false" {...rest}>
      {ICONS[name]}
    </svg>
  );
}
