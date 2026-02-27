import type { Request, Response } from "express";
import {
  setAuthCookie,
  clearAuthCookie,
  COOKIE_NAME,
} from "../../lib/cookie.js";
import { verifyAuthToken } from "../../lib/jwt.js";
import type { GitHubUser } from "../../lib/passport.js";

export function handleCallback(req: Request, res: Response): void {
  setAuthCookie(res, req.user as GitHubUser);
  res.redirect(`${process.env.UI_ORIGIN}/events`);
}

export function handleSession(req: Request, res: Response): void {
  const token = req.cookies?.[COOKIE_NAME];
  if (!token) {
    res.status(401).json({ user: null });
    return;
  }

  try {
    const user = verifyAuthToken(token);
    res.json({ user });
  } catch {
    res.status(401).json({ user: null });
  }
}

export function handleLogout(req: Request, res: Response): void {
  if (req.headers.origin !== process.env.UI_ORIGIN) {
    res.status(403).json({ error: "Forbidden" });
    return;
  }

  clearAuthCookie(res);
  res.json({ ok: true });
}
