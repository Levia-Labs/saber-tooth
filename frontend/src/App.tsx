import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Suspense, useEffect, useRef, useState } from "react";
import { createBrowserRouter, Link, Outlet, useLocation, type RouteObject } from "react-router";
import { RouterProvider } from "react-router/dom";
import { AnnouncerProvider } from "./components/Announcer";
import { JobToasts } from "./components/JobToasts";
import { Logo } from "./components/Logo";
import { TipProvider } from "./components/Tip";
import { PageBoundary } from "./components/ErrorPanel";
import { PageSkeleton } from "./components/Skeletons";
import { RouteError } from "./components/RouteError";
import { lazyRoute } from "./lib/lazyRoute";
import { ModeSwitch } from "./vr/ModeSwitch";
import { VrBanner } from "./vr/VrBanner";
import { VrModeProvider } from "./vr/VrMode";
import { LibraryPage } from "./pages/LibraryPage";
import { NotFoundPage } from "./pages/NotFoundPage";

const MapPage = lazyRoute(() => import("./pages/MapPage").then((m) => ({ default: m.MapPage })));
const BeatSaverPage = lazyRoute(() =>
  import("./pages/BeatSaverPage").then((m) => ({ default: m.BeatSaverPage })),
);
const BeatSaverPlaylistsPage = lazyRoute(() =>
  import("./pages/BeatSaverPlaylistsPage").then((m) => ({ default: m.BeatSaverPlaylistsPage })),
);
const JobsPage = lazyRoute(() => import("./pages/JobsPage").then((m) => ({ default: m.JobsPage })));
const PlaylistsPage = lazyRoute(() =>
  import("./pages/PlaylistsPage").then((m) => ({ default: m.PlaylistsPage })),
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

/** The page frame; the VR mode context wraps it so the mode and `data-ui` apply app-wide. */
export function Shell() {
  return (
    <VrModeProvider>
      <ShellFrame />
    </VrModeProvider>
  );
}

function ShellFrame() {
  useFocusHeading();
  const { pathname } = useLocation();
  return (
    <div className="app">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <header className="masthead">
        <div className="masthead-inner">
          <Link className="brand" to="/" aria-label="Saber Tooth, library">
            <Logo />
            <span className="wordmark">
              <span className="red">Saber</span>
              <span className="space">{" "}</span>
              <span className="blue">Tooth</span>
            </span>
          </Link>
          <div className="masthead-actions">
            <ModeSwitch />
          </div>
        </div>
      </header>
      <AnnouncerProvider>
        <VrBanner />
        <JobToasts />
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
      { path: "/jobs", element: <JobsPage />, errorElement: <RouteError /> },
      { path: "/playlists", element: <PlaylistsPage />, errorElement: <RouteError /> },
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
      // The VR routes mount the desktop pages; the VR shell styles scale them.
      { path: "/vr", element: <LibraryPage />, errorElement: <RouteError /> },
      { path: "/vr/maps/:id", element: <MapPage />, errorElement: <RouteError /> },
      { path: "/vr/beatsaver", element: <BeatSaverPage />, errorElement: <RouteError /> },
      { path: "/vr/jobs", element: <JobsPage />, errorElement: <RouteError /> },
      { path: "/vr/playlists", element: <PlaylistsPage />, errorElement: <RouteError /> },
      { path: "*", element: <NotFoundPage />, errorElement: <RouteError /> },
    ],
  },
];

export function createAppRouter() {
  return createBrowserRouter(routes);
}

type AppRouter = ReturnType<typeof createBrowserRouter>;

/**
 * One router and one query client for the life of the app. Built in the render body they were
 * rebuilt whenever React re-ran `App` (an error retry, a Suspense replay): a second browser router
 * then registered its own popstate listener and started loading beside the first.
 */
export function useAppInstances(router?: AppRouter) {
  const [client] = useState(makeQueryClient);
  const [own] = useState(() => (router ? null : createAppRouter()));
  return { client, router: router ?? own };
}

export function App({ router }: { router?: AppRouter }) {
  const instances = useAppInstances(router);
  if (!instances.router) return null;
  return (
    <QueryClientProvider client={instances.client}>
      <TipProvider delayDuration={300}>
        <RouterProvider router={instances.router} />
      </TipProvider>
    </QueryClientProvider>
  );
}
