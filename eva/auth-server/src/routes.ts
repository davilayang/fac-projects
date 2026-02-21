import { Router, type Request, type Response } from "express";
import passport from "./passport.js";

const router = Router();

// Kick off the GitHub OAuth flow
router.get("/auth/github/login", passport.authenticate("github"));

// GitHub redirects here after the user approves
router.get(
  "/auth/github/callback",
  passport.authenticate("github", {
    failureRedirect: `${process.env.UI_ORIGIN}/?error=unauthorised`,
  }),
  (_req: Request, res: Response) => {
    res.redirect(`${process.env.UI_ORIGIN}/events`);
  }
);

// The UI calls this on mount to check if there is an active session
router.get("/auth/session", (req: Request, res: Response) => {
  if (req.isAuthenticated()) {
    res.json({ user: req.user });
  } else {
    res.status(401).json({ user: null });
  }
});

// Sign out — clears the session cookie
// Origin check guards against CSRF (a malicious page silently logging the user out)
router.post("/auth/logout", (req: Request, res: Response) => {
  if (req.headers.origin !== process.env.UI_ORIGIN) {
    res.status(403).json({ error: "forbidden" });
    return;
  }
  req.logout(() => {
    res.json({ ok: true });
  });
});

export default router;
