import { useState } from "react";
import type { MapItem } from "../api/types";
import { formatBpm, formatDuration } from "../lib/format";
import { levelColor, levelSlots } from "../lib/levels";
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

/**
 * Plain-text level display "Ea | No | Ha | Ex | Ex+": present levels in their beatsaver colour,
 * missing ones muted so gaps stay visible. The full name and the NPS (when known) are in the Tip.
 */
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
    <span className={`levels ${className ?? ""}`.trim()} role="group" aria-label="Difficulties">
      {levelSlots(names).map(({ level: l, present }, i) => {
        const rate = nps?.[l.key];
        const text = present
          ? rate === undefined
            ? l.label
            : `${l.label}, ${rate.toFixed(1)} NPS`
          : `Missing: ${l.label}`;
        return (
          <span key={l.key} className="level-part">
            {i > 0 && (
              <span className="level-sep" aria-hidden="true">
                {" | "}
              </span>
            )}
            <Tip text={text}>
              <span
                className={present ? "level" : "level missing"}
                style={present ? { color: levelColor(l.key) } : undefined}
                role="img"
                aria-label={text}
              >
                <span aria-hidden="true">{l.abbr}</span>
              </span>
            </Tip>
          </span>
        );
      })}
    </span>
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
