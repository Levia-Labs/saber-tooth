import { useState } from "react";
import type { MapItem } from "../api/types";
import { formatBpm, formatDuration } from "../lib/format";
import { levelsFor, textColor } from "../lib/levels";
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

export function LevelChips({ names, className }: { names: readonly string[]; className?: string }) {
  const levels = levelsFor(names);
  if (!levels.length) return null;
  return (
    <ul className={`levels ${className ?? ""}`.trim()} aria-label="Difficulties">
      {levels.map((l) => (
        <li key={l.key} className="level" style={{ background: l.bg, color: textColor(l.bg) }}>
          {l.label}
        </li>
      ))}
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
      {formatDuration(item.duration_s)} <span className="dot">&middot;</span> {formatBpm(item.bpm)}
    </span>
  );
}
