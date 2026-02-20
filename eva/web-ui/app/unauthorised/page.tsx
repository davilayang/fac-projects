import Link from 'next/link';

export default function UnauthorisedPage() {
  return (
    <main className="relative flex min-h-svh items-center justify-center overflow-hidden bg-neutral-950 text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_2%,rgba(96,165,250,0.3),transparent_42%),radial-gradient(circle_at_85%_8%,rgba(244,114,182,0.2),transparent_40%),linear-gradient(180deg,#0a0c12_0%,#07080b_55%,#030303_100%)]" />
      <div className="relative flex flex-col items-center gap-4 rounded-2xl border border-white/12 bg-white/5 px-10 py-12 text-center backdrop-blur-sm">
        <h1 className="text-2xl font-semibold">Access denied</h1>
        <p className="max-w-xs text-sm text-white/60">
          Your account is not authorised to use this application. Contact the administrator to
          request access.
        </p>
        <Link
          href="/"
          className="mt-2 text-xs text-white/40 underline underline-offset-4 hover:text-white/70"
        >
          Back to sign in
        </Link>
      </div>
    </main>
  );
}
