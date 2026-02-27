import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@eva-configs": resolve(__dirname, "src/configs"),
      "@eva-elements": resolve(__dirname, "src/components/elements"),
      "@eva-icons": resolve(__dirname, "src/components/icons"),
      "@eva-providers": resolve(__dirname, "src/providers"),
      "@eva-router": resolve(__dirname, "src/router.ts"),
    },
  },
  server: {
    proxy: {
      "/auth": {
        target: "http://localhost:4000",
        changeOrigin: true,
      },
    },
  },
});
