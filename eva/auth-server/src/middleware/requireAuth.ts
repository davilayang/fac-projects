import type { Request, Response, NextFunction } from "express";
import { COOKIE_NAME } from "../lib/cookie.js";
import { verifyAuthToken } from "../lib/jwt.js";
import type { GitHubUser } from "../lib/passport.js";

declare global {
  namespace Express {
    interface Request {
      authUser?: GitHubUser;
    }
  }
}

export function requireAuth(
  req: Request,
  res: Response,
  next: NextFunction,
): void {
  const token = req.cookies?.[COOKIE_NAME];
  if (!token) {
    res.status(401).json({ error: "Unauthorised" });
    return;
  }

  try {
    req.authUser = verifyAuthToken(token);
    next();
  } catch {
    res.status(401).json({ error: "Unauthorised" });
  }
}
