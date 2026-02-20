import { redirect } from 'next/navigation';
import { auth } from '@/auth';
import { NavBar } from '@/components/app/nav-bar';

interface AppLayoutProps {
  children: React.ReactNode;
}

export default async function AppLayout({ children }: AppLayoutProps) {
  const session = await auth();

  if (!session?.user) {
    redirect('/');
  }

  return (
    <>
      <NavBar user={session.user} />
      {children}
    </>
  );
}
