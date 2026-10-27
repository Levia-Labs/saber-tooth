import { Link } from "react-router";
import { Icon } from "../components/icons";
import { libraryHref, useDocumentTitle } from "../lib/hooks";

interface Props {
  title?: string;
  detail?: string;
}

export function NotFoundPage({
  title = "Page not found",
  detail = "There is nothing at this address.",
}: Props) {
  useDocumentTitle(title);
  return (
    <section className="page">
      <Link className="back" to={libraryHref()}>
        <Icon name="back" />
        Library
      </Link>
      <h1 tabIndex={-1} data-page-heading>
        {title}
      </h1>
      <p className="muted">{detail}</p>
    </section>
  );
}
