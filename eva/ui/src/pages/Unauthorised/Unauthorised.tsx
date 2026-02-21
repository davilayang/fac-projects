import { Link } from "react-router";
import { Card } from "@eva-elements";
import { ROUTES } from "../../router";
import "./Unauthorised.css";

export function Unauthorised() {
  return (
    <main className="page-home">
      <Card>
        <div className="page-unauth__icon" aria-hidden="true">
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

        <h1 className="page-unauth__title">Access denied</h1>
        <p className="page-unauth__body">
          Your GitHub account is not authorised to use this application. Contact
          an administrator to request access.
        </p>

        <hr className="page-login__divider" />

        <Link to={ROUTES.HOME} className="page-unauth__back">
          Back to sign in
        </Link>
      </Card>
    </main>
  );
}
