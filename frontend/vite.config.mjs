import { join } from "node:path";
import { tmpdir } from "node:os";

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  cacheDir: join(tmpdir(), "ai-agent-lab-vite-cache"),
  plugins: [react()],
});
