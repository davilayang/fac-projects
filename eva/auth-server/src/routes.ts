import { Router, type Request, type Response } from "express";
import jwt from "jsonwebtoken";
import passport from "./passport.js";
import type { GitHubUser } from "./passport.js";

const router = Router();

const COOKIE_NAME = "eva_auth";
const COOKIE_MAX_AGE = 7 * 24 * 60 * 60 * 1000; // 7 days in ms
const JWT_MAX_AGE = "7d";

function jwtSecret(): string {
  return process.env.JWT_SECRET!;
}

function setAuthCookie(res: Response, user: GitHubUser): void {
  const token = jwt.sign(
    {
      id: user.id,
      login: user.login,
      name: user.name,
      email: user.email,
      avatarUrl: user.avatarUrl,
    },
    jwtSecret(),
    { expiresIn: JWT_MAX_AGE },
  );

  res.cookie(COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: process.env.NODE_ENV === "production" ? "strict" : "lax",
    maxAge: COOKIE_MAX_AGE,
  });
}

// Kick off the GitHub OAuth flow
router.get("/auth/github/login", passport.authenticate("github"));

// GitHub redirects here after the user approves
router.get(
  "/auth/github/callback",
  passport.authenticate("github", {
    session: false,
    failureRedirect: `${process.env.UI_ORIGIN}/unauthorised`,
  }),
  (req: Request, res: Response) => {
    setAuthCookie(res, req.user as GitHubUser);
    res.redirect(`${process.env.UI_ORIGIN}/events`);
  },
);

// Returns the authenticated user decoded from the JWT cookie
router.get("/auth/session", (req: Request, res: Response) => {
  const token = req.cookies?.[COOKIE_NAME];
  if (!token) {
    res.status(401).json({ user: null });
    return;
  }

  try {
    const user = jwt.verify(token, jwtSecret()) as GitHubUser;
    res.json({ user });
  } catch {
    res.status(401).json({ user: null });
  }
});

// Sign out — clears the JWT cookie
// Origin check guards against CSRF (a malicious page silently logging the user out)
router.post("/auth/logout", (req: Request, res: Response) => {
  if (req.headers.origin !== process.env.UI_ORIGIN) {
    res.status(403).json({ error: "forbidden" });
    return;
  }

  res.clearCookie(COOKIE_NAME, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: process.env.NODE_ENV === "production" ? "strict" : "lax",
  });
  res.json({ ok: true });
});

export default router;
