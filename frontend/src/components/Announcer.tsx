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
const WithdrawContext = createContext<(key: string) => void>(() => undefined);

/** Hook returning a function that removes the toast with the given key, if it is showing. */
export function useWithdraw(): (key: string) => void {
  return useContext(WithdrawContext);
}

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

  const withdraw = useCallback((key: string) => setBanners((list) => dismissBanner(list, key)), []);

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
      <WithdrawContext.Provider value={withdraw}>
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
              {...(b.details ? { details: b.details } : {})}
              actions={
                (b.link || b.actions) && (
                  <>
                    {b.link && <Link to={b.link.to}>{b.link.label}</Link>}
                    {b.actions?.map((a) => (
                      <button
                        key={a.label}
                        type="button"
                        className="btn"
                        onClick={() => {
                          // Dismiss first so a handler that re-announces this key keeps its toast.
                          setBanners((list) => dismissBanner(list, b.key));
                          a.onClick();
                        }}
                      >
                        {a.label}
                      </button>
                    ))}
                  </>
                )
              }
              onDismiss={
                b.variant === "progress"
                  ? undefined
                  : () => {
                      b.onDismiss?.();
                      withdraw(b.key);
                    }
              }
            />
          ))}
        </div>
      </WithdrawContext.Provider>
    </AnnounceContext.Provider>
  );
}
