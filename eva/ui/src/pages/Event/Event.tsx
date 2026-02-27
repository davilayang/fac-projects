import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router";
import {
  SessionProvider,
  useSessionContext,
  useVoiceAssistant,
  useLocalParticipant,
  useIsSpeaking,
  RoomAudioRenderer,
} from "@livekit/components-react";

import { ChevronLeftIcon, ChevronRightIcon } from "@eva-icons";
import { ROUTES } from "@eva-router";
import { VideoPlayer, Tabs } from "@eva-elements";
import { VideoControls } from "@eva-elements/VideoPlayer/controls";
import type { TabItem } from "@eva-elements";
import { useAgentSession } from "@eva-providers";

import { VoiceGuideTab, MomentsTab } from "./_components";

import "./Event.css";

// ── Agent control bar wiring ──────────────────────────────────────────────
// Reads LiveKit session/agent state and passes plain props down to AgentButton.
// This is the only place in the app that knows about both LiveKit and the
// video control bar — everything else is decoupled.

interface AgentControlsProps {
  onSpeakingChange: (speaking: boolean) => void;
}

function AgentControls({ onSpeakingChange }: AgentControlsProps) {
  const session = useSessionContext();
  const { state: agentState } = useVoiceAssistant();
  const { localParticipant } = useLocalParticipant();
  const isUserSpeaking = useIsSpeaking(localParticipant);
  const [muted, setMuted] = useState(false);

  const handleStart = useCallback(() => void session.start(), [session]);
  const handleEnd = useCallback(() => void session.end(), [session]);
  const handleToggleMute = useCallback(() => setMuted((m) => !m), []);

  // Pause while agent OR user is speaking
  const shouldPause = session.isConnected && (agentState === "speaking" || isUserSpeaking);
  useEffect(() => { onSpeakingChange(shouldPause); }, [shouldPause, onSpeakingChange]);

  return (
    <>
      {session.isConnected && <RoomAudioRenderer muted={muted} />}
      <VideoControls
        agent={{
          isConnected: session.isConnected,
          agentState,
          muted,
          onStart: handleStart,
          onEnd: handleEnd,
          onToggleMute: handleToggleMute,
        }}
      />
    </>
  );
}

// ── Event page ────────────────────────────────────────────────────────────

export function Event() {
  const { id } = useParams<{ id: string }>();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [agentSpeaking, setAgentSpeaking] = useState(false);
  const session = useAgentSession();

  const sessionRef = useRef(session);

  useEffect(() => {
    sessionRef.current = session;
  });

  useEffect(() => {
    return () => {
      void sessionRef.current.end();
    };
  }, []);

  const eventTabs = useMemo<TabItem[]>(
    () => [
      { id: "voice-guide", label: "Voice Guide", content: <VoiceGuideTab /> },
      {
        id: "moments",
        label: "Moments",
        content: <MomentsTab videoId={id ?? ""} />,
      },
    ],
    [id],
  );

  if (!id) {
    return <p>No video available</p>;
  }

  return (
    <SessionProvider session={session}>
      <section className="event">
        <nav className="event__breadcrumbs" aria-label="Breadcrumb">
          <Link to={ROUTES.EVENTS} className="event__breadcrumb-link">
            Events
          </Link>
          <span className="event__breadcrumb-sep" aria-hidden="true">
            /
          </span>
          <span className="event__breadcrumb-current" aria-current="page">
            {id}
          </span>
        </nav>

        <div
          className={[
            "event__body",
            sidebarOpen ? "event__body--sidebar-open" : "",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          <header className="event__header">
            <p className="event__eyebrow">Now Playing</p>
            <h1 className="event__title">{id}</h1>
            <VideoPlayer
              id={id}
              pauseOnAgentSpeech={agentSpeaking}
              controls={<AgentControls onSpeakingChange={setAgentSpeaking} />}
            />
          </header>

          <div className="event__sidebar" aria-expanded={sidebarOpen}>
            <button
              className="event__sidebar-toggle"
              onClick={() => setSidebarOpen((o) => !o)}
              aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
            >
              {sidebarOpen ? <ChevronRightIcon /> : <ChevronLeftIcon />}
            </button>

            <div className="event__sidebar-panel" aria-hidden={!sidebarOpen}>
              <Tabs tabs={eventTabs} />
            </div>
          </div>
        </div>
      </section>
    </SessionProvider>
  );
}
