import { useId } from "react";

/** The full-colour logo mark (same geometry as favicon.svg). */
export function Logo({ size = 52 }: { size?: number }) {
  const id = useId();
  const glow = `${id}-glow`;
  const red = "M78 78C68 134 90 182 118 216";
  const blue = "M178 78C188 134 166 182 138 216";
  return (
    <svg className="logo" viewBox="0 0 256 256" width={size} height={size} aria-hidden="true">
      <defs>
        <filter id={glow} x="-50%" y="-30%" width="200%" height="160%">
          <feGaussianBlur stdDeviation="7" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <rect width="256" height="256" rx="48" fill="#07070D" />
      <g fill="none" strokeLinecap="round">
        <path d="M40 72Q128 38 216 72" stroke="#8b8ba7" strokeWidth="10" />
        <g filter={`url(#${glow})`}>
          <path d={red} stroke="#C81414" strokeWidth="16" />
          <path d={blue} stroke="#288ED2" strokeWidth="16" />
        </g>
        <path d={red} stroke="#FF3B3B" strokeWidth="9" />
        <path d={blue} stroke="#4FC3FF" strokeWidth="9" />
        <path d={`${red}M${blue.slice(1)}`} stroke="#fff" strokeWidth="3" />
        <path d="M64 72h28M164 72h28" stroke="#2a2a3a" strokeWidth="12" />
      </g>
    </svg>
  );
}

/** Tinted logo geometry for empty covers. */
export function LogoGlyph() {
  return (
    <svg viewBox="0 0 256 256" className="ic glyph" aria-hidden="true" focusable="false">
      <g fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="14">
        <path d="M40 72Q128 38 216 72" />
        <path d="M78 78C68 134 90 182 118 216M178 78C188 134 166 182 138 216" />
      </g>
    </svg>
  );
}
