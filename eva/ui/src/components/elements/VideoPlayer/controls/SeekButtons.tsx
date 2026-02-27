import { SeekBackIcon, SeekForwardIcon } from "@eva-icons";
import { useVideoPlayer } from "./VideoPlayerContext";
import "./controls.css";

const SEEK_DELTA = 10; // seconds

export function SeekButtons() {
  const { playerRef, state } = useVideoPlayer();

  const seekBy = (delta: number) => {
    const next = Math.max(0, Math.min(state.currentTime + delta, state.duration));
    playerRef.current?.setCurrentTime(next);
  };

  return (
    <>
      <button
        type="button"
        className="vc-btn"
        aria-label={`Seek back ${SEEK_DELTA} seconds`}
        onClick={() => seekBy(-SEEK_DELTA)}
      >
        <SeekBackIcon />
      </button>
      <button
        type="button"
        className="vc-btn"
        aria-label={`Seek forward ${SEEK_DELTA} seconds`}
        onClick={() => seekBy(SEEK_DELTA)}
      >
        <SeekForwardIcon />
      </button>
    </>
  );
}
