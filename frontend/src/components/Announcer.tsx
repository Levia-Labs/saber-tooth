import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import {
  addBanner,
  dismissBanner,
  expireBanners,
  nextExpiry,
  type AnnounceInput,
  type Banner,
} from "../lib/announcements";
import { Link } from "react-router";
import { Alert } from "./Alert";

type Announce = (input: AnnounceInput) => void;

const AnnounceContext = createContext<Announce>(() => undefined);

/** Hook returning a function that shows or updates a toast at the bottom of the window. */
export function useAnnounce(): Announce {
  return useContext(AnnounceContext);
}

export function AnnouncerProvider({ children }: { children: ReactNode }) {
  const [banners, setBanners] = useState<Banner[]>([]);
  const announce = useCallback<Announce>(
    (input) => setBanners((list) => addBanner(list, input, Date.now())),
    [],
  );

  useEffect(() => {
    const at = nextExpiry(banners);
    if (at === null) return undefined;
    const timer = setTimeout(
      () => setBanners((list) => expireBanners(list, Date.now())),
      Math.max(0, at - Date.now()),
    );
    return () => clearTimeout(timer);
  }, [banners]);

  return (
    <AnnounceContext.Provider value={announce}>
      {children}
      <div className="toast-stack">
        {banners.map((b) => (
          <Alert
            key={b.key}
            className="toast"
            variant={b.variant === "progress" ? "info" : b.variant}
            progress={b.variant === "progress"}
            title={b.title}
            message={b.message}
            actions={b.link && <Link to={b.link.to}>{b.link.label}</Link>}
            onDismiss={
              b.variant === "progress"
                ? undefined
                : () => setBanners((list) => dismissBanner(list, b.key))
            }
          />
        ))}
      </div>
    </AnnounceContext.Provider>
  );
}
