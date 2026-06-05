import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy /chat and /memories to Person 1's backend when USE_MOCK=false
      "/chat":     "http://localhost:8000",
      "/memories": "http://localhost:8000",
    },
  },
});
