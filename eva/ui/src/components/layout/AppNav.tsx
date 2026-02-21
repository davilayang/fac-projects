import { Link } from "react-router";
import "./AppNav.css";

export function AppNav() {
  return (
    <nav className="nav">
      <Link to="/" className="nav__brand">
        <img
          className="nav__logo"
          src="/web-app-manifest-192x192.png"
          alt="EVA"
          width="32"
          height="32"
        />
        <span className="nav__wordmark">EVA</span>
      </Link>
    </nav>
  );
}
