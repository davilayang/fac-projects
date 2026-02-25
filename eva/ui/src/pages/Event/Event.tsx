import { useMemo, useState } from "react";
import { useParams } from "react-router";
import { Link } from "react-router";

import { ROUTES } from "../../router";

import { VideoPlayer, Tabs } from "@eva-elements";
import type { TabItem } from "@eva-elements";
import { ChevronLeftIcon, ChevronRightIcon } from "@eva-icons";

import { VoiceGuideTab, MomentsTab } from "./_components";

import "./Event.css";

export function Event() {
  const { id } = useParams<{ id: string }>();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const eventTabs = useMemo<TabItem[]>(
    () => [
      { id: "voice-guide", label: "Voice Guide", content: <VoiceGuideTab /> },
      {
        id: "moments",
        label: "Moments",
        content: <MomentsTab videoId={id ?? ""} />,
      },
    ],
    [id]
  );

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
            <Tabs tabs={eventTabs} />
          </div>
        </div>
      </div>
    </section>
  );
}
