import "dotenv/config";
import express from "express";
import session from "express-session";
import FileStore from "session-file-store";
import cors from "cors";
import passport from "./passport.js";
import routes from "./routes.js";

const SessionFileStore = FileStore(session);

const REQUIRED_ENV = ["AUTH_GITHUB_ID", "AUTH_GITHUB_SECRET", "AUTH_CALLBACK_URL", "SESSION_SECRET"];
const missing = REQUIRED_ENV.filter((k) => !process.env[k]);
if (missing.length > 0) {
  console.error(`Missing required environment variables: ${missing.join(", ")}`);
  process.exit(1);
}

const app = express();
const PORT = Number(process.env.PORT ?? 4000);
const UI_ORIGIN = process.env.UI_ORIGIN ?? "http://localhost:5173";

app.set("trust proxy", 1);

app.use(
  cors({
    origin: UI_ORIGIN,
    credentials: true, // allow the session cookie to be sent cross-origin in dev
  })
);

app.use(
  session({
    store: new SessionFileStore({ retries: 1 }),
    secret: process.env.SESSION_SECRET!,
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,                              // JS cannot read the cookie
      secure: process.env.NODE_ENV === "production",
      sameSite: process.env.NODE_ENV === "production" ? "strict" : "lax",
      maxAge: 7 * 24 * 60 * 60 * 1000,           // 7 days
    },
  })
);

app.use(passport.initialize());
app.use(passport.session());
app.use(routes);

app.listen(PORT, () => {
  console.log(`Auth server running on http://localhost:${PORT}`);
});
