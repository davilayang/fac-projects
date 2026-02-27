import { Router } from "express";
import passport from "../../lib/passport.js";
import {
  handleCallback,
  handleSession,
  handleLogout,
} from "./github.handlers.js";

const router = Router();

router.get("/login", passport.authenticate("github"));

router.get(
  "/callback",
  passport.authenticate("github", {
    session: false,
    failureRedirect: `${process.env.UI_ORIGIN}/unauthorised`,
  }),
  handleCallback,
);

router.get("/session", handleSession);

router.post("/logout", handleLogout);

export default router;
