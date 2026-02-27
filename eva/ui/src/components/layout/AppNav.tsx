import { Link } from "react-router";
import { useAuth } from "@eva-providers";
import { ROUTES } from "@eva-router";
import "./AppNav.css";

export function AppNav() {
  const { user, signOut } = useAuth();

  return (
    <nav className="nav">
      <Link to={ROUTES.EVENTS} className="nav__brand">
        <img
          className="nav__logo"
          src="/web-app-manifest-192x192.png"
          alt="EVA"
          width="32"
          height="32"
        />
        <span className="nav__wordmark">EVA</span>
      </Link>

      <div className="nav__user">
        {user?.avatarUrl && (
          <img
            className="nav__avatar"
            src={user.avatarUrl}
            alt={user.name ?? user.login}
            width="32"
            height="32"
          />
        )}
        <span className="nav__name">{user?.name ?? user?.login}</span>
        <button className="nav__logout" type="button" onClick={signOut}>
          Sign out
        </button>
      </div>
    </nav>
  );
}
