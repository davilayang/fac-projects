import ApiVideoPlayer, {
  type ApiVideoPlayerRef,
} from "@api.video/react-player";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import {
  VideoPlayerContext,
  type VideoPlayerState,
} from "./controls/VideoPlayerContext";
import "./VideoPlayer.css";

// ── Global imperative controller (used by agent RPC handlers) ────────────

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

// ── Component ─────────────────────────────────────────────────────────────

interface EventVideoPlayerProps {
  id: string;
  /**
   * Slot for the control bar — render <VideoControls /> here.
   * Sits below the video inside the fullscreen wrapper so controls
   * are always visible regardless of fullscreen state.
   */
  controls?: ReactNode;
}

export function EventVideoPlayer({ id, controls }: EventVideoPlayerProps) {
  const playerRef = useRef<ApiVideoPlayerRef>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const isReadyRef = useRef(false);

  // ── Player state — surfaced via context to all child controls ────────────
  const [playerState, setPlayerState] = useState<VideoPlayerState>({
    isPlaying: false,
    isMuted: false,
    volume: 1,
    currentTime: 0,
    duration: 0,
    isFullscreen: false,
  });

  // Stable ref so agent callbacks can read current values synchronously
  const stateRef = useRef(playerState);
  const updateState = useCallback((patch: Partial<VideoPlayerState>) => {
    setPlayerState((prev) => {
      const next = { ...prev, ...patch };
      stateRef.current = next;
      return next;
    });
  }, []);

  // ── Fullscreen — fullscreen the entire wrapper (video + controls) ────────
  const enterFullscreen = useCallback(() => {
    void wrapperRef.current?.requestFullscreen();
  }, []);

  const exitFullscreen = useCallback(() => {
    if (document.fullscreenElement) void document.exitFullscreen();
  }, []);

  useEffect(() => {
    const onChange = () =>
      updateState({ isFullscreen: document.fullscreenElement === wrapperRef.current });
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, [updateState]);

  // ── Global imperative controller (called by agent RPC) ──────────────────
  const setCurrentTime = useCallback(
    (time: number) => playerRef.current?.setCurrentTime(Math.max(0, time)),
    [],
  );

  const seekBy = useCallback(
    (delta: number) => setCurrentTime(stateRef.current.currentTime + delta),
    [setCurrentTime],
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
        isPlaying: stateRef.current.isPlaying,
        currentTime: stateRef.current.currentTime,
        duration: stateRef.current.duration,
      }),
    };
    window.eventVideoPlayer = controller;
    return () => {
      if (window.eventVideoPlayer === controller)
        window.eventVideoPlayer = undefined;
    };
  }, [id, seekBy, setCurrentTime]);

  return (
    <VideoPlayerContext
      value={{ playerRef, state: playerState, enterFullscreen, exitFullscreen }}
    >
      {/*
       * The wrapper is what gets fullscreened — both the video and the
       * control bar are inside it, so controls stay visible in fullscreen.
       */}
      <div ref={wrapperRef} className="video-player">
        <ApiVideoPlayer
          ref={playerRef}
          video={{ id }}
          chromeless
          style={{ width: "100%", aspectRatio: "16/9", display: "block" }}
          onReady={() => { isReadyRef.current = true; }}
          onPlay={() => updateState({ isPlaying: true })}
          onPause={() => updateState({ isPlaying: false })}
          onEnded={() => updateState({ isPlaying: false })}
          onTimeUpdate={(t) => updateState({ currentTime: t })}
          onDurationChange={(d) => updateState({ duration: d })}
          onVolumeChange={(v) => updateState({ volume: v, isMuted: v === 0 })}
        />
        {controls && (
          <div className="video-player__controls-bar">{controls}</div>
        )}
      </div>
    </VideoPlayerContext>
  );
}
