import { headers } from 'next/headers';
import { EventVoiceExperience } from '@/components/video/event-voice-experience';
import { EventMomentsPanel } from '@/components/video/moments-panel';
import { getAppConfig } from '@/lib/utils';
import { PageProps } from '@/types/page-props';

export default async function EventPage({ params }: PageProps) {
  const hdrs = await headers();
  const appConfig = await getAppConfig(hdrs);
  const { slug } = await params;
  const readableTitle = slug
    .split(/[-_]/g)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');

  return (
    <main className="relative min-h-svh overflow-hidden bg-neutral-950 text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_0%,rgba(120,119,198,0.35),transparent_50%),radial-gradient(circle_at_85%_15%,rgba(56,189,248,0.22),transparent_40%),linear-gradient(180deg,#0a0a0a_0%,#09090b_45%,#000_100%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_bottom,rgba(255,255,255,0.08)_1px,transparent_1px)] bg-[size:100%_32px] opacity-20" />

      <section className="relative mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 pt-24 pb-10 sm:px-6 lg:px-8 lg:pt-28">
        <header className="space-y-4">
          <p className="font-mono text-xs tracking-[0.22em] text-white/60 uppercase">Now Playing</p>
          <h1 className="max-w-4xl text-3xl leading-tight font-semibold text-balance md:text-5xl">
            {readableTitle || 'Event Video'}
          </h1>
        </header>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
          <div className="space-y-4">
            <EventVoiceExperience videoId={slug} appConfig={appConfig} />
            <div className="flex flex-wrap items-center gap-2 text-xs text-white/70">
              <span className="rounded-full border border-white/20 bg-white/5 px-3 py-1 font-mono">
                Event
              </span>
              <span className="rounded-full border border-white/20 bg-white/5 px-3 py-1 font-mono">
                Past Recording
              </span>
              <span className="rounded-full border border-white/20 bg-white/5 px-3 py-1 font-mono">
                ID: {slug}
              </span>
            </div>
          </div>

          <EventMomentsPanel videoId={slug} />
        </div>
      </section>
    </main>
  );
}
