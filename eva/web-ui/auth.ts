import NextAuth from 'next-auth';
import GitHub from 'next-auth/providers/github';

const ALLOWED_EMAILS = [
  'cy.yang@apolitical.co',
  'duckduckyang@duck.com',
  'rihards.jukna@apolitical.co',
  'rihards.dev@pm.me',
];

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [GitHub],
  pages: {
    error: '/unauthorised',
  },
  callbacks: {
    signIn({ user }) {
      console.log(user);
      return ALLOWED_EMAILS.includes(user.email ?? '');
    },
  },
});
