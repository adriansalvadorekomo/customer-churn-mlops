// @ts-check
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";

// Static multi-page build (intake / ledger / report), served by nginx in
// Docker. The backend URL is baked in at build time via PUBLIC_API_URL
// (see Dockerfile: default http://localhost:8000).
export default defineConfig({
  server: { host: true, port: 4321 },
  vite: { plugins: [tailwindcss()] },
});
