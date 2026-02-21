import { Outlet } from "react-router";
import { AppNav } from "./AppNav";
import "./AppLayout.css";

export function AppLayout() {
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
