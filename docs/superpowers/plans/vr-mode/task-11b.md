# Task 11: `VrMode` context, redirects and the `data-ui` attribute (part b)

Continues [task-11a.md](task-11a.md).

- [ ] **Step 3: Implement**

Create `frontend/src/vr/VrMode.tsx`:

```tsx
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
    return () => {
      delete root.dataset.ui;
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
```

Append to `frontend/src/vr/README.md`:

```markdown
3. `VrMode.tsx`: `VrModeProvider` and `useVrMode`: the decided mode, headset status, banner state, `choose`, the `data-ui` attribute and the redirects between desktop and VR paths.
```

- [ ] **Step 4: Run it to see it pass**

Run: `npx --prefix frontend vitest run --root frontend tests/vrmode.test.tsx`
Expected: PASS, 18 passed.

- [ ] **Step 5: Type check**

Run: `npm --prefix frontend run typecheck`
Expected: exit 0.

- [ ] **Step 6: Commit**

Commit: main thread runs `task st:commit -- -m "feat(vr): VrMode context with redirects and data-ui" frontend/src/vr frontend/tests/vrmode.test.tsx`
