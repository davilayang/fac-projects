import { Outlet } from "react-router";
import "./PageLayout.css";

export function PageLayout() {
  return (
    <div className="app">
      <div className="app__bg" aria-hidden="true" />
      <div className="app__grid" aria-hidden="true" />
      <div className="app__content">
        <Outlet />
      </div>
    </div>
  );
}
