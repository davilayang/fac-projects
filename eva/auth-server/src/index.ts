import "dotenv/config";
import express from "express";
import cookieParser from "cookie-parser";
import cors from "cors";
import passport from "./lib/passport.js";
import routes from "./routes/index.js";

const REQUIRED_ENV = [
  "AUTH_GITHUB_ID",
  "AUTH_GITHUB_SECRET",
  "AUTH_CALLBACK_URL",
  "JWT_SECRET",
  "LIVEKIT_API_KEY",
  "LIVEKIT_API_SECRET",
  "LIVEKIT_URL",
];
const missing = REQUIRED_ENV.filter((k) => !process.env[k]);
if (missing.length > 0) {
  console.error(
    `Missing required environment variables: ${missing.join(", ")}`,
  );
  process.exit(1);
}

const app = express();
const PORT = Number(process.env.PORT ?? 4000);
const UI_ORIGIN = process.env.UI_ORIGIN ?? "http://localhost:5173";

app.set("trust proxy", 1);

app.use(
  cors({
    origin: UI_ORIGIN,
    credentials: true,
  }),
);

app.use(express.json());
app.use(cookieParser());
app.use(passport.initialize());
app.use(routes);

app.get("/health", (_req, res) => res.sendStatus(200));

app.listen(PORT, () => {
  console.log(`Auth server running on http://localhost:${PORT}`);
});
