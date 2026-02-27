import { useEffect } from "react";
import { useSession, SessionProvider } from "@livekit/components-react";
import { TokenSource } from "livekit-client";
import { env } from "@eva-configs";

const tokenSource = TokenSource.endpoint("/auth/livekit/token", {
  credentials: "include",
});

interface AgentSessionProviderProps {
  children: React.ReactNode;
}

export function AgentSessionProvider({ children }: AgentSessionProviderProps) {
  const session = useSession(tokenSource, { agentName: env.VITE_AGENT_NAME });

  useEffect(() => {
    session.start();
    return () => {
      session.end();
    };
  }, []);

  return <SessionProvider session={session}>{children}</SessionProvider>;
}
