import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [
      react({
        // Disable Fast Refresh to avoid additional dev re-renders that could trigger duplicate requests
        fastRefresh: false,
      }),
    ],
    define: {
      __APP_VERSION__: JSON.stringify(env.npm_package_version ?? "dev"),
    },
    server: {
      port: Number(env.FRONTEND_PORT ?? 5173),
      host: env.FRONTEND_HOST ?? "0.0.0.0",
    },
  };
});
