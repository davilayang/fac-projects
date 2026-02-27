import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router";
import { SessionProvider } from "@livekit/components-react";

import { ChevronLeftIcon, ChevronRightIcon } from "@eva-icons";
import { ROUTES } from "@eva-router";
import { VideoPlayer, Tabs } from "@eva-elements";
import type { TabItem } from "@eva-elements";
import { useAgentSession } from "@eva-providers";

import { VoiceGuideTab, MomentsTab, AgentOverlayInner } from "./_components";

import "./Event.css";

export function Event() {
  const { id } = useParams<{ id: string }>();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const session = useAgentSession();

  // Keep a stable ref so the cleanup always reaches the live session
  // without listing `session` as a dep (prevents StrictMode double-fire).
  const sessionRef = useRef(session);
  sessionRef.current = session;

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
            <VideoPlayer id={id} overlay={<AgentOverlayInner />} />
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
