import { percent } from "../../lib/settingsfmt";

interface Props {
  label: string;
  value: number | null;
  max: number | null;
  /** Visible reading beside the bar. */
  text: string;
}

/** A labelled horizontal meter: name and reading above, a filled bar below. */
export function Meter({ label, value, max, text }: Props) {
  const pct = percent(value, max);
  return (
    <div className="settings-meter">
      <div className="settings-meter-row">
        <span>{label}</span>
        <span className="settings-meter-text">{text}</span>
      </div>
      <div
        className="settings-meter-bar"
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
        aria-valuetext={text}
      >
        <span style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
