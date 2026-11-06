import { useRef, type KeyboardEvent, type ReactNode } from "react";
import { MAP_TABS, tabForKey, type MapTab } from "../lib/mapTabs";
import { Icon } from "./icons";

export const tabId = (k: MapTab) => `map-tab-${k}`;
export const panelId = (k: MapTab) => `map-panel-${k}`;

interface Props {
  available: readonly MapTab[];
  active: MapTab;
  onSelect: (tab: MapTab) => void;
  /** Shows the copy-folder-path button at the right end of the row when given. */
  onCopyPath?: () => void;
}

/** WAI-ARIA tablist (automatic activation): arrows, Home and End move and select. */
export function MapTabList({ available, active, onSelect, onCopyPath }: Props) {
  const list = useRef<HTMLDivElement>(null);
  const onKey = (e: KeyboardEvent) => {
    const next = tabForKey(e.key, active, available);
    if (next === null) return;
    e.preventDefault();
    onSelect(next);
    list.current?.querySelector<HTMLElement>(`#${tabId(next)}`)?.focus();
  };
  return (
    <div className="map-tabs-row">
      <div ref={list} className="mode-switch map-tabs" role="tablist" aria-label="Map">
        {MAP_TABS.filter((t) => available.includes(t.key)).map((t) => (
          <button
            key={t.key}
            id={tabId(t.key)}
            type="button"
            role="tab"
            className={t.key === "delete" ? "pill map-tab map-tab-danger" : "pill map-tab"}
            aria-selected={t.key === active}
            aria-controls={panelId(t.key)}
            tabIndex={t.key === active ? 0 : -1}
            onClick={() => onSelect(t.key)}
            onKeyDown={onKey}
          >
            <Icon name={t.icon} />
            {t.label}
          </button>
        ))}
      </div>
      {onCopyPath && (
        <button
          type="button"
          className="btn map-copy-path"
          aria-label="Copy folder path to clipboard"
          title="Copy folder path to clipboard"
          onClick={onCopyPath}
        >
          <Icon name="copy" />
        </button>
      )}
    </div>
  );
}

/** A tab's panel; `hidden` keeps its state while another tab shows. */
export function MapTabPanel({
  tab,
  active,
  children,
}: {
  tab: MapTab;
  active: boolean;
  children: ReactNode;
}) {
  return (
    <div
      id={panelId(tab)}
      role="tabpanel"
      aria-labelledby={tabId(tab)}
      hidden={!active}
      className="map-tabpanel"
    >
      {children}
    </div>
  );
}
