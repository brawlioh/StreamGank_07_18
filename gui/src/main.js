/**
 * StreamGank Video Generator - Professional Modular Frontend
 * Main Application Entry Point
 *
 * This is the core orchestrator that initializes and coordinates all modules:
 * - DOM Management (Element caching and manipulation)
 * - API Communication (HTTP client with caching and retry logic)
 * - Real-time Updates (SSE with polling fallback)
 * - Job Management (Video generation lifecycle)
 * - UI Management (Status messages, progress, video display)
 * - Form Management (Validation, dynamic updates, preview)
 */

// Main entry point - modular system loading

// Core modules
import DOMManager from './core/DOMManager.js';
import Router from './core/Router.js';

// Service modules
import APIService from './services/APIService.js';
import RealtimeService from './services/RealtimeService.js';
import JobManager from './services/JobManager.js';

// Component modules
import UIManager from './components/UIManager.js';
import FormManager from './components/FormManager.js';
import ProcessTable from './components/ProcessTable.js';
import Navigation from './components/Navigation.js';

// Page modules
import DashboardPage from './pages/Dashboard.js';
import JobDetailPage from './pages/JobDetail.js';

/**
 * Main Application Class - Orchestrates all modules
 */
class StreamGankApp {
    constructor() {
        this.isInitialized = false;
        this.currentPage = null;
        this.appContainer = null;
        this.modules = {
            dom: DOMManager,
            router: Router,
            api: APIService,
            realtime: RealtimeService,
            jobs: JobManager,
            ui: UIManager,
            form: FormManager,
            navigation: Navigation
        };
        this.pages = {
            dashboard: DashboardPage,
            jobDetail: JobDetailPage
        };
    }

    /**
     * Initialize the entire application
     */
    async init() {
        if (this.isInitialized) {
            console.warn('⚠️ App already initialized');
            return;
        }

        try {
            // Phase 1: Initialize core systems
            await this.initializeCore();

            // Phase 2: Setup application container
            this.setupAppContainer();

            // Phase 3: Initialize routing system
            this.setupRouting();

            // Phase 4: Initialize services
            await this.initializeServices();

            // Phase 5: Initialize components
            await this.initializeComponents();

            // Phase 6: Setup cross-module event handlers
            this.setupEventHandlers();

            // Phase 7: Start routing and real-time services
            this.startServices();

            this.isInitialized = true;

            // Application is ready - no need for status message spam
        } catch (error) {
            console.error('❌ Failed to initialize app:', error);
            this.handleInitializationError(error);
        }
    }

    /**
     * Phase 1: Initialize core systems
     */
    async initializeCore() {
        // Initialize DOM manager (must be first)
        DOMManager.init();
    }

    /**
     * Phase 2: Setup application container
     */
    setupAppContainer() {
        // Use the existing HTML structure - DON'T replace it
        this.appContainer = document.body;

        // Find existing main content area or use body
        this.mainContent =
            document.querySelector('.main-content') || document.querySelector('.container-fluid') || this.appContainer;
    }

    /**
     * Phase 3: Setup routing system
     */
    setupRouting() {
        // Define routes
        Router.addRoute('/', () => this.renderPage('dashboard'), {
            title: 'Dashboard - StreamGank Video Generator'
        });

        Router.addRoute('/dashboard', () => this.renderPage('dashboard'), {
            title: 'Dashboard - StreamGank Video Generator'
        });

        Router.addRoute('/job/:jobId', (params) => this.renderPage('jobDetail', params), {
            title: 'Job Details - StreamGank Video Generator'
        });

        Router.addRoute('/jobs', () => this.renderJobsPage(), {
            title: 'All Jobs - StreamGank Video Generator'
        });

        // Setup router event handlers
        Router.addEventListener('routeChange', (event) => {});

        Router.addEventListener('notFound', (event) => {
            console.warn(`🛤️ Route not found: ${event.detail.path}`);
            // Redirect to dashboard for unknown routes
            Router.navigate('/dashboard', { replace: true });
        });
    }

    /**
     * Phase 4: Initialize services
     */
    async initializeServices() {
        // API Service is ready by default (no async init needed)

        // Initialize Job Manager
        JobManager.init();
    }

    /**
     * Phase 5: Initialize components
     */
    async initializeComponents() {
        // Initialize Navigation Component
        Navigation.init();

        // Initialize Process Table Component
        await ProcessTable.init();

        // Initialize page components
        DashboardPage.init();

        // JobDetail page initialized when needed
    }

    /**
     * Phase 4: Setup cross-module event handlers
     */
    setupEventHandlers() {
        // Form submission -> Job creation (only for dashboard page)
        document.addEventListener('formSubmit', (event) => {
            this.handleFormSubmission(event.detail);
        });

        // Job events -> UI updates
        JobManager.addEventListener('jobStarted', (event) => {
            console.log('💼 Job started:', event.detail.job.id);
        });

        JobManager.addEventListener('jobCompleted', (event) => {
            console.log('✅ Job completed:', event.detail.job.id);
        });

        JobManager.addEventListener('jobFailed', (event) => {
            console.error('❌ Job failed:', event.detail.job.id, event.detail.error);
        });

        // Realtime connection events
        RealtimeService.addEventListener('connected', (event) => {
            console.log('📡 Real-time connection established:', event.detail.type);

            // Update navigation status
            Navigation.updateStatus({
                connected: true,
                connectionType: event.detail.type
            });
        });

        RealtimeService.addEventListener('disconnected', (event) => {
            console.warn('📡 Real-time connection lost:', event.detail.type);

            // Update navigation status
            Navigation.updateStatus({
                connected: false,
                connectionType: event.detail.type
            });
        });

        RealtimeService.addEventListener('queueUpdate', (event) => {
            // Update navigation with queue info
            Navigation.updateStatus({
                connected: true,
                queue: event.detail.stats
            });
        });

        // Navigation refresh requests
        window.addEventListener('nav-refresh-requested', () => {
            RealtimeService.refreshStatus();
        });

        // Setup navigation event handlers
        Navigation.setupEventHandlers();
    }

    /**
     * Setup button event handlers
     */
    setupButtonHandlers() {
        // Refresh queue status button
        const refreshQueueBtn = DOMManager.get('refreshQueueBtn');
        if (refreshQueueBtn) {
            refreshQueueBtn.addEventListener('click', () => {
                RealtimeService.refreshStatus();
            });
        }

        // Clear queue button
        const clearQueueBtn = DOMManager.get('clearQueueBtn');
        if (clearQueueBtn) {
            clearQueueBtn.addEventListener('click', async () => {
                if (confirm('Are you sure you want to clear the entire queue? This will cancel all pending jobs.')) {
                    try {
                        const result = await APIService.clearQueue();

                        if (result.success) {
                            UIManager.addStatusMessage('success', '✅', 'Queue cleared successfully');
                        } else {
                            UIManager.addStatusMessage('error', '❌', 'Failed to clear queue');
                        }
                    } catch (error) {
                        UIManager.addStatusMessage('error', '❌', `Error clearing queue: ${error.message}`);
                    }
                }
            });
        }

        // Check status button (for manual Creatomate status check)
        const checkStatusBtn = DOMManager.get('checkStatusBtn');
        if (checkStatusBtn) {
            checkStatusBtn.addEventListener('click', () => {
                this.handleManualStatusCheck();
            });
        }

        // Load video button (for manual video loading)
        const loadVideoBtn = DOMManager.get('loadVideoBtn');
        if (loadVideoBtn) {
            loadVideoBtn.addEventListener('click', () => {
                this.handleManualVideoLoad();
            });
        }
    }

    /**
     * Phase 7: Start routing and real-time services
     */
    startServices() {
        // Initialize Router (must be after routes are defined)
        Router.init();

        // Initialize real-time connection (SSE with polling fallback)
        RealtimeService.init();
    }

    // === Page Rendering Methods ===

    /**
     * Render a page (activate page without replacing HTML)
     * @param {string} pageName - Name of the page to render
     * @param {Object} params - Route parameters
     */
    async renderPage(pageName, params = {}) {
        try {
            // Deactivate current page
            if (this.currentPage && this.pages[this.currentPage]) {
                if (typeof this.pages[this.currentPage].deactivate === 'function') {
                    this.pages[this.currentPage].deactivate();
                }
            }

            // For dashboard, just activate the existing functionality
            if (pageName === 'dashboard') {
                // Initialize UI and Form managers with existing DOM
                UIManager.init();
                await FormManager.init();

                // Expose FormManager for debugging
                window.FormManager = FormManager;

                // Activate dashboard functionality
                if (this.pages[pageName] && typeof this.pages[pageName].activate === 'function') {
                    this.pages[pageName].activate(params);
                }

                this.currentPage = pageName;
            } else if (pageName === 'jobDetail') {
                // For job detail, render in a modal or dedicated container
                await this.renderJobDetailPage(params);
                this.currentPage = pageName;
            } else {
                throw new Error(`Page '${pageName}' not found`);
            }
        } catch (error) {
            console.error(`🎨 Failed to render page '${pageName}':`, error);
            alert(`Error: ${error.message}`);
        }
    }

    /**
     * Render job detail in a modal or overlay
     * @param {Object} params - Route parameters
     */
    async renderJobDetailPage(params) {
        const { jobId } = params;

        // Create modal overlay for job details
        const modalHtml = `
            <div class="modal fade" id="jobDetailModal" tabindex="-1" aria-labelledby="jobDetailModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="jobDetailModalLabel">Job ${jobId}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body" id="jobDetailContent">
                            <div class="text-center py-4">
                                <div class="spinner-border" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <p class="mt-3">Loading job details...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add modal to DOM if it doesn't exist
        let modal = document.getElementById('jobDetailModal');
        if (!modal) {
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            modal = document.getElementById('jobDetailModal');
        }

        // Show modal
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();

        // Load job detail content
        try {
            const contentDiv = document.getElementById('jobDetailContent');
            if (this.pages.jobDetail && typeof this.pages.jobDetail.render === 'function') {
                await this.pages.jobDetail.render(contentDiv, params);
            }
        } catch (error) {
            console.error('Failed to load job details:', error);
            document.getElementById('jobDetailContent').innerHTML = `
                <div class="alert alert-danger">
                    <h6>Error</h6>
                    <p>Failed to load job details: ${error.message}</p>
                </div>
            `;
        }

        // Handle modal close - go back to dashboard
        modal.addEventListener('hidden.bs.modal', () => {
            Router.navigate('/dashboard');
        });
    }

    /**
     * Render jobs list page (simple implementation)
     */
    renderJobsPage() {
        const appContent = document.getElementById('app-content');
        if (!appContent) return;

        appContent.innerHTML = `
            <div class="jobs-page">
                <div class="container-fluid">
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <h1 class="h3">All Jobs</h1>
                        <div class="nav-links">
                            <a href="/dashboard" class="btn btn-outline-primary me-2">Dashboard</a>
                        </div>
                    </div>
                    
                    <div class="alert alert-info">
                        <h4 class="alert-heading">🚧 Under Construction</h4>
                        <p class="mb-0">
                            The jobs page is coming soon! For now, you can view individual jobs by visiting 
                            <code>/job/[job-id]</code> or return to the 
                            <a href="/dashboard" class="alert-link">Dashboard</a>.
                        </p>
                    </div>
                </div>
            </div>
        `;

        console.log('🎨 Jobs page rendered (placeholder)');
    }

    /**
     * Render error page
     * @param {HTMLElement} container - Container to render into
     * @param {string} message - Error message
     */
    renderErrorPage(container, message) {
        container.innerHTML = `
            <div class="error-page">
                <div class="container-fluid">
                    <div class="text-center py-5">
                        <h1 class="h2 text-danger">⚠️ Error</h1>
                        <p class="lead">${message}</p>
                        <div class="mt-4">
                            <a href="/dashboard" class="btn btn-primary">Return to Dashboard</a>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // === Event Handler Methods ===

    /**
     * Handle form submission and start video generation
     * @param {Object} data - Form submission data
     */
    async handleFormSubmission(data) {
        const { formData, previewUrl, validation } = data;

        console.log('📋 Form submitted:', formData);

        try {
            // Prepare generation parameters
            const generationParams = {
                country: formData.country,
                platform: formData.platform,
                genre: formData.genre,
                template: formData.template,
                contentType: formData.contentType,
                url: previewUrl
            };

            // Start video generation via Job Manager
            await JobManager.startVideoGeneration(generationParams);

            // IMMEDIATE DASHBOARD UPDATE: Refresh dashboard to show the new job
            console.log('🔄 Refreshing dashboard to show new job...');
            if (window.ProcessTable && typeof window.ProcessTable.loadRecentJobs === 'function') {
                setTimeout(() => {
                    window.ProcessTable.loadRecentJobs();
                }, 1000); // Give the job 1 second to be created
            }
        } catch (error) {
            console.error('❌ Form submission failed:', error);
            UIManager.addStatusMessage('error', '❌', `Generation failed: ${error.message}`);
        }
    }

    /**
     * Handle manual status check (for Creatomate renders)
     */
    async handleManualStatusCheck() {
        const creatomateIdDisplay = DOMManager.get('creatomateIdDisplay');
        if (!creatomateIdDisplay || !creatomateIdDisplay.textContent) {
            UIManager.addStatusMessage('warning', '⚠️', 'No Creatomate ID available for status check');
            return;
        }

        const creatomateId = creatomateIdDisplay.textContent.trim();

        try {
            UIManager.addStatusMessage('info', '🔍', 'Checking render status...');

            const statusData = await APIService.getCreatomateStatus(creatomateId);

            if (statusData.success && statusData.videoUrl) {
                UIManager.addStatusMessage('success', '🎬', 'Video is ready!');
                UIManager.displayVideo({
                    jobId: `manual-${Date.now()}`,
                    videoUrl: statusData.videoUrl,
                    creatomateId: creatomateId
                });
            } else if (statusData.success && statusData.status) {
                const status = statusData.status.charAt(0).toUpperCase() + statusData.status.slice(1);
                UIManager.addStatusMessage('info', '⏳', `Render status: ${status}`);
            } else {
                UIManager.addStatusMessage(
                    'error',
                    '❌',
                    `Status check failed: ${statusData.message || 'Unknown error'}`
                );
            }
        } catch (error) {
            console.error('❌ Manual status check failed:', error);
            UIManager.addStatusMessage('error', '❌', `Status check error: ${error.message}`);
        }
    }

    /**
     * Handle manual video loading
     */
    handleManualVideoLoad() {
        const creatomateIdInput = prompt('Enter Creatomate render ID:');

        if (!creatomateIdInput || !creatomateIdInput.trim()) {
            UIManager.addStatusMessage('warning', '⚠️', 'No render ID provided');
            return;
        }

        const creatomateId = creatomateIdInput.trim();

        // Update display and trigger status check
        const creatomateIdDisplay = DOMManager.get('creatomateIdDisplay');
        if (creatomateIdDisplay) {
            creatomateIdDisplay.textContent = creatomateId;
        }

        UIManager.addStatusMessage('info', '📥', `Loading video for render ID: ${creatomateId}`);
        this.handleManualStatusCheck();
    }

    // === Error Handling ===

    /**
     * Handle app initialization errors
     * @param {Error} error - Initialization error
     */
    handleInitializationError(error) {
        const errorMsg = `Failed to initialize application: ${error.message}`;

        // Try to show error in UI if possible
        try {
            UIManager.addStatusMessage('error', '❌', errorMsg, false);
        } catch {
            // Fallback to console and alert if UI isn't available
            console.error('❌', errorMsg);
            alert(errorMsg);
        }
    }

    // === Utility Methods ===

    /**
     * Get application status
     * @returns {Object} Application status
     */
    getStatus() {
        return {
            initialized: this.isInitialized,
            modules: Object.fromEntries(
                Object.entries(this.modules).map(([key, module]) => [
                    key,
                    typeof module.getStatus === 'function' ? module.getStatus() : 'ready'
                ])
            ),
            realtime: RealtimeService.getConnectionStatus(),
            jobs: JobManager.getJobStats(),
            api: APIService.getCacheStats()
        };
    }

    /**
     * Restart the application
     */
    async restart() {
        console.log('🔄 Restarting application...');

        // Cleanup existing resources
        this.cleanup();

        // Reset initialization flag
        this.isInitialized = false;

        // Wait a moment then reinitialize
        setTimeout(async () => {
            await this.init();
        }, 1000);
    }

    /**
     * Stop all polling timers to prevent request spam
     */
    stopAllPolling() {
        console.log('🛑 ANTI-SPAM: Stopping all polling timers...');

        // Stop ProcessTable polling
        if (window.ProcessTable && typeof window.ProcessTable.stopPeriodicUpdates === 'function') {
            window.ProcessTable.stopPeriodicUpdates();
        }

        console.log('✅ All polling stopped (anti-spam mode)');
    }

    /**
     * Cleanup application resources
     */
    cleanup() {
        console.log('🧹 Cleaning up application resources...');

        // ANTI-SPAM: Stop all polling first
        this.stopAllPolling();

        // Cleanup modules that support it
        Object.values(this.modules).forEach((module) => {
            if (typeof module.cleanup === 'function') {
                module.cleanup();
            }
        });

        console.log('✅ Application cleaned up');
    }
}

// === Application Bootstrap ===

// Create app instance
const app = new StreamGankApp();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        app.init();
    });
} else {
    // DOM is already ready
    app.init();
}

// Export for global access and debugging
window.StreamGankApp = app;

// Export default for module systems
export default app;
