'use client';

import { useMemo, useState } from 'react';
import { TokenSource } from 'livekit-client';
import { Mic } from 'lucide-react';
import { useSession, useSessionContext, useVoiceAssistant } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { AgentAudioVisualizerBar } from '@/components/agents-ui/agent-audio-visualizer-bar';
import {
  AgentControlBar,
  type AgentControlBarControls,
} from '@/components/agents-ui/agent-control-bar';
import { AgentSessionProvider } from '@/components/agents-ui/agent-session-provider';
import { Button } from '@/components/ui/button';
import { getSandboxTokenSource } from '@/lib/utils';
import { EventVideoPlayer } from './player';

interface EventVoiceExperienceProps {
  videoId: string;
  appConfig: AppConfig;
}

function EventVoiceExperienceInner({ videoId, appConfig }: EventVoiceExperienceProps) {
  const session = useSessionContext();
  const { state: agentState, audioTrack } = useVoiceAssistant();
  const [chatOpen, setChatOpen] = useState(false);

  const controls: AgentControlBarControls = {
    leave: true,
    microphone: true,
    chat: appConfig.supportsChatInput,
    camera: false,
    screenShare: false,
  };

  const statusLabel = agentState
    ? agentState.charAt(0).toUpperCase() + agentState.slice(1)
    : 'Idle';
  const isConnected = session.isConnected;
  const isAgentSpeaking = agentState === 'speaking';

  const overlay = (
    <div className="flex justify-end">
      {!isConnected ? (
        <Button
          type="button"
          onClick={() => {
            void session.start();
          }}
          className="pointer-events-auto rounded-full border border-white/20 bg-black/70 px-4 font-mono text-xs tracking-[0.14em] uppercase"
        >
          <Mic className="mr-2 size-4" />
          Talk To Agent
        </Button>
      ) : (
        <div className="pointer-events-auto flex min-w-[220px] items-center gap-3 rounded-full border border-white/20 bg-black/70 px-4 py-2">
          <AgentAudioVisualizerBar
            size="icon"
            state={agentState}
            audioTrack={audioTrack}
            barCount={6}
            className="h-5"
          />
          <div className="font-mono text-[11px] tracking-[0.12em] text-white/80 uppercase">
            Agent: {statusLabel}
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="space-y-4">
      <EventVideoPlayer
        videoId={videoId}
        overlay={overlay}
        pauseOnAgentSpeech={isConnected && isAgentSpeaking}
      />

      <div className="rounded-2xl border border-white/15 bg-black/35 p-4 backdrop-blur-sm">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <p className="font-mono text-[11px] tracking-[0.16em] text-white/70 uppercase">
            Voice Agent
          </p>
          <p className="text-xs text-white/60">Video auto-pauses while the agent is speaking</p>
        </div>
        <AgentControlBar
          variant="livekit"
          controls={controls}
          isChatOpen={chatOpen}
          isConnected={isConnected}
          onIsChatOpenChange={setChatOpen}
          className="border-white/15 bg-black/50 text-white [&_textarea]:text-white [&_textarea]:placeholder:text-white/40"
        />
      </div>
    </div>
  );
}

export function EventVoiceExperience({ videoId, appConfig }: EventVoiceExperienceProps) {
  const tokenSource = useMemo(() => {
    return typeof process.env.NEXT_PUBLIC_CONN_DETAILS_ENDPOINT === 'string'
      ? getSandboxTokenSource(appConfig)
      : TokenSource.endpoint('/api/connection-details');
  }, [appConfig]);

  const session = useSession(
    tokenSource,
    appConfig.agentName ? { agentName: appConfig.agentName } : undefined
  );

  return (
    <AgentSessionProvider session={session}>
      <EventVoiceExperienceInner videoId={videoId} appConfig={appConfig} />
    </AgentSessionProvider>
  );
}
