import { redirect } from 'next/navigation';
import { auth, signIn } from '@/auth';

export default async function Page() {
  const session = await auth();

  if (session?.user) {
    redirect('/events');
  }

  return (
    <main className="relative flex min-h-svh items-center justify-center overflow-hidden bg-neutral-950 text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_2%,rgba(96,165,250,0.3),transparent_42%),radial-gradient(circle_at_85%_8%,rgba(244,114,182,0.2),transparent_40%),linear-gradient(180deg,#0a0c12_0%,#07080b_55%,#030303_100%)]" />
      <div className="relative flex flex-col items-center gap-6 rounded-2xl border border-white/12 bg-white/5 px-10 py-12 text-center backdrop-blur-sm">
        <h1 className="text-2xl font-semibold">EVA (Event Voice Agent)</h1>
        <p className="text-sm text-white/60">Sign in to continue</p>
        <form
          action={async () => {
            'use server';
            await signIn('github', { redirectTo: '/events' });
          }}
        >
          <button
            type="submit"
            className="flex items-center gap-3 rounded-xl border border-white/15 bg-white/10 px-6 py-3 text-sm font-medium text-white transition hover:border-white/30 hover:bg-white/20"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.387.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0 1 12 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222 0 1.606-.015 2.896-.015 3.286 0 .322.216.694.825.576C20.565 21.795 24 17.298 24 12c0-6.63-5.37-12-12-12z" />
            </svg>
            Sign in with GitHub
          </button>
        </form>
      </div>
    </main>
  );
}
