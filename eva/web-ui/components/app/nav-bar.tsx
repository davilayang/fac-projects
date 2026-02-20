import Image from 'next/image';
import { signOut } from '@/auth';

interface NavBarProps {
  user: {
    name?: string | null;
    email?: string | null;
    image?: string | null;
  };
}

export function NavBar({ user }: NavBarProps) {
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-white/10 bg-neutral-900 backdrop-blur-md">
      <div className="mx-auto flex h-18 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <span className="font-mono text-sm font-medium tracking-wide text-white/80">
          EVA (Event Voice Agent)
        </span>

        <div className="flex items-center gap-8">
          <div className="flex items-center gap-4">
            {user.image && (
              <Image
                src={user.image}
                alt={user.name ?? 'User avatar'}
                width={36}
                height={36}
                className="rounded-full ring-1 ring-white/20"
              />
            )}
            <span className="text-base font-semibold text-white">{user.name ?? user.email}</span>
          </div>

          <form
            action={async () => {
              'use server';
              await signOut({ redirectTo: '/' });
            }}
          >
            <button
              type="submit"
              className="rounded-lg border border-white/12 bg-white/5 px-3 py-1.5 text-xs text-white/60 transition hover:border-white/25 hover:bg-white/10 hover:text-white/90"
            >
              Sign out
            </button>
          </form>
        </div>
      </div>
    </header>
  );
}
