import { useSession } from "@livekit/components-react";
import { TokenSource } from "livekit-client";
import { env } from "@eva-configs";

const tokenSource = TokenSource.endpoint("/auth/livekit/token", {
  credentials: "include",
});

/**
 * Creates a LiveKit agent session scoped to the calling component.
 * The session is NOT started automatically — call session.start() on user gesture.
 */
export function useAgentSession() {
  return useSession(tokenSource, { agentName: env.VITE_AGENT_NAME });
}
