import { useCallback, useMemo, useState, type CSSProperties, type RefObject } from "react";
import {
  BREAKPOINTS,
  clampWidth,
  columnVars,
  defaultWidths,
  gridTemplate,
  LIBRARY_COLUMNS,
  loadWidths,
  saveWidths,
  tableMinWidth,
  type Breakpoint,
  type ColumnSet,
  type ColumnKey,
  type Widths,
} from "./columns";
import { scaledPx, unscaledPx, useUiScale } from "../vr/scale";
import { COMPACT_QUERY, MID_QUERY } from "./breakpoint";
import { useMediaQuery } from "./hooks";

export interface ColumnsApi {
  bp: Breakpoint;
  widths: Widths;
  /** Move a column during a drag: writes the CSS custom properties only, no React render. */
  preview: (key: ColumnKey, px: number) => void;
  /** Settle a column width: state and storage. */
  commit: (key: ColumnKey, px: number) => void;
  reset: (key: ColumnKey) => void;
  resetAll: () => void;
}

type All = Record<Breakpoint, Widths>;

export function useBreakpoint(): Breakpoint {
  // Outside VR both tier queries stand for the mobile view (see lib/breakpoint.ts), so the table
  // is compact there; in VR they follow the effective width.
  const mid = useMediaQuery(MID_QUERY);
  const compact = useMediaQuery(COMPACT_QUERY);
  return compact ? "compact" : mid ? "mid" : "wide";
}

/** Column widths for the library list; `style` goes on the list container that holds the rows. */
export function useColumns(
  table: RefObject<HTMLElement | null>,
  set: ColumnSet = LIBRARY_COLUMNS,
): {
  api: ColumnsApi;
  style: CSSProperties;
} {
  const bp = useBreakpoint();
  const scale = useUiScale();
  const [all, setAll] = useState<All>(() => ({
    wide: loadWidths("wide", undefined, set),
    mid: loadWidths("mid", undefined, set),
    compact: loadWidths("compact", undefined, set),
  }));

  const preview = useCallback(
    (key: ColumnKey, px: number) => {
      const next = { ...all[bp], [key]: clampWidth(key, unscaledPx(px, scale)) };
      const el = table.current;
      if (!el) return;
      el.style.setProperty(`--cols-${bp}`, gridTemplate(bp, next, set, scale));
      el.style.setProperty(`--min-${bp}`, `${tableMinWidth(bp, next, set, scale)}px`);
    },
    [all, bp, table, set, scale],
  );

  const settle = useCallback(
    (next: Widths) => {
      saveWidths(bp, next, undefined, set);
      setAll((prev) => ({ ...prev, [bp]: next }));
    },
    [bp, set],
  );
  const commit = useCallback(
    (key: ColumnKey, px: number) =>
      settle({ ...all[bp], [key]: clampWidth(key, unscaledPx(px, scale)) }),
    [all, bp, settle, scale],
  );
  const reset = useCallback(
    (key: ColumnKey) => settle({ ...all[bp], [key]: defaultWidths(bp, set)[key] }),
    [all, bp, settle, set],
  );
  const resetAll = useCallback(() => {
    for (const each of BREAKPOINTS) saveWidths(each, defaultWidths(each, set), undefined, set);
    setAll({
      wide: defaultWidths("wide", set),
      mid: defaultWidths("mid", set),
      compact: defaultWidths("compact", set),
    });
  }, [set]);

  const style = useMemo(() => columnVars(all, set, scale) as CSSProperties, [all, set, scale]);
  const shown = useMemo(() => scaleWidths(all[bp], scale), [all, bp, scale]);
  const api = useMemo(
    () => ({ bp, widths: shown, preview, commit, reset, resetAll }),
    [bp, shown, preview, commit, reset, resetAll],
  );
  return { api, style };
}

/** The widths as rendered at a VR scale, which is what a drag handle measures; identity at 1. */
function scaleWidths(widths: Widths, scale: number): Widths {
  if (scale === 1) return widths;
  const out: Widths = {};
  for (const [key, value] of Object.entries(widths) as [ColumnKey, number][]) {
    out[key] = scaledPx(value, scale);
  }
  return out;
}
