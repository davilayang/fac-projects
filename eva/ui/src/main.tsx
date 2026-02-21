import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter } from "react-router";
import { RouterProvider } from "react-router/dom";

import "./index.css";
import { Home, Event, EventGallery } from "./pages";
import { PageLayout } from "./components/layout/PageLayout";

const router = createBrowserRouter([
  {
    Component: PageLayout,
    children: [
      {
        path: "/",
        Component: Home,
      },
      {
        path: "events",
        Component: EventGallery,
      },
      {
        path: "events/:id",
        Component: Event,
      },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
