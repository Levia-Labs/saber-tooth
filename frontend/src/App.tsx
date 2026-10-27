import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Suspense, useEffect, useRef } from "react";
import { createBrowserRouter, Link, Outlet, useLocation, type RouteObject } from "react-router";
import { RouterProvider } from "react-router/dom";
import { AnnouncerProvider } from "./components/Announcer";
import { Icon } from "./components/icons";
import { Logo } from "./components/Logo";
import { Tip, TipProvider } from "./components/Tip";
import { PageBoundary } from "./components/ErrorPanel";
import { PageSkeleton } from "./components/Skeletons";
import { RouteError } from "./components/RouteError";
import { lazyRoute } from "./lib/lazyRoute";
import { LibraryPage } from "./pages/LibraryPage";
import { NotFoundPage } from "./pages/NotFoundPage";

const MapPage = lazyRoute(() => import("./pages/MapPage").then((m) => ({ default: m.MapPage })));
const BeatSaverPage = lazyRoute(() =>
  import("./pages/BeatSaverPage").then((m) => ({ default: m.BeatSaverPage })),
);
const BeatSaverPlaylistsPage = lazyRoute(() =>
  import("./pages/BeatSaverPlaylistsPage").then((m) => ({ default: m.BeatSaverPlaylistsPage })),
);
const AboutPage = lazyRoute(() =>
  import("./pages/AboutPage").then((m) => ({ default: m.AboutPage })),
);
const NewPage = lazyRoute(() => import("./pages/NewPage").then((m) => ({ default: m.NewPage })));

export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { staleTime: 15_000, refetchOnWindowFocus: false } },
  });
}

/** Move focus to the page heading after client-side navigation (not on first load). */
function useFocusHeading() {
  const { pathname } = useLocation();
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    document.querySelector<HTMLElement>("[data-page-heading]")?.focus();
  }, [pathname]);
}

/** Library | BeatSaver switch: two real links, the active one follows the route. */
function ModeSwitch() {
  const { pathname } = useLocation();
  const onBeatSaver = pathname === "/beatsaver" || pathname.startsWith("/beatsaver/");
  const items = [
    { to: "/", label: "Library", active: !onBeatSaver, tip: "Maps in your CustomLevels folder." },
    { to: "/beatsaver", label: "BeatSaver", active: onBeatSaver, tip: "Search and download maps." },
  ];
  return (
    <nav className="mode-switch" aria-label="Section">
      {items.map((i) => (
        <Tip key={i.to} text={i.tip}>
          <Link to={i.to} aria-current={i.active ? "page" : undefined}>
            {i.label}
          </Link>
        </Tip>
      ))}
    </nav>
  );
}

export function Shell() {
  useFocusHeading();
  const { pathname } = useLocation();
  return (
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
      </header>
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
  );
}

export const routes: RouteObject[] = [
  {
    element: <Shell />,
    errorElement: <RouteError />,
    children: [
      { path: "/", element: <LibraryPage />, errorElement: <RouteError /> },
      { path: "/maps/:id", element: <MapPage />, errorElement: <RouteError /> },
      { path: "/about", element: <AboutPage />, errorElement: <RouteError /> },
      { path: "/new", element: <NewPage />, errorElement: <RouteError /> },
      { path: "/beatsaver", element: <BeatSaverPage />, errorElement: <RouteError /> },
      {
        path: "/beatsaver/playlists",
        element: <BeatSaverPlaylistsPage />,
        errorElement: <RouteError />,
      },
      {
        path: "/beatsaver/playlists/:id",
        element: <BeatSaverPlaylistsPage />,
        errorElement: <RouteError />,
      },
      { path: "*", element: <NotFoundPage />, errorElement: <RouteError /> },
    ],
  },
];

export function createAppRouter() {
  return createBrowserRouter(routes);
}

export function App({
  router = createAppRouter(),
}: {
  router?: ReturnType<typeof createBrowserRouter>;
}) {
  return (
    <QueryClientProvider client={makeQueryClient()}>
      <TipProvider delayDuration={300}>
        <RouterProvider router={router} />
      </TipProvider>
    </QueryClientProvider>
  );
}
