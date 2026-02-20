'use client';

import { useEffect, useMemo, useState } from 'react';
import { Bookmark, Clock3, FileText, Trash2 } from 'lucide-react';
import { type EventVideoMoment, VIDEO_MOMENT_ADDED_EVENT } from '@/components/video/player';

interface EventMomentsPanelProps {
  videoId: string;
}

interface AddedMomentEventDetail {
  videoId: string;
  moment: EventVideoMoment;
}

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

function formatSeconds(value: number) {
  const total = Math.max(0, Math.floor(value));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }
  return `${minutes}:${String(seconds).padStart(2, '0')}`;
}

function MomentItem({ moment }: { moment: EventVideoMoment }) {
  const isNote = moment.type === 'note';

  return (
    <button
      type="button"
      onClick={() => window.eventVideoPlayer?.setCurrentTime(moment.time)}
      className="group w-full rounded-xl border border-white/10 bg-black/30 p-3 text-left transition hover:border-white/25 hover:bg-black/45"
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="inline-flex items-center gap-2 text-[11px] tracking-[0.14em] text-white/70 uppercase">
          {isNote ? <FileText className="size-3.5" /> : <Bookmark className="size-3.5" />}
          {isNote ? 'Note' : 'Bookmark'}
        </div>
        <div className="inline-flex items-center gap-1 rounded-full border border-white/15 bg-white/5 px-2 py-0.5 font-mono text-[11px] text-white/80">
          <Clock3 className="size-3" />
          {formatSeconds(moment.time)}
        </div>
      </div>
      <p className="line-clamp-3 text-sm text-white/85 group-hover:text-white">{moment.text}</p>
    </button>
  );
}

export function EventMomentsPanel({ videoId }: EventMomentsPanelProps) {
  const [moments, setMoments] = useState<EventVideoMoment[]>([]);
  const [activeTab, setActiveTab] = useState<'moments' | 'guide'>('guide');

  useEffect(() => {
    setMoments(readMoments(videoId));
  }, [videoId]);

  useEffect(() => {
    const onMomentAdded = (event: Event) => {
      const customEvent = event as CustomEvent<AddedMomentEventDetail>;
      if (customEvent.detail?.videoId !== videoId) {
        return;
      }
      setMoments((current) => [customEvent.detail.moment, ...current]);
    };

    window.addEventListener(VIDEO_MOMENT_ADDED_EVENT, onMomentAdded as EventListener);
    return () => {
      window.removeEventListener(VIDEO_MOMENT_ADDED_EVENT, onMomentAdded as EventListener);
    };
  }, [videoId]);

  const bookmarks = useMemo(
    () => moments.filter((moment) => moment.type === 'bookmark'),
    [moments]
  );
  const notes = useMemo(() => moments.filter((moment) => moment.type === 'note'), [moments]);

  const clearAll = () => {
    writeMoments(videoId, []);
    setMoments([]);
  };

  return (
    <aside className="rounded-2xl border border-white/15 bg-white/5 p-5 backdrop-blur-sm">
      <div className="mb-8">
        <div className="flex items-end border-b border-white/15">
          <button
            type="button"
            onClick={() => setActiveTab('guide')}
            aria-pressed={activeTab === 'guide'}
            className={`px-1 pb-3 text-sm font-semibold whitespace-nowrap transition ${
              activeTab === 'guide'
                ? 'border-b-2 border-white text-white'
                : 'text-white/65 hover:text-white'
            }`}
          >
            Voice Guide
          </button>
          <span className="mx-5 mb-3 h-4 w-px bg-white/15" aria-hidden />
          <button
            type="button"
            onClick={() => setActiveTab('moments')}
            aria-pressed={activeTab === 'moments'}
            className={`px-1 pb-3 text-sm font-semibold whitespace-nowrap transition ${
              activeTab === 'moments'
                ? 'border-b-2 border-white text-white'
                : 'text-white/65 hover:text-white'
            }`}
          >
            Moments
          </button>
        </div>
      </div>

      {activeTab === 'guide' && (
        <div className="pt-4">
          <ul className="space-y-3 text-sm text-white/75">
            <li>Tap Talk To Agent directly on the player to start the voice session.</li>
            <li>
              Use voice commands like pause the video, play the video, or jump to 1 minute 20
              seconds.
            </li>
            <li>You can also say skip forward 30 seconds or rewind 15 seconds.</li>
            <li>Say bookmark this moment to save a timestamp you can revisit later.</li>
            <li>Say take a note then dictate what to remember at this exact point.</li>
            <li>When the agent speaks, playback pauses automatically and then resumes.</li>
          </ul>
          <div className="mt-6 rounded-xl border border-white/10 bg-black/30 p-4">
            <h3 className="text-xs font-semibold tracking-[0.18em] text-white/80 uppercase">
              Agent Control API
            </h3>
            <p className="mt-3 text-xs leading-relaxed text-white/70">
              Voice-agent integrations can call{' '}
              <code className="text-white">window.eventVideoPlayer</code> for play, pause,
              setCurrentTime, and seekBy.
            </p>
            <p className="mt-2 text-xs leading-relaxed text-white/70">
              You can also dispatch <code className="text-white">event-video-player:command</code>{' '}
              with commands such as{' '}
              <code className="text-white">{`{ action: 'setCurrentTime', time: 90 }`}</code>.
            </p>
          </div>
        </div>
      )}

      {activeTab === 'moments' && (
        <div className="pt-4">
          <div className="mb-5 flex items-center justify-between gap-2">
            <ul className="space-y-2 text-sm text-white/75">
              <li>Say bookmark this moment to save a timestamp.</li>
              <li>Say take a note then dictate what to remember.</li>
              <li>Tap any saved moment to jump back instantly.</li>
            </ul>
            <button
              type="button"
              onClick={clearAll}
              className="inline-flex h-fit items-center gap-1 rounded-full border border-white/15 bg-black/30 px-3 py-1 text-[11px] tracking-[0.12em] text-white/70 uppercase transition hover:border-white/30 hover:text-white"
            >
              <Trash2 className="size-3.5" />
              Clear
            </button>
          </div>

          <div className="space-y-4">
            <section>
              <h3 className="mb-2 font-mono text-[11px] tracking-[0.16em] text-white/65 uppercase">
                Bookmarks
              </h3>
              <div className="space-y-2">
                {bookmarks.length === 0 ? (
                  <p className="rounded-xl border border-white/10 bg-black/20 p-3 text-xs text-white/55">
                    No bookmarks yet.
                  </p>
                ) : (
                  bookmarks.map((moment) => <MomentItem key={moment.id} moment={moment} />)
                )}
              </div>
            </section>

            <section>
              <h3 className="mb-2 font-mono text-[11px] tracking-[0.16em] text-white/65 uppercase">
                Notes
              </h3>
              <div className="space-y-2">
                {notes.length === 0 ? (
                  <p className="rounded-xl border border-white/10 bg-black/20 p-3 text-xs text-white/55">
                    No notes yet.
                  </p>
                ) : (
                  notes.map((moment) => <MomentItem key={moment.id} moment={moment} />)
                )}
              </div>
            </section>
          </div>
        </div>
      )}
    </aside>
  );
}
