import { useContext } from "react";
import { AuthContext, type AuthContextValue, type AuthUser } from "./authTypes";

export type { AuthUser, AuthContextValue };

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
