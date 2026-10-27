import { Link } from "react-router";
import { Icon } from "../components/icons";
import { useDocumentTitle } from "../lib/hooks";
import { libraryHref } from "../lib/hooks";

export function NotFoundPage() {
  useDocumentTitle("Page not found");
  return (
    <section className="page">
      <Link className="back" to={libraryHref()}>
        <Icon name="back" />
        Library
      </Link>
      <h1 tabIndex={-1} data-page-heading>
        Page not found
      </h1>
      <p className="muted">There is nothing at this address.</p>
    </section>
  );
}
