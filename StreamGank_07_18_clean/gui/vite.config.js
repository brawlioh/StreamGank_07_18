import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
    // Entry point configuration
    build: {
        outDir: 'dist',
        rollupOptions: {
            input: {
                main: resolve(__dirname, 'index.html'),
                'job-detail-app': resolve(__dirname, 'src/job-detail-app.js')
            },
            output: {
                entryFileNames: (chunkInfo) => {
                    // Keep job-detail-app filename consistent for direct loading
                    if (chunkInfo.name === 'job-detail-app') {
                        return 'js/job-detail-app.js';
                    }
                    return 'js/[name].[hash].js';
                },
                chunkFileNames: 'js/[name].[hash].js',
                assetFileNames: (assetInfo) => {
                    if (assetInfo.name && assetInfo.name.endsWith('.css')) {
                        return 'css/[name].[hash].[ext]';
                    }
                    return 'assets/[name].[hash].[ext]';
                }
            }
        },
        // Enable source maps for debugging
        sourcemap: true,
        // Use esbuild for faster minification (built into Vite)
        minify: 'esbuild'
    },

    // Development server configuration
    server: {
        port: 3001,
        host: 'localhost',
        open: false
    },

    // Preview server configuration
    preview: {
        port: 3002,
        host: 'localhost'
    },

    // Base public path
    base: './',

    // Define global constants
    define: {
        'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development')
    },

    // Optimize dependencies
    optimizeDeps: {
        include: ['axios']
    }
});
