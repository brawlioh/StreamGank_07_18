/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
    theme: {
        extend: {
            colors: {
                // StreamGank brand colors
                primary: "#1e88e5",
                accent: "#16c784",
                gank: "#16c784",

                // Dark theme colors
                "dark-bg": "#121212",
                "dark-panel": "#1a1a1a",
                "text-light": "#ffffff",
                "text-secondary": "#b0b0b0",
                "border-color": "#333333",

                // Status colors
                success: "#28a745",
                warning: "#ffc107",
                danger: "#dc3545",
                info: "#17a2b8",
            },

            fontFamily: {
                sans: ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Open Sans", "Helvetica Neue", "sans-serif"],
                mono: ["Consolas", "Monaco", "Courier New", "monospace"],
            },

            animation: {
                "fade-in": "fadeIn 0.3s ease-in-out",
                "fade-in-up": "fadeInUp 0.6s ease forwards",
                "pulse-border": "pulseBorder 2s infinite",
                "pulse-status": "pulseStatus 2s infinite",
                shimmer: "shimmer 2s infinite",
                "nav-pulse": "navPulse 2s infinite",
            },

            keyframes: {
                fadeIn: {
                    from: { opacity: "0", transform: "translateY(-10px)" },
                    to: { opacity: "1", transform: "translateY(0)" },
                },
                fadeInUp: {
                    from: { opacity: "0", transform: "translateY(30px)" },
                    to: { opacity: "1", transform: "translateY(0)" },
                },
                pulseBorder: {
                    "0%": { borderLeftColor: "#16c784" },
                    "50%": { borderLeftColor: "#00ff88" },
                    "100%": { borderLeftColor: "#16c784" },
                },
                pulseStatus: {
                    "0%, 100%": { opacity: "1" },
                    "50%": { opacity: "0.7" },
                },
                shimmer: {
                    "0%": { backgroundPosition: "-200% 0" },
                    "100%": { backgroundPosition: "200% 0" },
                },
                navPulse: {
                    "0%": { boxShadow: "0 0 0 0 rgba(255, 255, 255, 0.4)" },
                    "70%": { boxShadow: "0 0 0 8px rgba(255, 255, 255, 0)" },
                    "100%": { boxShadow: "0 0 0 0 rgba(255, 255, 255, 0)" },
                },
            },

            backdropBlur: {
                xs: "2px",
            },

            boxShadow: {
                glow: "0 0 20px rgba(22, 199, 132, 0.3)",
                "glow-hover": "0 0 30px rgba(22, 199, 132, 0.4)",
            },
        },
    },
    plugins: [],
};
