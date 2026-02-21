import { Navigate } from "react-router";
import { Button, Card } from "@eva-elements";
import { GitHubIcon } from "@eva-icons";
import { useAuth } from "../../auth/useAuth";
import { ROUTES } from "../../router";
import "./Home.css";

export function Home() {
  const { signIn, status } = useAuth();

  if (status === "authenticated") return <Navigate to={ROUTES.EVENTS} replace />;

  return (
    <main className="page-home">
      <Card>
        <div className="page-login__logo-wrap" aria-hidden="true">
          <img
            className="page-login__logo"
            src="/web-app-manifest-192x192.png"
            alt=""
            width="96"
            height="96"
          />
          <div className="page-login__logo-glow" aria-hidden="true" />
        </div>

        <h1 className="page-login__title">EVA</h1>
        <p className="page-login__subtitle">Event Voice Agent</p>

        <hr className="page-login__divider" />

        <p className="page-login__hint">Sign in to continue</p>

        <Button icon={<GitHubIcon size="small" />} type="button" onClick={signIn}>
          Sign in with GitHub
        </Button>
      </Card>
    </main>
  );
}
