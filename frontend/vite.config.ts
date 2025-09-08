import { defineConfig } from "vite";
import { resolve } from "path";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig(() => {
    return {
        plugins: [react()],

        // CSS processing with PostCSS for Tailwind v4
        css: {
            postcss: "./postcss.config.mjs",
        },

        // Path aliases
        resolve: {
            alias: {
                "@": resolve(__dirname, "./src"),
                "@/components": resolve(__dirname, "./src/components"),
                "@/services": resolve(__dirname, "./src/services"),
                "@/pages": resolve(__dirname, "./src/pages"),
                "@/utils": resolve(__dirname, "./src/utils"),
                "@/types": resolve(__dirname, "./src/types"),
            },
        },

        // Development server configuration
        server: {
            port: 3000,
            host: true,
            // NO PROXY - Frontend uses VITE_BACKEND_URL directly
            // Proxy disabled for production deployment
        },

        // Build configuration
        build: {
            outDir: "dist",
            sourcemap: true,
            // Optimize for production
            rollupOptions: {
                output: {
                    manualChunks: {
                        vendor: ["react", "react-dom"],
                        router: ["react-router-dom"],
                        api: ["axios"],
                    },
                },
            },
        },

        // Pass ONLY safe, non-sensitive variables to frontend
        define: {
            // Frontend-specific variables (safe for client-side)
            "import.meta.env.VITE_BACKEND_URL": JSON.stringify(process.env.VITE_BACKEND_URL),

            // Non-sensitive configuration
            "process.env.NODE_ENV": JSON.stringify(process.env.NODE_ENV),
            "process.env.APP_ENV": JSON.stringify(process.env.APP_ENV),
            "process.env.WEBHOOK_BASE_URL": JSON.stringify(process.env.WEBHOOK_BASE_URL),
            "process.env.WEBHOOK_CREATOMATE_URL": JSON.stringify(process.env.WEBHOOK_CREATOMATE_URL),
        },
    };
});
