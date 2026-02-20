'use client';

import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { RpcInvocationData } from 'livekit-client';
import ApiVideoPlayer, { type ApiVideoPlayerRef } from '@api.video/react-player';
import { useMaybeRoomContext } from '@livekit/components-react';

export type EventVideoPlayerCommand =
  | { action: 'play' }
  | { action: 'pause' }
  | { action: 'setCurrentTime'; time: number }
  | { action: 'seekBy'; delta: number };

export type EventVideoMomentType = 'bookmark' | 'note';

export interface EventVideoMoment {
  id: string;
  type: EventVideoMomentType;
  time: number;
  text: string;
  createdAt: string;
  source: 'agent' | 'user';
}

export interface EventVideoPlayerState {
  videoId: string;
  isReady: boolean;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
}

export interface EventVideoPlayerController {
  play: () => void;
  pause: () => void;
  setCurrentTime: (time: number) => void;
  seekBy: (delta: number) => void;
  getState: () => EventVideoPlayerState;
}

interface EventVideoPlayerProps {
  videoId: string;
  pauseOnAgentSpeech?: boolean;
  overlay?: ReactNode;
}

declare global {
  interface Window {
    eventVideoPlayer?: EventVideoPlayerController;
  }
}

const VIDEO_PLAYER_COMMAND_EVENT = 'event-video-player:command';
const VIDEO_PLAY_RPC_METHOD = 'video.play';
const VIDEO_PAUSE_RPC_METHOD = 'video.pause';
const VIDEO_SEEK_BY_RPC_METHOD = 'video.seekBy';
const VIDEO_SET_CURRENT_TIME_RPC_METHOD = 'video.setCurrentTime';
const VIDEO_ADD_BOOKMARK_RPC_METHOD = 'video.addBookmark';
const VIDEO_ADD_NOTE_RPC_METHOD = 'video.addNote';
export const VIDEO_MOMENT_ADDED_EVENT = 'event-video-moment:added';

function getMomentsStorageKey(videoId: string) {
  return `event-video-moments:${videoId}`;
}

function readMoments(videoId: string): EventVideoMoment[] {
  const raw = window.localStorage.getItem(getMomentsStorageKey(videoId));
  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw) as EventVideoMoment[];
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed;
  } catch {
    return [];
  }
}

function writeMoments(videoId: string, moments: EventVideoMoment[]) {
  window.localStorage.setItem(getMomentsStorageKey(videoId), JSON.stringify(moments));
}

function clampToMinZero(value: number) {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.max(0, value);
}

export function EventVideoPlayer({
  videoId,
  pauseOnAgentSpeech = false,
  overlay,
}: EventVideoPlayerProps) {
  const room = useMaybeRoomContext();
  const playerRef = useRef<ApiVideoPlayerRef>(null);
  const [isReady, setIsReady] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentPlaybackTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const currentTimeRef = useRef(0);
  const wasPlayingBeforeAgentSpeechRef = useRef(false);
  const previousPauseOnAgentSpeechRef = useRef(false);
  const resumeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const setCurrentTime = useCallback((time: number) => {
    playerRef.current?.setCurrentTime(clampToMinZero(time));
  }, []);
  const seekBy = useCallback(
    (delta: number) => {
      setCurrentTime(currentTimeRef.current + delta);
    },
    [setCurrentTime]
  );

  const handleCommand = useCallback(
    (command: EventVideoPlayerCommand) => {
      switch (command.action) {
        case 'play':
          playerRef.current?.play();
          return;
        case 'pause':
          playerRef.current?.pause();
          return;
        case 'setCurrentTime':
          setCurrentTime(command.time);
          return;
        case 'seekBy':
          seekBy(command.delta);
          return;
        default:
          return;
      }
    },
    [seekBy, setCurrentTime]
  );

  const controller = useMemo<EventVideoPlayerController>(
    () => ({
      play: () => playerRef.current?.play(),
      pause: () => playerRef.current?.pause(),
      setCurrentTime,
      seekBy,
      getState: () => ({
        videoId,
        isReady,
        isPlaying,
        currentTime,
        duration,
      }),
    }),
    [currentTime, duration, isPlaying, isReady, seekBy, setCurrentTime, videoId]
  );

  useEffect(() => {
    currentTimeRef.current = currentTime;
  }, [currentTime]);

  useEffect(() => {
    window.eventVideoPlayer = controller;
    return () => {
      if (window.eventVideoPlayer === controller) {
        window.eventVideoPlayer = undefined;
      }
    };
  }, [controller]);

  useEffect(() => {
    if (resumeTimeoutRef.current) {
      clearTimeout(resumeTimeoutRef.current);
      resumeTimeoutRef.current = null;
    }

    const wasAgentSpeaking = previousPauseOnAgentSpeechRef.current;

    if (pauseOnAgentSpeech && !wasAgentSpeaking) {
      wasPlayingBeforeAgentSpeechRef.current = isPlaying;
      if (isPlaying) {
        playerRef.current?.pause();
      }
    }

    if (!pauseOnAgentSpeech && wasAgentSpeaking && wasPlayingBeforeAgentSpeechRef.current) {
      // slight delay avoids rapid pause/play jitter between speaking turns
      resumeTimeoutRef.current = setTimeout(() => {
        playerRef.current?.play();
      }, 450);
      wasPlayingBeforeAgentSpeechRef.current = false;
    }

    previousPauseOnAgentSpeechRef.current = pauseOnAgentSpeech;

    return () => {
      if (resumeTimeoutRef.current) {
        clearTimeout(resumeTimeoutRef.current);
      }
    };
  }, [isPlaying, pauseOnAgentSpeech]);

  useEffect(() => {
    if (!room) {
      return;
    }

    const addMoment = (
      type: EventVideoMomentType,
      text: string,
      source: 'agent' | 'user',
      time?: number
    ) => {
      const moment: EventVideoMoment = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        type,
        time: clampToMinZero(time ?? currentTimeRef.current),
        text: text.trim(),
        createdAt: new Date().toISOString(),
        source,
      };
      const nextMoments = [moment, ...readMoments(videoId)];
      writeMoments(videoId, nextMoments);

      window.dispatchEvent(
        new CustomEvent(VIDEO_MOMENT_ADDED_EVENT, {
          detail: { videoId, moment },
        })
      );
      return moment;
    };

    room.localParticipant.registerRpcMethod(VIDEO_PLAY_RPC_METHOD, async () => {
      handleCommand({ action: 'play' });
      return JSON.stringify({ ok: true });
    });

    room.localParticipant.registerRpcMethod(VIDEO_PAUSE_RPC_METHOD, async () => {
      handleCommand({ action: 'pause' });
      // TODO: grab timestamp from player and return to the agent
      return JSON.stringify({ ok: true });
    });

    room.localParticipant.registerRpcMethod(
      VIDEO_SET_CURRENT_TIME_RPC_METHOD,
      async (data: RpcInvocationData) => {
        let parsedPayload: unknown;
        try {
          parsedPayload = JSON.parse(data.payload);
        } catch {
          throw new Error('Invalid RPC payload JSON');
        }

        const payload = parsedPayload as { time?: number };
        const time = Number(payload.time);
        if (!Number.isFinite(time) || time < 0) {
          throw new Error('time must be a number greater than or equal to 0');
        }

        setCurrentTime(time);
        return JSON.stringify({ ok: true, time });
      }
    );

    room.localParticipant.registerRpcMethod(
      VIDEO_SEEK_BY_RPC_METHOD,
      async (data: RpcInvocationData) => {
        let parsedPayload: unknown;
        try {
          parsedPayload = JSON.parse(data.payload);
        } catch {
          throw new Error('Invalid RPC payload JSON');
        }

        const payload = parsedPayload as { delta?: number };
        const delta = Number(payload.delta);
        if (!Number.isFinite(delta)) {
          throw new Error('delta must be a finite number');
        }

        seekBy(delta);
        return JSON.stringify({ ok: true, delta });
      }
    );

    room.localParticipant.registerRpcMethod(
      VIDEO_ADD_BOOKMARK_RPC_METHOD,
      async (data: RpcInvocationData) => {
        let parsedPayload: unknown = {};
        if (data.payload) {
          try {
            parsedPayload = JSON.parse(data.payload);
          } catch {
            throw new Error('Invalid RPC payload JSON');
          }
        }

        const payload = parsedPayload as { label?: string; time?: number };
        const label = payload.label?.trim() || 'Bookmark';
        const moment = addMoment('bookmark', label, 'agent', payload.time);
        return JSON.stringify({ ok: true, moment });
      }
    );

    room.localParticipant.registerRpcMethod(
      VIDEO_ADD_NOTE_RPC_METHOD,
      async (data: RpcInvocationData) => {
        let parsedPayload: unknown;
        try {
          parsedPayload = JSON.parse(data.payload);
        } catch {
          throw new Error('Invalid RPC payload JSON');
        }

        const payload = parsedPayload as { text?: string; time?: number };
        const text = payload.text?.trim() ?? '';
        if (!text) {
          throw new Error('text is required for notes');
        }

        const moment = addMoment('note', text, 'agent', payload.time);
        return JSON.stringify({ ok: true, moment });
      }
    );

    return () => {
      room.localParticipant.unregisterRpcMethod(VIDEO_PLAY_RPC_METHOD);
      room.localParticipant.unregisterRpcMethod(VIDEO_PAUSE_RPC_METHOD);
      room.localParticipant.unregisterRpcMethod(VIDEO_SET_CURRENT_TIME_RPC_METHOD);
      room.localParticipant.unregisterRpcMethod(VIDEO_SEEK_BY_RPC_METHOD);
      room.localParticipant.unregisterRpcMethod(VIDEO_ADD_BOOKMARK_RPC_METHOD);
      room.localParticipant.unregisterRpcMethod(VIDEO_ADD_NOTE_RPC_METHOD);
    };
  }, [handleCommand, room, seekBy, setCurrentTime, videoId]);

  useEffect(() => {
    const onCommandEvent = (event: Event) => {
      const customEvent = event as CustomEvent<EventVideoPlayerCommand>;
      if (!customEvent.detail) {
        return;
      }
      handleCommand(customEvent.detail);
    };

    const onWindowMessage = (event: MessageEvent) => {
      const payload = event.data as
        | { type?: string; command?: EventVideoPlayerCommand }
        | undefined;
      if (payload?.type !== VIDEO_PLAYER_COMMAND_EVENT || !payload.command) {
        return;
      }
      handleCommand(payload.command);
    };

    window.addEventListener(VIDEO_PLAYER_COMMAND_EVENT, onCommandEvent as EventListener);
    window.addEventListener('message', onWindowMessage);
    return () => {
      window.removeEventListener(VIDEO_PLAYER_COMMAND_EVENT, onCommandEvent as EventListener);
      window.removeEventListener('message', onWindowMessage);
    };
  }, [handleCommand]);

  return (
    <div className="relative overflow-hidden rounded-2xl border border-white/15 bg-black/40 shadow-[0_20px_80px_rgba(0,0,0,0.6)] backdrop-blur-sm">
      <ApiVideoPlayer
        ref={playerRef}
        video={{ id: videoId }}
        style={{
          width: '100%',
          height: 'auto',
          aspectRatio: '16 / 9',
          display: 'block',
          backgroundColor: '#000',
        }}
        onReady={() => setIsReady(true)}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onEnded={() => setIsPlaying(false)}
        onTimeUpdate={setCurrentPlaybackTime}
        onDurationChange={setDuration}
      />
      {overlay && (
        <div className="pointer-events-auto absolute inset-x-0 top-0 z-20 p-4">{overlay}</div>
      )}
    </div>
  );
}
