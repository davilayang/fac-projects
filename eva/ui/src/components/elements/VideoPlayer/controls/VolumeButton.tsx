import { useState } from "react";
import { VolumeIcon, VolumeOffIcon } from "@eva-icons";
import { useVideoPlayer } from "./VideoPlayerContext";
import "./controls.css";

export function VolumeButton() {
  const { playerRef, state } = useVideoPlayer();
  const { volume } = state;

  // The api.video SDK has no onMute/onUnmute event, so we track mute locally.
  const [isMuted, setIsMuted] = useState(false);

  const toggleMute = () => {
    if (isMuted) {
      playerRef.current?.unmute();
      setIsMuted(false);
    } else {
      playerRef.current?.mute();
      setIsMuted(true);
    }
  };

  const displayVolume = isMuted ? 0 : volume;

  return (
    <div className="vc-volume">
      <button
        type="button"
        className="vc-btn"
        aria-label={isMuted ? "Unmute" : "Mute"}
        aria-pressed={isMuted}
        onClick={toggleMute}
      >
        {isMuted ? <VolumeOffIcon /> : <VolumeIcon />}
      </button>
      <input
        type="range"
        className="vc-volume__slider"
        min={0}
        max={1}
        step={0.05}
        value={displayVolume}
        aria-label="Volume"
        style={{ "--progress": `${displayVolume * 100}%` } as React.CSSProperties}
        onChange={(e) => {
          const v = Number(e.target.value);
          playerRef.current?.setVolume(v);
          if (isMuted && v > 0) {
            playerRef.current?.unmute();
            setIsMuted(false);
          }
        }}
      />
    </div>
  );
}
