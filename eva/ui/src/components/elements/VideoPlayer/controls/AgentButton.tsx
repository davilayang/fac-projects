import type { AgentState } from "@livekit/components-react";
import { useEffect, useRef, useState } from "react";
import { MicIcon, VolumeIcon, VolumeOffIcon } from "@eva-icons";
import "./controls.css";

/**
 * A video control bar slot for the voice agent.
 *
 * Accepts session state as props — it knows nothing about LiveKit internals.
 * Wire it up from the outside (e.g. Event.tsx) using useSessionContext and
 * useVoiceAssistant to obtain the values.
 */

// ── Animated bar visualizer ───────────────────────────────────────────────

const BAR_COUNT = 4;

function getSequencerInterval(state: AgentState): number {
  switch (state) {
    case "connecting":
    case "initializing":
      return 400;
    case "listening":
      return 120;
    case "thinking":
      return 60;
    default:
      return 250;
  }
}

function AgentVisualizer({ state }: { state: AgentState }) {
  const [highlighted, setHighlighted] = useState<number>(0);
  const frameRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (frameRef.current) clearTimeout(frameRef.current);
    const interval = getSequencerInterval(state);
    let idx = 0;
    const tick = () => {
      setHighlighted(idx % BAR_COUNT);
      idx++;
      frameRef.current = setTimeout(tick, interval);
    };
    tick();
    return () => { if (frameRef.current) clearTimeout(frameRef.current); };
  }, [state]);

  return (
    <span className="vc-agent-visualizer" aria-hidden="true">
      {Array.from({ length: BAR_COUNT }, (_, i) => (
        <span
          key={i}
          className="vc-agent-visualizer__bar"
          data-active={i === highlighted}
        />
      ))}
    </span>
  );
}

// ── Status label ──────────────────────────────────────────────────────────

function getStatusLabel(state: AgentState, muted: boolean): string {
  if (muted) return "Muted";
  switch (state) {
    case "connecting":
    case "initializing": return "Connecting…";
    case "listening":    return "Listening";
    case "thinking":     return "Thinking…";
    case "speaking":     return "Speaking";
    case "idle":         return "Idle";
    default:             return state;
  }
}

// ── AgentButton ───────────────────────────────────────────────────────────

export interface AgentButtonProps {
  /** Whether the LiveKit session is connected */
  isConnected: boolean;
  agentState: AgentState;
  muted: boolean;
  onStart: () => void;
  onEnd: () => void;
  onToggleMute: () => void;
}

export function AgentButton({
  isConnected,
  agentState,
  muted,
  onStart,
  onEnd,
  onToggleMute,
}: AgentButtonProps) {
  if (!isConnected) {
    return (
      <button
        type="button"
        className="vc-btn vc-agent-btn"
        onClick={onStart}
        aria-label="Talk to agent"
      >
        <MicIcon />
        <span className="vc-agent-btn__label">Talk to Agent</span>
      </button>
    );
  }

  return (
    <div className="vc-agent-connected">
      <AgentVisualizer state={agentState} />
      <span className="vc-agent-connected__label">
        {getStatusLabel(agentState, muted)}
      </span>
      <button
        type="button"
        className="vc-btn vc-btn--icon"
        onClick={onToggleMute}
        aria-label={muted ? "Unmute agent" : "Mute agent"}
        aria-pressed={muted}
        data-muted={muted}
      >
        {muted ? <VolumeOffIcon /> : <VolumeIcon />}
      </button>
      <button
        type="button"
        className="vc-btn vc-btn--danger"
        onClick={onEnd}
        aria-label="End voice session"
      >
        End
      </button>
    </div>
  );
}

