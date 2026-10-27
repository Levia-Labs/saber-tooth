import { useState } from "react";
import type { MapItem } from "../api/types";
import { formatBpm, formatDuration } from "../lib/format";
import { levelSlots, ringText } from "../lib/levels";
import { STATUS_META, statusLabel, statusText } from "../lib/status";
import { Icon } from "./icons";
import { Tip } from "./Tip";
import { LogoGlyph } from "./Logo";

export function StatusChip({
  item,
}: {
  item: Pick<MapItem, "status" | "errors" | "warnings"> & Partial<Pick<MapItem, "parse_error">>;
}) {
  const kind = Object.hasOwn(STATUS_META, item.status) ? item.status : "unscanned";
  const full = { ...item, status: kind };
  const label = statusLabel(full);
  const text = statusText(full);
  return (
    <Tip text={label}>
      <span className={`chip chip-${kind}`} data-status={kind} role="img" aria-label={label}>
        <Icon name={STATUS_META[kind].icon} />
        {text !== null && (
          <span className="chip-text" aria-hidden="true">
            {text}
          </span>
        )}
      </span>
    </Tip>
  );
}

/** Outlined, abbreviated level chips; the full name and the NPS (when known) are in the Tip. */
export function LevelChips({
  names,
  className,
  nps,
}: {
  names: readonly string[];
  className?: string;
  /** Notes per second by level key, when known. */
  nps?: Readonly<Record<string, number>>;
}) {
  return (
    <ul className={`levels ${className ?? ""}`.trim()} aria-label="Difficulties">
      {levelSlots(names).map(({ level: l, present }) => {
        if (!present) {
          const gone = `Missing: ${l.label}`;
          return (
            <li key={l.key} className="level missing">
              <Tip text={gone}>
                <span className="level-text" role="img" aria-label={gone}>
                  <span aria-hidden="true">{l.abbr}</span>
                </span>
              </Tip>
            </li>
          );
        }
        const rate = nps?.[l.key];
        const full = rate === undefined ? l.label : `${l.label}, ${rate.toFixed(1)} NPS`;
        return (
          <li key={l.key} className="level" style={{ borderColor: l.bg, color: ringText(l.bg) }}>
            <Tip text={full}>
              <span className="level-text" role="img" aria-label={full}>
                <span aria-hidden="true">{l.abbr}</span>
              </span>
            </Tip>
          </li>
        );
      })}
    </ul>
  );
}

export function Cover({ url, big = false }: { url: string | null; big?: boolean }) {
  const [failed, setFailed] = useState(false);
  const size = big ? " cover-big" : "";
  if (!url || failed) {
    return (
      <span className={`cover cover-empty${size}`}>
        <LogoGlyph />
      </span>
    );
  }
  return (
    <img
      className={`cover${size}`}
      src={url}
      alt=""
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
    />
  );
}

export function Tempo({ item }: { item: Pick<MapItem, "bpm" | "duration_s"> }) {
  return (
    <span className="tempo">
      <span className="tempo-item">
        <Icon name="clock" />
        {formatDuration(item.duration_s)}
      </span>
      <span className="tempo-item">
        <Icon name="bpm" />
        {formatBpm(item.bpm)}
      </span>
    </span>
  );
}
