import { defineConfig } from "vite";
import { resolve } from "path";

// Try to import React plugin, fallback if not available
let react: any;
try {
    react = require("@vitejs/plugin-react").default;
} catch (e) {
    console.warn("@vitejs/plugin-react not found, building without React plugin");
    react = () => ({});
}

// https://vite.dev/config/
export default defineConfig({
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

    // NO HARDCODED ENVIRONMENT VARIABLES
    // All URLs come from .env file via VITE_BACKEND_URL
});
