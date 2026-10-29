import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import consoleForwardPlugin from "./console-forward-plugin.mjs";

const backend = process.env.VITE_BACKEND_URL || "http://localhost:8000";

export default defineConfig({
	plugins: [react(), tailwindcss(), consoleForwardPlugin()],
	server: {
		proxy: {
			"/api": { target: backend },
			"/ws": { target: backend, ws: true },
			"/auth": { target: backend },
			"/project": { target: backend },
			"/login": { target: backend },
			"/logout": { target: backend },
			"/user": { target: backend },
			"/mcp": { target: backend },
			"/set-session-cookie": { target: backend },
			"/feedback": { target: backend },
			"/logo": { target: backend },
		},
	},
});
