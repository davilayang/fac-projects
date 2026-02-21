import { Button, Card } from "@libs/components";
import { GitHubIcon } from "@libs/components/icons";
import "./App.css";

function App() {
  return (
    <main className="page">
      <div className="page__bg" aria-hidden="true" />
      <div className="page__grid" aria-hidden="true" />

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

        <Button icon={<GitHubIcon size="small" />} type="button">
          Sign in with GitHub
        </Button>
      </Card>
    </main>
  );
}

export default App;
