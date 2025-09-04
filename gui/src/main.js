/**
 * StreamGank Video Generator - Main App
 * Simple, Clean, Working SPA
 */

import Router from './core/Router.js';
import { DashboardPage } from './pages/Dashboard.js';
import { JobDetailPage } from './pages/JobDetail.js';
import { QueuePage } from './pages/QueuePage.js';

/**
 * Main App Class
 */
class StreamGankApp {
    constructor() {
        this.currentPage = null;
        console.log('🔧 StreamGankApp created');
    }

    /**
     * Initialize the app
     */
    async init() {
        console.log('🚀 Initializing StreamGank App...');

        try {
            // Setup routing
            this.setupRoutes();

            // Start router
            Router.start();

            console.log('✅ App initialized successfully');
        } catch (error) {
            console.error('❌ App initialization failed:', error);
        }
    }

    /**
     * Setup all routes
     */
    setupRoutes() {
        console.log('🛤️ Setting up routes...');

        // Job detail route (most specific first)
        Router.addRoute('/job/:jobId', (params) => {
            console.log('🎯 Job route matched:', params);
            this.renderJobDetail(params.jobId);
        });

        // Queue route
        Router.addRoute('/queue', () => {
            console.log('🎯 Queue route');
            this.renderQueue();
        });

        // Dashboard route
        Router.addRoute('/dashboard', () => {
            console.log('🎯 Dashboard route');
            this.renderDashboard();
        });

        // Root route
        Router.addRoute('/', () => {
            console.log('🎯 Root route');
            this.renderDashboard();
        });

        console.log('✅ Routes setup complete');
    }

    /**
     * Get main content container
     */
    getMainContainer() {
        return document.querySelector('.main-content') || document.body;
    }

    /**
     * Render dashboard page
     */
    renderDashboard() {
        console.log('🎨 Rendering Dashboard');

        // Dashboard uses the existing HTML content - just activate it
        // Don't pass container since Dashboard.render() doesn't need it
        const dashboard = new DashboardPage();
        dashboard.render();
        dashboard.activate();

        // Update navigation
        this.updateNavigation('/dashboard');

        this.currentPage = 'dashboard';
    }

    /**
     * Render queue page
     */
    async renderQueue() {
        console.log('🎨 Rendering Queue');

        const container = this.getMainContainer();

        // Create queue instance
        const queue = new QueuePage();
        await queue.render(container);
        queue.activate();

        // Update navigation
        this.updateNavigation('/queue');

        this.currentPage = 'queue';
    }

    /**
     * Render job detail page
     */
    async renderJobDetail(jobId) {
        console.log('🎨 Rendering Job Detail:', jobId);

        if (!jobId) {
            console.error('❌ No jobId provided');
            Router.navigate('/dashboard');
            return;
        }

        const container = this.getMainContainer();

        // Create job detail instance
        const jobDetail = new JobDetailPage();
        await jobDetail.render(container, { jobId });
        jobDetail.activate({ jobId });

        // Update navigation
        this.updateNavigation(`/job/${jobId}`);

        this.currentPage = 'jobDetail';
    }

    /**
     * Update navigation active states
     */
    updateNavigation(currentPath) {
        // Remove all active states
        document.querySelectorAll('.nav-link').forEach((link) => {
            link.classList.remove('active');
        });

        // Add active state to current route
        if (currentPath.startsWith('/job/')) {
            // No specific nav item for job details
            return;
        }

        const navLink = document.querySelector(`[data-route="${currentPath}"]`);
        if (navLink) {
            navLink.classList.add('active');
        }
    }
}

// Initialize app when DOM is ready
console.log('🚀 Main.js loaded');

const app = new StreamGankApp();

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        app.init();
    });
} else {
    app.init();
}

// Global access for debugging
window.StreamGankApp = app;
window.Router = Router;

export default app;
