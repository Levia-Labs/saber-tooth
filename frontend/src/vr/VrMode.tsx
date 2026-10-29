import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useLocation, useNavigate } from "react-router";
import {
  decideMode,
  desktopPath,
  readDismissed,
  readStored,
  supportsImmersiveVr,
  vrPath,
  writeDismissed,
  writeStored,
  type Mode,
} from "./mode";
import { installScale, refreshScale } from "./scale";
import { NO_VR, useVisible, useVrStatus, type VrStatus } from "./status";

export interface VrModeValue {
  mode: Mode;
  status: VrStatus;
  /** `navigator.xr.isSessionSupported('immersive-vr')`, read once for the later immersive phase. */
  xrSupported: boolean;
  showBanner: boolean;
  choose: (mode: Mode) => void;
  dismissBanner: () => void;
}

installScale();

const NEUTRAL: VrModeValue = {
  mode: "desktop",
  status: NO_VR,
  xrSupported: false,
  showBanner: false,
  choose: () => undefined,
  dismissBanner: () => undefined,
};

const VrModeContext = createContext<VrModeValue>(NEUTRAL);

export const useVrMode = (): VrModeValue => useContext(VrModeContext);

export function VrModeProvider({ children }: { children: ReactNode }) {
  const { pathname, search } = useLocation();
  const navigate = useNavigate();
  const [stored, setStored] = useState<Mode | null>(() => readStored());
  const [dismissed, setDismissed] = useState<boolean>(() => readDismissed());
  const [xrSupported, setXrSupported] = useState(false);
  const status = useVrStatus(useVisible()).data ?? NO_VR;
  const decision = decideMode({ pathname, search, stored, userAgent: navigator.userAgent });
  const mode = decision.mode;

  useEffect(() => {
    let live = true;
    void supportsImmersiveVr().then((ok) => live && setXrSupported(ok));
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (mode === "vr") root.dataset.ui = "vr";
    else delete root.dataset.ui;
    refreshScale();
    return () => {
      delete root.dataset.ui;
      refreshScale();
    };
  }, [mode]);

  useEffect(() => {
    const target = mode === "vr" ? vrPath(pathname) : desktopPath(pathname);
    if (target !== pathname) void navigate({ pathname: target, search }, { replace: true });
  }, [mode, pathname, search, navigate]);

  const choose = useCallback(
    (next: Mode) => {
      writeStored(next);
      setStored(next);
      const params = new URLSearchParams(search);
      params.delete("mode");
      const target = next === "vr" ? vrPath(pathname) : desktopPath(pathname);
      void navigate({ pathname: target, search: params.toString() });
    },
    [pathname, search, navigate],
  );

  const dismissBanner = useCallback(() => {
    writeDismissed();
    setDismissed(true);
  }, []);

  const showBanner = decision.source === "default" && status.runtime !== null && !dismissed;
  const value = useMemo(
    () => ({ mode, status, xrSupported, showBanner, choose, dismissBanner }),
    [mode, status, xrSupported, showBanner, choose, dismissBanner],
  );
  return <VrModeContext.Provider value={value}>{children}</VrModeContext.Provider>;
}
