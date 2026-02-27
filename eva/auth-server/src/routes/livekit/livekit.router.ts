import { Router } from "express";
import { requireAuth } from "../../middleware/requireAuth.js";
import { handleToken } from "./livekit.handlers.js";

const router = Router();

router.post("/token", requireAuth, handleToken);

export default router;
