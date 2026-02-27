import { EnterFullscreenIcon, ExitFullscreenIcon } from "@eva-icons";
import { useVideoPlayer } from "./VideoPlayerContext";
import "./controls.css";

export function FullscreenButton() {
  const { state, enterFullscreen, exitFullscreen } = useVideoPlayer();
  const { isFullscreen } = state;

  return (
    <button
      type="button"
      className="vc-btn"
      aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
      onClick={isFullscreen ? exitFullscreen : enterFullscreen}
    >
      {isFullscreen ? <ExitFullscreenIcon /> : <EnterFullscreenIcon />}
    </button>
  );
}
