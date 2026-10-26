import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const DEV_API_URL = "http://127.0.0.1:8781";
// The token test compares src/ui/tokens.css with the prototype, which lives outside the app.
const PROTOTYPE_DIR = "../../docs/prototype";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": DEV_API_URL,
    },
    fs: {
      allow: [".", PROTOTYPE_DIR],
    },
  },
  test: {
    environment: "jsdom",
    // The token test reads the stylesheets as text; unprocessed CSS reaches it empty.
    css: true,
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});
