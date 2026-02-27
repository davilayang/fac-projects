import { Link } from "react-router";
import { Card } from "@eva-elements";
import { ROUTES } from "../../router";
import "./NotFound.css";

export function NotFound() {
  return (
    <main className="page-home">
      <Card>
        <div className="page-notfound__icon" aria-hidden="true">
          <svg
            width="40"
            height="40"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>

        <p className="page-notfound__code">404</p>

        <h1 className="page-notfound__title">Page not found</h1>
        <p className="page-notfound__body">
          The page you're looking for doesn't exist or has been moved.
        </p>

        <hr className="page-notfound__divider" />

        <Link to={ROUTES.EVENTS} className="page-notfound__back">
          Back to events
        </Link>
      </Card>
    </main>
  );
}
