import { VolumeIcon, VolumeOffIcon } from "@eva-icons";
import { useVideoPlayer } from "./VideoPlayerContext";
import "./controls.css";

export function VolumeButton() {
  const { playerRef, state } = useVideoPlayer();
  const { isMuted, volume } = state;

  const toggleMute = () => {
    if (isMuted) {
      playerRef.current?.unmute();
    } else {
      playerRef.current?.mute();
    }
  };

  return (
    <div className="vc-volume">
      <button
        type="button"
        className="vc-btn"
        aria-label={isMuted ? "Unmute" : "Mute"}
        onClick={toggleMute}
      >
        {isMuted || volume === 0 ? <VolumeOffIcon /> : <VolumeIcon />}
      </button>
      <input
        type="range"
        className="vc-volume__slider"
        min={0}
        max={1}
        step={0.05}
        value={isMuted ? 0 : volume}
        aria-label="Volume"
        style={{ "--progress": `${(isMuted ? 0 : volume) * 100}%` } as React.CSSProperties}
        onChange={(e) => playerRef.current?.setVolume(Number(e.target.value))}
      />
    </div>
  );
}
