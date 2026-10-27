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
  const mid = useMediaQuery("(max-width: 1279px)");
  const compact = useMediaQuery("(max-width: 1099px)");
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
  const [all, setAll] = useState<All>(() => ({
    wide: loadWidths("wide", undefined, set),
    mid: loadWidths("mid", undefined, set),
    compact: loadWidths("compact", undefined, set),
  }));

  const preview = useCallback(
    (key: ColumnKey, px: number) => {
      const next = { ...all[bp], [key]: clampWidth(key, px) };
      const el = table.current;
      if (!el) return;
      el.style.setProperty(`--cols-${bp}`, gridTemplate(bp, next, set));
      el.style.setProperty(`--min-${bp}`, `${tableMinWidth(bp, next, set)}px`);
    },
    [all, bp, table, set],
  );

  const settle = useCallback(
    (next: Widths) => {
      saveWidths(bp, next, undefined, set);
      setAll((prev) => ({ ...prev, [bp]: next }));
    },
    [bp, set],
  );
  const commit = useCallback(
    (key: ColumnKey, px: number) => settle({ ...all[bp], [key]: clampWidth(key, px) }),
    [all, bp, settle],
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

  const style = useMemo(() => columnVars(all, set) as CSSProperties, [all, set]);
  const api = useMemo(
    () => ({ bp, widths: all[bp], preview, commit, reset, resetAll }),
    [bp, all, preview, commit, reset, resetAll],
  );
  return { api, style };
}
