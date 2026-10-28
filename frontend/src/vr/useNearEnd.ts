import { useEffect, useRef, type RefObject } from "react";

/** Calls `onNear` when the ref'd end sentinel comes within 600 px of view; off when `enabled` is false. */
export function useNearEnd(onNear: () => void, enabled: boolean): RefObject<HTMLDivElement | null> {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = ref.current;
    if (!enabled || !node || typeof IntersectionObserver === "undefined") return undefined;
    const seen = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) onNear();
      },
      { rootMargin: "600px" },
    );
    seen.observe(node);
    return () => seen.disconnect();
  }, [enabled, onNear]);
  return ref;
}
