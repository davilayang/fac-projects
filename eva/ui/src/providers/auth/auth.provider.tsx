"use client";

import { useState, useEffect, useCallback, type ReactNode } from "react";
import { AuthContext, type AuthUser } from "./auth.types";
import { AUTH_API } from "./auth.constants";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<
    "loading" | "authenticated" | "unauthenticated"
  >("loading");

  // On mount, verify the httpOnly JWT cookie and hydrate user state.
  // This is one request per page load — the server just runs jwt.verify(), no I/O.
  useEffect(() => {
    fetch(AUTH_API.SESSION, { credentials: "include" })
      .then((res) => (res.ok ? res.json() : null))
      .then((data: { user: AuthUser } | null) => {
        setUser(data?.user ?? null);
        setStatus(data?.user ? "authenticated" : "unauthenticated");
      })
      .catch(() => setStatus("unauthenticated"));
  }, []);

  const signIn = useCallback(() => {
    window.location.href = AUTH_API.LOGIN;
  }, []);

  const signOut = useCallback(async () => {
    await fetch(AUTH_API.LOGOUT, { method: "POST", credentials: "include" });
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  return (
    <AuthContext value={{ user, status, signIn, signOut }}>
      {children}
    </AuthContext>
  );
}
