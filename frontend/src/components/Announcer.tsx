import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

const AnnounceContext = createContext<(text: string) => void>(() => undefined);

/** Hook returning a function that sets the polite status line shown under the header. */
export function useAnnounce(): (text: string) => void {
  return useContext(AnnounceContext);
}

export function AnnouncerProvider({ children }: { children: ReactNode }) {
  const [text, setText] = useState("");
  const announce = useCallback((next: string) => setText(next), []);
  const value = useMemo(() => announce, [announce]);
  return (
    <AnnounceContext.Provider value={value}>
      <p className="status-line" role="status" aria-live="polite">
        {text}
      </p>
      {children}
    </AnnounceContext.Provider>
  );
}
