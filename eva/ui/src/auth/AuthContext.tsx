import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";

export interface AuthUser {
  id: string;
  login: string;
  name: string | null;
  email: string | null;
  avatarUrl: string | null;
}

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  user: AuthUser | null;
  status: AuthStatus;
  signIn: () => void;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  // On mount, verify the httpOnly JWT cookie and hydrate user state.
  // This is one request per page load — the server just runs jwt.verify(), no I/O.
  useEffect(() => {
    fetch("/auth/session", { credentials: "include" })
      .then((res) => (res.ok ? res.json() : null))
      .then((data: { user: AuthUser } | null) => {
        setUser(data?.user ?? null);
        setStatus(data?.user ? "authenticated" : "unauthenticated");
      })
      .catch(() => setStatus("unauthenticated"));
  }, []);

  const signIn = useCallback(() => {
    window.location.href = "/auth/github/login";
  }, []);

  const signOut = useCallback(async () => {
    await fetch("/auth/logout", { method: "POST", credentials: "include" });
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  return (
    <AuthContext value={{ user, status, signIn, signOut }}>
      {children}
    </AuthContext>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
