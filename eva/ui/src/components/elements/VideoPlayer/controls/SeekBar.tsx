import { useVideoPlayer } from "./VideoPlayerContext";
import "./controls.css";

function formatTime(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0)
    return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  return `${m}:${String(sec).padStart(2, "0")}`;
}

export function SeekBar() {
  const { playerRef, state } = useVideoPlayer();
  const { currentTime, duration } = state;
  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div className="vc-seek">
      <input
        type="range"
        className="vc-seek__bar"
        min={0}
        max={duration || 100}
        step={0.5}
        value={currentTime}
        style={{ "--progress": `${progress}%` } as React.CSSProperties}
        aria-label="Seek"
        onChange={(e) =>
          playerRef.current?.setCurrentTime(Number(e.target.value))
        }
      />
      <span className="vc-seek__time">
        {formatTime(currentTime)}
        <span className="vc-seek__time-sep"> / </span>
        {formatTime(duration)}
      </span>
    </div>
  );
}
