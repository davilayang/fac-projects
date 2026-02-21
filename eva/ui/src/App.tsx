import { Button, Card } from "@libs/components";
import { GitHubIcon } from "@libs/components/icons";
import "./App.css";

function App() {
  return (
    <main className="page">
      <div className="page__bg" aria-hidden="true" />

      <Card>
        <h1 className="page-login__title">EVA</h1>
        <p className="page-login__subtitle">Event Voice Agent</p>
        <p className="page-login__hint">Sign in to continue</p>

        <Button icon={<GitHubIcon size="small" />} type="button">
          Sign in with GitHub
        </Button>
      </Card>
    </main>
  );
}

export default App;
