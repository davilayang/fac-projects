import { Navigate, Outlet } from "react-router";
import { useAuth } from "../../auth/useAuth";
import { ROUTES } from "../../router";
import { AppNav } from "./AppNav";
import "./AppLayout.css";

export function AppLayout() {
  const { user, status } = useAuth();

  if (status === "loading") return null;

  if (!user) {
    return <Navigate to={ROUTES.HOME} replace />;
  }

  return (
    <>
      <AppNav />
      <main className="app-layout">
        <div className="app-layout__content">
          <Outlet />
        </div>
      </main>
    </>
  );
}
