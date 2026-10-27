import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Suspense, useEffect, useRef } from "react";
import { createBrowserRouter, Link, Outlet, useLocation, type RouteObject } from "react-router";
import { RouterProvider } from "react-router/dom";
import { AnnouncerProvider } from "./components/Announcer";
import { Logo } from "./components/Logo";
import { TipProvider } from "./components/Tip";
import { PageBoundary } from "./components/ErrorPanel";
import { RouteError } from "./components/RouteError";
import { lazyRoute } from "./lib/lazyRoute";
import { LibraryPage } from "./pages/LibraryPage";
import { NotFoundPage } from "./pages/NotFoundPage";

const MapPage = lazyRoute(() => import("./pages/MapPage").then((m) => ({ default: m.MapPage })));
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
            <span className="red">saber</span>-<span className="blue">tooth</span>
          </span>
        </Link>
      </header>
      <AnnouncerProvider>
        <main id="main" tabIndex={-1}>
          <PageBoundary resetKey={pathname}>
            <Suspense fallback={<p className="muted">Loading</p>}>
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
      { path: "/new", element: <NewPage />, errorElement: <RouteError /> },
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
