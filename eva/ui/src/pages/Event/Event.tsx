import { useState } from "react";
import { useParams } from "react-router";
import { Link } from "react-router";
import { ROUTES } from "../../router";
import "./Event.css";
import { VideoPlayer, Tabs } from "@eva-elements";
import type { TabItem } from "@eva-elements";

function VoiceGuide() {
  return (
    <div className="event__voice-guide">
      <ul className="event__guide-steps">
        <li>Tap <strong>Talk To Agent</strong> directly on the player to start the voice session.</li>
        <li>Use voice commands like <em>pause the video</em>, <em>play the video</em>, or <em>jump to 1 minute 20 seconds</em>.</li>
        <li>You can also say <em>skip forward 30 seconds</em> or <em>rewind 15 seconds</em>.</li>
        <li>Say <em>bookmark this moment</em> to save a timestamp you can revisit later.</li>
        <li>Say <em>take a note</em> then dictate what to remember at this exact point.</li>
        <li>When the agent speaks, playback pauses automatically and then resumes.</li>
      </ul>

      <div className="event__api-callout">
        <p className="event__api-callout-title">Agent Control API</p>
        <p>
          Voice-agent integrations can call{" "}
          <code>window.eventVideoPlayer</code> for{" "}
          <code>play</code>, <code>pause</code>, <code>setCurrentTime</code>, and <code>seekBy</code>.
        </p>
        <p>
          You can also dispatch <code>event-video-player:command</code> with commands such as{" "}
          <code>{"{ action: 'setCurrentTime', time: 90 }"}</code>.
        </p>
      </div>
    </div>
  );
}

function Moments() {
  return (
    <div className="event__moments">
      <p className="event__moments-empty">No moments saved yet. Use the voice agent to bookmark timestamps and take notes.</p>
    </div>
  );
}

const EVENT_TABS: TabItem[] = [
  { id: "voice-guide", label: "Voice Guide", content: <VoiceGuide /> },
  { id: "moments", label: "Moments", content: <Moments /> },
];

function ChevronRightIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronLeftIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Event() {
  const { id } = useParams<{ id: string }>();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  if (!id) {
    return <p>No video available</p>;
  }

  return (
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

      <div className={["event__body", sidebarOpen ? "event__body--sidebar-open" : ""].filter(Boolean).join(" ")}>
        <header className="event__header">
          <p className="event__eyebrow">Now Playing</p>
          <h1 className="event__title">{id}</h1>
          <VideoPlayer id={id} />
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
            <Tabs tabs={EVENT_TABS} />
          </div>
        </div>
      </div>
    </section>
  );
}
