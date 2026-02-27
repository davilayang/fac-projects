import { PlayIcon, PauseIcon } from "@eva-icons";
import { useVideoPlayer } from "./VideoPlayerContext";
import "./controls.css";

export function PlayButton() {
  const { playerRef, state } = useVideoPlayer();
  const { isPlaying } = state;

  return (
    <button
      type="button"
      className="vc-btn"
      aria-label={isPlaying ? "Pause" : "Play"}
      onClick={() =>
        isPlaying ? playerRef.current?.pause() : playerRef.current?.play()
      }
    >
      {isPlaying ? <PauseIcon /> : <PlayIcon />}
    </button>
  );
}
