import ApiVideoPlayer, {
  type ApiVideoPlayerRef,
} from "@api.video/react-player";
import { useCallback, useEffect, useRef } from "react";

interface EventVideoPlayerController {
  play: () => void;
  pause: () => void;
  setCurrentTime: (time: number) => void;
  seekBy: (delta: number) => void;
  getState: () => {
    videoId: string;
    isReady: boolean;
    isPlaying: boolean;
    currentTime: number;
    duration: number;
  };
}

declare global {
  interface Window {
    eventVideoPlayer?: EventVideoPlayerController;
  }
}

interface EventVideoPlayerProps {
  id: string;
}

export function EventVideoPlayer({ id }: EventVideoPlayerProps) {
  const playerRef = useRef<ApiVideoPlayerRef>(null);
  const currentTimeRef = useRef(0);
  const isPlayingRef = useRef(false);
  const isReadyRef = useRef(false);
  const durationRef = useRef(0);

  const setCurrentTime = useCallback((time: number) => {
    playerRef.current?.setCurrentTime(Math.max(0, time));
  }, []);

  const seekBy = useCallback(
    (delta: number) => {
      setCurrentTime(currentTimeRef.current + delta);
    },
    [setCurrentTime]
  );

  useEffect(() => {
    const controller: EventVideoPlayerController = {
      play: () => playerRef.current?.play(),
      pause: () => playerRef.current?.pause(),
      setCurrentTime,
      seekBy,
      getState: () => ({
        videoId: id,
        isReady: isReadyRef.current,
        isPlaying: isPlayingRef.current,
        currentTime: currentTimeRef.current,
        duration: durationRef.current,
      }),
    };

    window.eventVideoPlayer = controller;
    return () => {
      if (window.eventVideoPlayer === controller) {
        window.eventVideoPlayer = undefined;
      }
    };
  }, [id, seekBy, setCurrentTime]);

  return (
    <section id="video-player-section">
      <ApiVideoPlayer
        ref={playerRef}
        video={{ id }}
        style={{ height: "480px" }}
        responsive={true}
        onReady={() => {
          isReadyRef.current = true;
        }}
        onPlay={() => {
          isPlayingRef.current = true;
        }}
        onPause={() => {
          isPlayingRef.current = false;
        }}
        onEnded={() => {
          isPlayingRef.current = false;
        }}
        onTimeUpdate={(t) => {
          currentTimeRef.current = t;
        }}
        onDurationChange={(d) => {
          durationRef.current = d;
        }}
      />
    </section>
  );
}
