import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter } from "react-router";
import { RouterProvider } from "react-router/dom";

import "./index.css";
import { Home, Event, EventGallery } from "./pages";
import { PageLayout } from "./components/layout/PageLayout";
import { AppLayout } from "./components/layout/AppLayout";
import { AuthProvider } from "./auth/AuthContext";

const router = createBrowserRouter([
  {
    Component: PageLayout,
    children: [
      {
        path: "/",
        Component: Home,
      },
      {
        Component: AppLayout,
        children: [
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
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  </StrictMode>,
);
