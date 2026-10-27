import { useEffect } from "react";
import { isRouteErrorResponse, useLocation, useNavigate, useRouteError } from "react-router";
import { NotFoundPage } from "../pages/NotFoundPage";
import { ErrorPanel } from "./ErrorPanel";

/** errorElement for every route: 404 gets the Not found page, anything else the error panel. */
export function RouteError() {
  const error = useRouteError();
  const navigate = useNavigate();
  const { pathname, search } = useLocation();
  useEffect(() => {
    console.error("Route failed:", error);
  }, [error]);
  if (isRouteErrorResponse(error) && error.status === 404) return <NotFoundPage />;
  // A fresh navigation to the same address clears the route error and renders the page again.
  return (
    <ErrorPanel error={error} onRetry={() => void navigate(pathname + search, { replace: true })} />
  );
}
