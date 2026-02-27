import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router/dom";

import "hls-video-element";

import { AuthProvider, AgentSessionProvider } from "@eva-providers";
import { router } from "@eva-router";

import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <AgentSessionProvider>
        <RouterProvider router={router} />
      </AgentSessionProvider>
    </AuthProvider>
  </StrictMode>,
);
