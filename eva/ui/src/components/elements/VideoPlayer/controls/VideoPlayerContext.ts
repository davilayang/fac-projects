import { createContext, useContext } from "react";
import type { ApiVideoPlayerRef } from "@api.video/react-player";

export interface VideoPlayerState {
  isPlaying: boolean;
  isMuted: boolean;
  volume: number;        // 0–1
  currentTime: number;   // seconds
  duration: number;      // seconds
  isFullscreen: boolean;
}

export interface VideoPlayerContextValue {
  playerRef: React.RefObject<ApiVideoPlayerRef | null>;
  state: VideoPlayerState;
  /** Fullscreen the entire player wrapper (video + controls). */
  enterFullscreen: () => void;
  exitFullscreen: () => void;
}

export const VideoPlayerContext =
  createContext<VideoPlayerContextValue | null>(null);

export function useVideoPlayer(): VideoPlayerContextValue {
  const ctx = useContext(VideoPlayerContext);
  if (!ctx)
    throw new Error(
      "useVideoPlayer must be used inside <VideoPlayer>",
    );
  return ctx;
}
