import { useCallback, useMemo, useState } from "react";
import type { BsMap } from "../../api/beatsaver";

export interface Selection {
  items: BsMap[];
  ids: ReadonlySet<string>;
  toggle: (item: BsMap) => void;
  /** Tick every given map, or untick them all when they are all ticked already. */
  toggleAll: (items: BsMap[]) => void;
  clear: () => void;
}

/** Ticked maps; kept as objects so the confirmation can name them after the list changes. */
export function useSelection(): Selection {
  const [chosen, setChosen] = useState<ReadonlyMap<string, BsMap>>(new Map());
  const toggle = useCallback((item: BsMap) => {
    setChosen((prev) => {
      const next = new Map(prev);
      if (!next.delete(item.id)) next.set(item.id, item);
      return next;
    });
  }, []);
  const toggleAll = useCallback((items: BsMap[]) => {
    setChosen((prev) => {
      const next = new Map(prev);
      if (items.length && items.every((i) => next.has(i.id))) {
        for (const i of items) next.delete(i.id);
      } else {
        for (const i of items) next.set(i.id, i);
      }
      return next;
    });
  }, []);
  const clear = useCallback(() => setChosen(new Map()), []);
  const ids = useMemo(() => new Set(chosen.keys()), [chosen]);
  const items = useMemo(() => [...chosen.values()], [chosen]);
  return { items, ids, toggle, toggleAll, clear };
}
