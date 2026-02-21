import { Home, Event, EventGallery, Unauthorised, NotFound } from "./pages";
import { PageLayout } from "./components/layout/PageLayout";
import { AppLayout } from "./components/layout/AppLayout";
import { createBrowserRouter, type LoaderFunctionArgs } from "react-router";
import { apiVideo } from "./apis";
import type { ApiVideoListResponse } from "./apis/api-video/api-video";

export const ROUTES = {
  HOME: "/",
  UNAUTHORISED: "/unauthorised",
  EVENTS: "/events",
  EVENT: "/events/:id",
  NOT_FOUND: "*",
} as const;

export const toEventDetail = (id: string) => `/events/${id}`;

export type EventGalleryLoaderData = ApiVideoListResponse;

async function eventsLoader({ request }: LoaderFunctionArgs): Promise<EventGalleryLoaderData> {
  const url = new URL(request.url);
  const page = Math.max(1, Number(url.searchParams.get("page") ?? 1));
  const q = url.searchParams.get("q")?.trim() || undefined;
  return apiVideo.listPage(page, undefined, q);
}

export const router = createBrowserRouter([
  {
    Component: PageLayout,
    children: [
      {
        path: ROUTES.HOME,
        Component: Home,
      },
      {
        path: ROUTES.UNAUTHORISED,
        Component: Unauthorised,
      },
      {
        Component: AppLayout,
        children: [
          {
            path: ROUTES.EVENTS,
            loader: eventsLoader,
            Component: EventGallery,
          },
          {
            path: ROUTES.EVENT,
            Component: Event,
          },
        ],
      },
      {
        path: ROUTES.NOT_FOUND,
        Component: NotFound,
      },
    ],
  },
]);
