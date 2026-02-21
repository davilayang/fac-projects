import passport from "passport";
import { Strategy as GitHubStrategy } from "passport-github2";

export interface GitHubUser {
  id: string;
  login: string;
  name: string | null;
  email: string | null;
  avatarUrl: string | null;
}

const ALLOWED_EMAILS = (process.env.ALLOWED_EMAILS ?? "")
  .split(",")
  .map((e) => e.trim())
  .filter(Boolean);

passport.use(
  new GitHubStrategy(
    {
      clientID: process.env.AUTH_GITHUB_ID!,
      clientSecret: process.env.AUTH_GITHUB_SECRET!,
      callbackURL: process.env.AUTH_CALLBACK_URL!,
      scope: ["user:email"],
    },
    (_accessToken, _refreshToken, profile, done) => {
      const email =
        profile.emails?.find((e) => e.value)?.value ?? null;

      if (ALLOWED_EMAILS.length > 0 && !ALLOWED_EMAILS.includes(email ?? "")) {
        return done(null, false, { message: "unauthorised" });
      }

      const user: GitHubUser = {
        id: profile.id,
        login: profile.username ?? profile.id,
        name: profile.displayName ?? null,
        email,
        avatarUrl: profile.photos?.[0]?.value ?? null,
      };

      return done(null, user);
    }
  )
);

// Serialize the whole user object into the session cookie — no DB needed
passport.serializeUser((user, done) => done(null, user));
passport.deserializeUser((user, done) => done(null, user as GitHubUser));

export default passport;
