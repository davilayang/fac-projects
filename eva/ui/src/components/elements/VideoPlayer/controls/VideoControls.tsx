import { PlayButton } from "./PlayButton";
import { SeekButtons } from "./SeekButtons";
import { SeekBar } from "./SeekBar";
import { VolumeButton } from "./VolumeButton";
import { FullscreenButton } from "./FullscreenButton";
import { AgentButton } from "./AgentButton";
import type { AgentButtonProps } from "./AgentButton";
import "./VideoControls.css";

interface VideoControlsProps {
  /** Pass agent session props to wire up the Talk-to-Agent control. */
  agent?: AgentButtonProps;
}

/**
 * Default control bar layout.
 *
 * Layout:
 *   [Play] [SeekBack] [SeekFwd] [────── SeekBar ──────] [Volume] [Agent] [Fullscreen]
 *
 * Each control is independently importable — swap, add, or remove any of
 * them here to customise the bar, or build your own layout from scratch
 * using the same primitives.
 */
export function VideoControls({ agent }: VideoControlsProps) {
  return (
    <div className="video-controls">
      <PlayButton />
      <SeekButtons />
      <SeekBar />
      <VolumeButton />
      {agent && <AgentButton {...agent} />}
      <FullscreenButton />
    </div>
  );
}
