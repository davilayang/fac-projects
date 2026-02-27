import { useCallback, useEffect, useRef, useState } from "react";
import {
  useSessionContext,
  useVoiceAssistant,
  useMultibandTrackVolume,
  RoomAudioRenderer,
} from "@livekit/components-react";
import type { AgentState } from "@livekit/components-react";
import "./agent-overlay.css";

// ── Animated bar visualizer ──────────────────────────────────────────────────

const BAR_COUNT = 5;

function getSequencerInterval(state: AgentState): number {
  switch (state) {
    case "connecting":
    case "initializing":
      return 400;
    case "listening":
      return 100;
    case "thinking":
      return 60;
    default:
      return 200;
  }
}

function AgentVisualizer({
  state,
  audioTrack,
  muted,
}: {
  state: AgentState;
  audioTrack: ReturnType<typeof useVoiceAssistant>["audioTrack"];
  muted: boolean;
}) {
  const volumeBands = useMultibandTrackVolume(audioTrack, {
    bands: BAR_COUNT,
    loPass: 100,
    hiPass: 200,
  });

  const [highlighted, setHighlighted] = useState<number[]>([]);
  const frameRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const effectiveState = muted ? "idle" : state;

  useEffect(() => {
    if (frameRef.current) clearTimeout(frameRef.current);

    if (effectiveState === "speaking") {
      setHighlighted([]);
      return;
    }

    const interval = getSequencerInterval(effectiveState);
    let idx = 0;

    const tick = () => {
      setHighlighted([idx % BAR_COUNT]);
      idx++;
      frameRef.current = setTimeout(tick, interval);
    };

    tick();
    return () => {
      if (frameRef.current) clearTimeout(frameRef.current);
    };
  }, [effectiveState]);

  const bands =
    effectiveState === "speaking" ? volumeBands : new Array(BAR_COUNT).fill(0);

  return (
    <div className="agent-visualizer" data-state={effectiveState}>
      {bands.map((vol: number, i: number) => {
        const isHighlighted =
          effectiveState === "speaking" ? vol > 0.05 : highlighted.includes(i);
        return (
          <span
            key={i}
            className="agent-visualizer__bar"
            data-highlighted={isHighlighted}
            style={
              effectiveState === "speaking"
                ? { height: `${Math.max(20, vol * 100)}%` }
                : undefined
            }
          />
        );
      })}
    </div>
  );
}

// ── Status label ─────────────────────────────────────────────────────────────

function getStatusLabel(state: AgentState, muted: boolean): string {
  if (muted) return "Muted";
  switch (state) {
    case "connecting":
    case "initializing":
      return "Connecting…";
    case "listening":
      return "Listening";
    case "thinking":
      return "Thinking…";
    case "speaking":
      return "Speaking";
    case "idle":
      return "Idle";
    default:
      return state;
  }
}

// ── Main overlay ──────────────────────────────────────────────────────────────

export function AgentOverlayInner() {
  const session = useSessionContext();
  const { state: agentState, audioTrack } = useVoiceAssistant();
  const isConnected = session.isConnected;
  const [muted, setMuted] = useState(false);

  const handleStart = useCallback(() => void session.start(), [session]);
  const handleEnd = useCallback(() => void session.end(), [session]);
  const handleToggleMute = useCallback(() => setMuted((m) => !m), []);

  if (!isConnected) {
    return (
      <button
        type="button"
        className="agent-overlay__talk-btn"
        onClick={handleStart}
      >
        <MicIcon />
        Talk to Agent
      </button>
    );
  }

  return (
    <>
      <RoomAudioRenderer muted={muted} />
      <div className="agent-overlay__status">
        <AgentVisualizer
          state={agentState}
          audioTrack={audioTrack}
          muted={muted}
        />
        <span className="agent-overlay__status-label">
          {getStatusLabel(agentState, muted)}
        </span>
        <button
          type="button"
          className="agent-overlay__icon-btn"
          onClick={handleToggleMute}
          aria-label={muted ? "Unmute agent" : "Mute agent"}
          aria-pressed={muted}
          data-muted={muted}
        >
          {muted ? <VolumeOffIcon /> : <VolumeIcon />}
        </button>
        <button
          type="button"
          className="agent-overlay__end-btn"
          onClick={handleEnd}
          aria-label="End voice session"
        >
          End
        </button>
      </div>
    </>
  );
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function MicIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="22" />
    </svg>
  );
}

function VolumeIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
      <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
    </svg>
  );
}

function VolumeOffIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
      <line x1="23" y1="9" x2="17" y2="15" />
      <line x1="17" y1="9" x2="23" y2="15" />
    </svg>
  );
}
