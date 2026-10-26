import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const DEV_API_URL = "http://127.0.0.1:8781";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": DEV_API_URL,
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});
