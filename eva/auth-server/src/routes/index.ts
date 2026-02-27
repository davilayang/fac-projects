import { Router } from "express";
import githubRouter from "./github/github.router.js";
import livekitRouter from "./livekit/livekit.router.js";

const router = Router();

router.use("/auth/github", githubRouter);
router.use("/auth/livekit", livekitRouter);

export default router;
