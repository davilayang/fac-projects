import { createContext } from "react";

export interface AuthUser {
  id: string;
  login: string;
  name: string | null;
  email: string | null;
  avatarUrl: string | null;
}

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface AuthContextValue {
  user: AuthUser | null;
  status: AuthStatus;
  signIn: () => void;
  signOut: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
