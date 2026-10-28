# Task 17: Shell wiring: provider, banner and the masthead switch (part b)

Continues [task-17a.md](task-17a.md).

- [ ] **Step 3: Implement**

Create `frontend/src/vr/VrBanner.tsx`:

```tsx
import { Alert } from "../components/Alert";
import { useVrMode } from "./VrMode";

/** Suggests the VR layout when a headset runtime is active and nothing chose the mode. */
export function VrBanner() {
  const { showBanner, status, choose, dismissBanner } = useVrMode();
  if (!showBanner) return null;
  return (
    <Alert
      className="vr-suggest"
      variant="info"
      title="Headset in use: switch to VR layout?"
      message={`${status.runtime} is running. The VR layout has large buttons and text for the headset.`}
      actions={
        <button type="button" className="btn accent" onClick={() => choose("vr")}>
          Switch to VR
        </button>
      }
      onDismiss={dismissBanner}
    />
  );
}
```

Create `frontend/src/vr/ModeSwitch.tsx`:

```tsx
import { useVrMode } from "./VrMode";

const CHOICES = [
  { mode: "vr", label: "VR" },
  { mode: "desktop", label: "Desktop" },
] as const;

/** VR / Desktop toggle for the masthead: two buttons, not links, so the header keeps no nav. */
export function ModeSwitch() {
  const { mode, choose } = useVrMode();
  return (
    <div className="mode-pick" role="group" aria-label="Layout">
      {CHOICES.map((c) => (
        <button
          key={c.mode}
          type="button"
          className="mode-pick-btn"
          aria-pressed={mode === c.mode}
          onClick={() => choose(c.mode)}
        >
          {c.label}
        </button>
      ))}
    </div>
  );
}
```

Create `frontend/src/styles/vrmode.css` (not scoped: the switch and the banner show in both layouts):

```css
.masthead-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.mode-pick {
  display: inline-flex;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}
.mode-pick-btn {
  padding: 0.3rem 0.8rem;
  border: 0;
  background: transparent;
  color: var(--muted);
  font: inherit;
  cursor: pointer;
}
.mode-pick-btn[aria-pressed="true"] {
  background: var(--blue);
  color: #08051a;
}
.vr-suggest {
  width: calc(100% - 2.5rem);
  max-width: 1480px;
  margin: 0.5rem auto;
}
```

In `frontend/src/main.tsx`, add before `import "./styles/vr.css";`:

```ts
import "./styles/vrmode.css";
```

In `frontend/src/App.tsx`, add the imports:

```tsx
import { ModeSwitch } from "./vr/ModeSwitch";
import { VrBanner } from "./vr/VrBanner";
import { VrModeProvider } from "./vr/VrMode";
```

and replace the `Shell` return so it reads:

```tsx
return (
  <VrModeProvider>
    <div className="app">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <header className="masthead">
        <Link className="brand" to="/" aria-label="saber-tooth, library">
          <Logo />
          <span className="wordmark">
            <span className="red">saber</span>
            <span className="dash">-</span>
            <span className="blue">tooth</span>
          </span>
        </Link>
        <div className="masthead-actions">
          <ModeSwitch />
          <Tip text="What saber-tooth is">
            <Link
              className="about-link"
              to="/about"
              aria-label="About"
              aria-current={pathname === "/about" ? "page" : undefined}
            >
              <Icon name="info" />
              <span className="about-label">About</span>
            </Link>
          </Tip>
        </div>
      </header>
      <VrBanner />
      <AnnouncerProvider>
        <main id="main" tabIndex={-1}>
          <PageBoundary resetKey={pathname}>
            <Suspense fallback={<PageSkeleton />}>
              <Outlet />
            </Suspense>
          </PageBoundary>
        </main>
      </AnnouncerProvider>
    </div>
  </VrModeProvider>
);
```

Append to `frontend/src/vr/README.md`:

```markdown
8. `VrBanner.tsx`, `ModeSwitch.tsx`: the suggestion banner and the masthead VR / Desktop switch, mounted by `Shell` inside `VrModeProvider`.
```

- [ ] **Step 4: Run it to see it pass**

Run: `npx --prefix frontend vitest run --root frontend tests/vrshell.test.tsx tests/sectionTabs.test.tsx tests/about.test.tsx`
Expected: PASS, 10 passed in `vrshell.test.tsx`.

- [ ] **Step 5: Run the whole frontend suite once**

`Shell` is shared by every `renderApp` test, so run it all: `npm --prefix frontend run test`
Expected: PASS. A failure that names `/api/vr/status` means a handler that rejects unknown paths; fix that handler, never the production code.

- [ ] **Step 6: Type check, lint and format check**

Run: `task st:web:check`
Expected: exit 0.

- [ ] **Step 7: Commit**

Commit: main thread runs `task st:commit -- -m "feat(vr): mount VrMode in the shell with a banner and a masthead switch" frontend/src/App.tsx frontend/src/main.tsx frontend/src/vr frontend/src/styles/vrmode.css frontend/tests/vrshell.test.tsx`
