import ApiVideoPlayer, {
  type ApiVideoPlayerRef,
} from "@api.video/react-player";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { useRoomContext } from "@livekit/components-react";
import type { RpcInvocationData } from "livekit-client";
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

// ── Moment helpers (shared with MomentsTab via localStorage + custom event) ─

interface EventVideoMoment {
  id: string;
  type: "bookmark" | "note";
  time: number;
  text: string;
  createdAt: string;
  source: "agent" | "user";
}

function getMomentsStorageKey(videoId: string) {
  return `event-video-moments:${videoId}`;
}

function persistMoment(videoId: string, moment: EventVideoMoment) {
  const key = getMomentsStorageKey(videoId);
  const raw = window.localStorage.getItem(key);
  let existing: EventVideoMoment[] = [];
  try {
    const parsed = JSON.parse(raw ?? "[]") as EventVideoMoment[];
    if (Array.isArray(parsed)) existing = parsed;
  } catch { /* ignore */ }
  window.localStorage.setItem(key, JSON.stringify([moment, ...existing]));
  window.dispatchEvent(
    new CustomEvent("event-video-moment:added", { detail: { videoId, moment } }),
  );
}

function generateId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

// ── RPC method names (must match agent.py) ──────────────────────────────────

const RPC = {
  PLAY:             "video.play",
  PAUSE:            "video.pause",
  SET_CURRENT_TIME: "video.setCurrentTime",
  SEEK_BY:          "video.seekBy",
  ADD_BOOKMARK:     "video.addBookmark",
  ADD_NOTE:         "video.addNote",
} as const;

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
  const room = useRoomContext();
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

  // ── Idle cursor / controls auto-hide in fullscreen ───────────────────────
  const idleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;

    const IDLE_MS = 3000;

    const setIdle = () => wrapper.setAttribute("data-idle", "true");
    const resetIdle = () => {
      wrapper.removeAttribute("data-idle");
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
      idleTimerRef.current = setTimeout(setIdle, IDLE_MS);
    };

    wrapper.addEventListener("mousemove", resetIdle);
    wrapper.addEventListener("mousedown", resetIdle);
    wrapper.addEventListener("keydown", resetIdle);

    // Start the timer immediately
    idleTimerRef.current = setTimeout(setIdle, IDLE_MS);

    return () => {
      wrapper.removeEventListener("mousemove", resetIdle);
      wrapper.removeEventListener("mousedown", resetIdle);
      wrapper.removeEventListener("keydown", resetIdle);
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
      wrapper.removeAttribute("data-idle");
    };
  }, []);

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

  // ── LiveKit RPC handlers — agent calls these to control the player ────────
  useEffect(() => {
    if (!room.localParticipant) return;
    const lp = room.localParticipant;

    const ok = (extra?: object) =>
      JSON.stringify({ ok: true, ...extra });

    const parsePayload = (data: RpcInvocationData) => {
      try { return JSON.parse(data.payload) as Record<string, unknown>; }
      catch { return {}; }
    };

    const handlers: [string, (data: RpcInvocationData) => Promise<string>][] = [
      [RPC.PLAY, async () => {
        playerRef.current?.play();
        return ok();
      }],
      [RPC.PAUSE, async () => {
        playerRef.current?.pause();
        return ok();
      }],
      [RPC.SET_CURRENT_TIME, async (data) => {
        const { time } = parsePayload(data);
        const t = Number(time);
        if (!Number.isFinite(t) || t < 0) throw new Error("time must be a number >= 0");
        setCurrentTime(t);
        return ok({ time: t });
      }],
      [RPC.SEEK_BY, async (data) => {
        const { delta } = parsePayload(data);
        const d = Number(delta);
        if (!Number.isFinite(d)) throw new Error("delta must be a finite number");
        seekBy(d);
        return ok({ delta: d });
      }],
      [RPC.ADD_BOOKMARK, async (data) => {
        const { label, time } = parsePayload(data);
        const text = (typeof label === "string" && label.trim()) || "Bookmark";
        const t = time !== undefined ? Number(time) : stateRef.current.currentTime;
        const moment: EventVideoMoment = {
          id: generateId(), type: "bookmark", time: t, text,
          createdAt: new Date().toISOString(), source: "agent",
        };
        persistMoment(id, moment);
        return ok({ moment });
      }],
      [RPC.ADD_NOTE, async (data) => {
        const { text, time } = parsePayload(data);
        const noteText = typeof text === "string" ? text.trim() : "";
        if (!noteText) throw new Error("text is required for notes");
        const t = time !== undefined ? Number(time) : stateRef.current.currentTime;
        const moment: EventVideoMoment = {
          id: generateId(), type: "note", time: t, text: noteText,
          createdAt: new Date().toISOString(), source: "agent",
        };
        persistMoment(id, moment);
        return ok({ moment });
      }],
    ];

    for (const [method, handler] of handlers) {
      lp.registerRpcMethod(method, handler);
    }

    return () => {
      for (const [method] of handlers) {
        lp.unregisterRpcMethod(method);
      }
    };
  }, [room.localParticipant, id, setCurrentTime, seekBy]);

  return (
    <VideoPlayerContext
      value={{ playerRef, state: playerState, enterFullscreen, exitFullscreen }}
    >
      {/*
       * The wrapper is what gets fullscreened — both the video and the
       * control bar are inside it, so controls stay visible in fullscreen.
       */}
      <div ref={wrapperRef} className="video-player">
        <div className="video-player__video-area">
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
          {/* Transparent overlay so clicks on the video area toggle play/pause */}
          <div
            className="video-player__click-overlay"
            aria-hidden="true"
            onClick={() =>
              stateRef.current.isPlaying
                ? playerRef.current?.pause()
                : playerRef.current?.play()
            }
          />
        </div>
        {controls && (
          <div className="video-player__controls-bar">{controls}</div>
        )}
      </div>
    </VideoPlayerContext>
  );
}
