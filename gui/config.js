/**
 * StreamGank GUI Configuration for Railway Deployment
 *
 * This file contains configuration for connecting the GUI to the Railway backend API.
 * The configuration automatically detects the environment and sets the correct API URL.
 */

// Backend API Configuration for Railway Deployment
const STREAMGANK_CONFIG = {
    // Backend API URL Configuration
    //
    // For different deployment scenarios:
    //
    // 1. Local Development:
    //    BACKEND_API_URL: 'http://localhost:8000'
    //
    // 2. Netlify Frontend + Railway Backend (PRODUCTION):
    //    BACKEND_API_URL: 'https://your-app-name.railway.app'
    //
    // 3. Custom Domain:
    //    BACKEND_API_URL: 'https://api.streamgank.com'

    // 🚀 RAILWAY DEPLOYMENT - Replace with your actual Railway URL
    BACKEND_API_URL: 'https://YOUR-ACTUAL-RAILWAY-URL.railway.app', // Replace with your Railway app URL

    // Environment-based auto-detection
    AUTO_DETECT: true, // Set to false to force specific BACKEND_API_URL above

    // Debug logging
    DEBUG: true, // Set to false in production to reduce console logs
};

// Auto-detection logic for different environments
if (STREAMGANK_CONFIG.AUTO_DETECT) {
    const hostname = window.location.hostname;

    if (hostname.includes('netlify.app') || hostname.includes('netlify.com')) {
        // Netlify deployment - use Railway backend
        STREAMGANK_CONFIG.BACKEND_API_URL = 'https://YOUR-ACTUAL-RAILWAY-URL.railway.app'; // Replace with your Railway URL

        if (STREAMGANK_CONFIG.DEBUG) {
            console.log('🌐 Netlify deployment detected - using Railway backend');
        }
    } else if (hostname === 'localhost' || hostname === '127.0.0.1') {
        // Local development - check if Railway is available, fallback to local
        STREAMGANK_CONFIG.BACKEND_API_URL = 'http://localhost:8000';

        if (STREAMGANK_CONFIG.DEBUG) {
            console.log('🏠 Local development detected - using local backend');
        }
    } else if (hostname.includes('streamgank.com')) {
        // Production domain - use Railway backend
        STREAMGANK_CONFIG.BACKEND_API_URL = 'https://YOUR-ACTUAL-RAILWAY-URL.railway.app'; // Replace with your Railway URL

        if (STREAMGANK_CONFIG.DEBUG) {
            console.log('🌍 Production domain detected - using Railway backend');
        }
    }
    // For other domains, use the configured BACKEND_API_URL
}

// Make config globally available
window.STREAMGANK_CONFIG = STREAMGANK_CONFIG;

if (STREAMGANK_CONFIG.DEBUG) {
    console.log('🔧 StreamGank Configuration:', {
        backendUrl: STREAMGANK_CONFIG.BACKEND_API_URL,
        autoDetect: STREAMGANK_CONFIG.AUTO_DETECT,
        hostname: window.location.hostname,
        environment: hostname.includes('netlify') ? 'Netlify' : hostname === 'localhost' ? 'Local' : hostname.includes('streamgank.com') ? 'Production' : 'Custom',
    });
}
