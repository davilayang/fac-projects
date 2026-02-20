import Link from 'next/link';
import { listApiVideoVideos } from '@/lib/api-video';

type EventGalleryItem = {
  slug: string;
  title: string;
  meta: string;
  category: string;
  accent: string;
  subline: string;
  thumbnail?: string;
};

const ACCENTS = [
  'from-cyan-400/45 to-blue-500/20',
  'from-emerald-400/40 to-teal-500/20',
  'from-amber-400/40 to-orange-500/20',
  'from-fuchsia-400/35 to-pink-500/20',
  'from-indigo-400/40 to-blue-600/20',
  'from-sky-400/40 to-cyan-600/20',
];

function formatDateLabel(value?: string) {
  if (!value) {
    return 'Unpublished';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return 'Unpublished';
  }

  return parsed.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

async function getGalleryItems(): Promise<EventGalleryItem[]> {
  try {
    const videos = await listApiVideoVideos({ pageSize: 100, maxPages: 5 });
    return videos.map((video, index) => ({
      slug: video.videoId,
      title: video.title?.trim() || `Video ${video.videoId}`,
      meta: formatDateLabel(video.publishedAt ?? video.updatedAt),
      category: video.tags?.[0] || 'Event',
      accent: ACCENTS[index % ACCENTS.length],
      subline: video.description?.trim() || `ID: ${video.videoId}`,
      thumbnail: video.assets?.thumbnail,
    }));
  } catch (error) {
    console.error('Failed to load api.video videos', error);
    return [];
  }
}

export default async function EventsGalleryPage() {
  const events = await getGalleryItems();

  if (events.length === 0) {
    return (
      <main className="relative min-h-svh overflow-hidden bg-neutral-950 text-white">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_2%,rgba(96,165,250,0.3),transparent_42%),radial-gradient(circle_at_85%_8%,rgba(244,114,182,0.2),transparent_40%),linear-gradient(180deg,#0a0c12_0%,#07080b_55%,#030303_100%)]" />
        <section className="relative mx-auto w-full max-w-5xl px-4 pt-24 pb-12 sm:px-6 lg:px-8">
          <div className="rounded-3xl border border-white/15 bg-white/5 p-8 text-center backdrop-blur-sm">
            <h1 className="text-3xl font-semibold">Events</h1>
            <p className="mt-3 text-white/70">
              No videos were returned from api.video. Check `APIVIDEO_API_KEY` and workspace
              content.
            </p>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="relative min-h-svh overflow-hidden bg-neutral-950 text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_2%,rgba(96,165,250,0.3),transparent_42%),radial-gradient(circle_at_85%_8%,rgba(244,114,182,0.2),transparent_40%),linear-gradient(180deg,#0a0c12_0%,#07080b_55%,#030303_100%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_bottom,rgba(255,255,255,0.04)_1px,transparent_1px)] bg-[size:100%_34px] opacity-25" />

      <section className="relative mx-auto w-full max-w-7xl px-4 pt-20 pb-12 sm:px-6 lg:px-8 lg:pt-24">
        <header className="mb-8">
          <p className="font-mono text-xs tracking-[0.22em] text-white/55 uppercase">Library</p>
          <h1 className="mt-2 text-3xl leading-tight font-semibold md:text-5xl">Events</h1>
        </header>

        <div className="grid grid-cols-2 gap-9">
          {events.map((event) => (
            <Link
              key={event.slug}
              href={`/events/${event.slug}`}
              className="group overflow-hidden rounded-2xl border border-white/12 bg-white/5 transition hover:border-white/30"
            >
              <div className={`relative aspect-[16/10] bg-gradient-to-br ${event.accent}`}>
                {event.thumbnail && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={event.thumbnail}
                    alt={event.title}
                    className="absolute inset-0 h-full w-full object-cover"
                  />
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/30 to-transparent" />
                <div className="absolute right-3 bottom-3 rounded-full border border-white/20 bg-black/45 px-2 py-0.5 font-mono text-[10px] tracking-[0.08em] text-white/85 uppercase">
                  {event.meta}
                </div>
              </div>
              <div className="p-4">
                {/*<h2 className="line-clamp-2 text-base font-semibold text-white group-hover:text-cyan-200">
                </h2>*/}
                <p className="mt-1 line-clamp-2 text-xs text-white/60">{event.title}</p>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
