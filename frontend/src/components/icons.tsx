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
  "sort-asc": <path d="M12 19V5M6 11l6-6 6 6" />,
  "sort-desc": <path d="M12 5v14M6 13l6 6 6-6" />,
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
  approve: <path d="M5 12.5l4.5 4.5L19 7.5" />,
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
  spinner: <path d="M12 3a9 9 0 1 0 9 9" />,
  chevron: <path d="M6 9l6 6 6-6" />,
  upload: <path d="M12 16V4M7 9l5-5 5 5M4 17v3h16v-3" />,
  download: <path d="M12 4v12M7 11l5 5 5-5M4 17v3h16v-3" />,
  play: <path d="M8 5l11 7-11 7z" />,
  stop: <rect x="6" y="6" width="12" height="12" rx="1.5" />,
  playlist: <path d="M4 6h12M4 11h12M4 16h7M17 14v6l5-3z" />,
  bookmark: <path d="M7 4h10v16l-5-4-5 4z" />,
} satisfies Record<string, ReactNode>;

export type IconName = keyof typeof ICONS;
export const ICON_NAMES = Object.keys(ICONS) as IconName[];

interface IconProps extends Omit<SVGProps<SVGSVGElement>, "name"> {
  name: IconName;
  filled?: boolean;
}

export function Icon({ name, filled = false, className, ...rest }: IconProps) {
  const cls = ["ic", filled ? "ic-filled" : "", className ?? ""].filter(Boolean).join(" ");
  return (
    <svg viewBox="0 0 24 24" className={cls} aria-hidden="true" focusable="false" {...rest}>
      {ICONS[name]}
    </svg>
  );
}
