import { tickLabel, timeTicks, yFrac } from "../lib/axis";
import { LEVELS, levelColor } from "../lib/levels";

/** Notes-per-second values down the left edge, on the same scale as the lines. */
export function YAxis({ ticks, top }: { ticks: number[]; top: number }) {
  return (
    <div className="nps-yaxis" data-testid="y-axis" aria-hidden="true">
      {ticks.map((t) => (
        <span key={t} className="nps-ytick" style={{ bottom: `${yFrac(t, top) * 100}%` }}>
          {t}
        </span>
      ))}
    </div>
  );
}

/** Time ticks (mm:ss) under the chart. */
export function TimeAxis({ duration }: { duration: number }) {
  return (
    <div className="nps-xaxis" data-testid="time-axis" aria-hidden="true">
      {timeTicks(duration).map((t) => (
        <span key={t} className="nps-xtick" style={{ left: `${(t / duration) * 100}%` }}>
          {tickLabel(t)}
        </span>
      ))}
    </div>
  );
}

/** One swatch per difficulty line, in the colour the line and the library chips use. */
export function Legend({ names }: { names: string[] }) {
  return (
    <ul className="nps-legend" aria-label="Difficulty colours">
      {names.map((name) => (
        <li key={name}>
          <svg viewBox="0 0 16 4" width="16" height="4" aria-hidden="true">
            <line x1="0" x2="16" y1="2" y2="2" stroke={levelColor(name) ?? "currentColor"} />
          </svg>
          {LEVELS.find((l) => l.key === name)?.label ?? name}
        </li>
      ))}
    </ul>
  );
}
