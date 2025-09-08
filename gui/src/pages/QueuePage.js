/**
 * QueuePage - Dedicated page for queue management and job monitoring
 * Provides comprehensive real-time queue visualization and management
 */

import UIManager from '../components/UIManager.js';
import APIService from '../services/APIService.js';
import RealtimeService from '../services/RealtimeService.js';
import Router from '../core/Router.js';

export class QueuePage {
    constructor() {
        this.jobs = [];
        this.queueStats = {};
        this.refreshTimer = null;
        this.refreshInterval = 5000; // 5 seconds
        this.currentFilter = 'all';
        this.isInitialized = false;

        // Make Router available globally for onclick handlers
        window.Router = Router;
    }

    /**
     * Render the queue page
     * @param {HTMLElement} container - Container to render into
     */
    async render(container) {
        if (!container) {
            console.error('📋 QueuePage: No container provided');
            return;
        }

        // Show loading state first
        container.innerHTML = this.createLoadingTemplate();

        try {
            // Load initial data
            await this.loadQueueData();

            // Render queue interface
            container.innerHTML = this.createQueueTemplate();

            // Set up event listeners
            this.setupEventListeners();

            // Start real-time updates
            this.startRealTimeUpdates();

            console.log('📋 Queue Page rendered successfully');
            this.isInitialized = true;
        } catch (error) {
            console.error('📋 Queue Page render error:', error);
            this.renderError(container, error.message);
        }
    }

    /**
     * Create loading template
     * @returns {string} Loading HTML
     */
    createLoadingTemplate() {
        return `
            <div class="queue-page">
                <div class="container-fluid">
                    <!-- Header -->
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <div>
                            <h1 class="h3 mb-0">
                                <i class="fas fa-tasks me-2"></i>
                                Queue Management
                            </h1>
                            <p class="text-light mb-0">Monitor and manage video generation jobs</p>
                        </div>
                        <div class="nav-links">
                            <a href="/dashboard" class="btn btn-outline-primary me-2 nav-link" data-route="/dashboard">
                                <i class="fas fa-home me-1"></i>Dashboard
                            </a>
                        </div>
                    </div>
                    
                    <!-- Loading State -->
                    <div class="text-center py-5">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="text-light">Loading queue data...</p>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Create main queue template
     * @returns {string} Queue page HTML
     */
    createQueueTemplate() {
        return `
            <div class="queue-page">
                <div class="container-fluid">
                    <!-- Header with Stats -->
                    <div class="row mb-4">
                        <div class="col-md-8">
                            <h1 class="h3 mb-0">
                                <i class="fas fa-tasks me-2"></i>
                                Queue Management
                            </h1>
                            <p class="text-light mb-0">Monitor and manage video generation jobs</p>
                        </div>
                        <div class="col-md-4 text-end">
                            <a href="/dashboard" class="btn btn-outline-primary me-2 nav-link" data-route="/dashboard">
                                <i class="fas fa-home me-1"></i>Dashboard
                            </a>
                            <button id="refresh-queue" class="btn btn-primary">
                                <i class="fas fa-sync-alt me-1"></i>Refresh
                            </button>
                        </div>
                    </div>

                    <!-- Queue Statistics Cards -->
                    <div class="row mb-4">
                        <div class="col-md-3">
                            <div class="card bg-dark border-warning">
                                <div class="card-body text-center">
                                    <div class="display-6 text-warning" id="stat-pending">0</div>
                                    <div class="text-light">⏳ Pending Jobs</div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card bg-dark border-info">
                                <div class="card-body text-center">
                                    <div class="display-6 text-info" id="stat-processing">0</div>
                                    <div class="text-light">🔄 Processing</div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card bg-dark border-success">
                                <div class="card-body text-center">
                                    <div class="display-6 text-success" id="stat-completed">0</div>
                                    <div class="text-light">✅ Completed</div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="card bg-dark border-danger">
                                <div class="card-body text-center">
                                    <div class="display-6 text-danger" id="stat-failed">0</div>
                                    <div class="text-light">❌ Failed</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Worker Pool Status -->
                    <div class="row mb-4">
                        <div class="col-12">
                            <div class="card bg-dark">
                                <div class="card-header">
                                    <h5 class="mb-0">
                                        <i class="fas fa-users me-2"></i>Worker Pool Status
                                    </h5>
                                </div>
                                <div class="card-body">
                                    <div class="row text-center">
                                        <div class="col-md-4">
                                            <div class="border-end">
                                                <div class="h4 text-primary" id="workers-active">0</div>
                                                <div class="text-light">🏃 Active Workers</div>
                                            </div>
                                        </div>
                                        <div class="col-md-4">
                                            <div class="border-end">
                                                <div class="h4 text-success" id="workers-available">3</div>
                                                <div class="text-light">💤 Available</div>
                                            </div>
                                        </div>
                                        <div class="col-md-4">
                                            <div class="h4 text-info" id="workers-concurrent">Yes</div>
                                            <div class="text-light">⚙️ Concurrent Mode</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Job Controls and Filters -->
                    <div class="row mb-4">
                        <div class="col-md-8">
                            <div class="btn-group me-3" role="group">
                                <button type="button" class="btn btn-outline-secondary filter-btn active" data-filter="all">
                                    All Jobs <span id="count-all" class="badge bg-primary">0</span>
                                </button>
                                <button type="button" class="btn btn-outline-warning filter-btn" data-filter="pending">
                                    Pending <span id="count-pending" class="badge bg-warning">0</span>
                                </button>
                                <button type="button" class="btn btn-outline-info filter-btn" data-filter="processing">
                                    Processing <span id="count-processing" class="badge bg-info">0</span>
                                </button>
                                <button type="button" class="btn btn-outline-success filter-btn" data-filter="completed">
                                    Completed <span id="count-completed" class="badge bg-success">0</span>
                                </button>
                                <button type="button" class="btn btn-outline-danger filter-btn" data-filter="failed">
                                    Failed <span id="count-failed" class="badge bg-danger">0</span>
                                </button>
                            </div>
                        </div>
                        <div class="col-md-4 text-end">
                            <button id="pause-queue" class="btn btn-outline-warning me-2">
                                <i class="fas fa-pause me-1"></i>Pause Queue
                            </button>
                            <button id="clear-queue" class="btn btn-outline-danger">
                                <i class="fas fa-trash me-1"></i>Clear Failed
                            </button>
                        </div>
                    </div>

                    <!-- Jobs List -->
                    <div class="card bg-dark">
                        <div class="card-header">
                            <h5 class="mb-0">
                                <i class="fas fa-list me-2"></i>Job Queue 
                                <span id="total-jobs-count" class="badge bg-primary ms-2">0</span>
                            </h5>
                        </div>
                        <div class="card-body p-0">
                            <div id="jobs-container" class="jobs-list">
                                <!-- Jobs will be populated here -->
                            </div>
                            
                            <!-- Empty State -->
                            <div id="empty-queue" class="text-center py-5 d-none">
                                <i class="fas fa-inbox fa-3x text-light mb-3"></i>
                                <h5 class="text-light">No jobs in queue</h5>
                                <p class="text-light">Generate a video to see jobs appear here</p>
                                <a href="/dashboard" class="btn btn-primary nav-link" data-route="/dashboard">
                                    <i class="fas fa-plus me-1"></i>Generate Video
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <style>
                .jobs-list {
                    max-height: 600px;
                    overflow-y: auto;
                }
                
                .job-item {
                    border-bottom: 1px solid #495057;
                    padding: 1rem;
                    transition: background-color 0.2s;
                }
                
                .job-item:hover {
                    background-color: rgba(255, 255, 255, 0.05);
                }
                
                .job-item:last-child {
                    border-bottom: none;
                }
                
                .status-badge {
                    font-size: 0.8rem;
                    padding: 0.25rem 0.5rem;
                }
                
                .filter-btn.active {
                    background-color: #0d6efd;
                    border-color: #0d6efd;
                    color: white;
                }
            </style>
        `;
    }

    /**
     * Load queue data from API
     */
    async loadQueueData() {
        try {
            console.log('📋 Loading queue data...');

            // Load queue statistics with fallback
            try {
                const statsResponse = await APIService.get('/api/queue/status');
                if (statsResponse.success) {
                    this.queueStats = statsResponse.stats;
                }
            } catch (statsError) {
                console.warn('📋 Failed to load queue stats, using defaults:', statsError.message);
                this.queueStats = {
                    pending: 0,
                    processing: 0,
                    completed: 0,
                    failed: 0,
                    activeWorkers: 0,
                    availableWorkers: 3,
                    concurrentProcessing: true
                };
            }

            // Load all jobs with fallback
            try {
                const jobsResponse = await APIService.get('/api/queue/jobs');
                if (jobsResponse.success) {
                    this.jobs = jobsResponse.jobs || [];
                }
            } catch (jobsError) {
                console.warn('📋 Failed to load jobs, using empty array:', jobsError.message);
                this.jobs = [];
            }

            console.log(`📋 Loaded ${this.jobs.length} jobs and queue stats`);
        } catch (error) {
            console.error('📋 Failed to load queue data:', error);
            // Don't throw if we have fallback data
            if (!this.queueStats) {
                throw error;
            }
        }
    }

    /**
     * Update the UI with current data
     */
    updateUI() {
        this.updateStats();
        this.updateJobsList();
        console.log('📋 UI updated with latest queue data');
    }

    /**
     * Update statistics display
     */
    updateStats() {
        const stats = this.queueStats;

        // Update main stats - with safety checks
        const pendingEl = document.getElementById('stat-pending');
        const processingEl = document.getElementById('stat-processing');
        const completedEl = document.getElementById('stat-completed');
        const failedEl = document.getElementById('stat-failed');

        if (pendingEl) pendingEl.textContent = stats.pending || 0;
        if (processingEl) processingEl.textContent = stats.processing || 0;
        if (completedEl) completedEl.textContent = stats.completed || 0;
        if (failedEl) failedEl.textContent = stats.failed || 0;

        // Update worker stats - with safety checks
        const activeEl = document.getElementById('workers-active');
        const availableEl = document.getElementById('workers-available');
        const concurrentEl = document.getElementById('workers-concurrent');

        if (activeEl) activeEl.textContent = stats.activeWorkers || 0;
        if (availableEl) availableEl.textContent = stats.availableWorkers || 0;
        if (concurrentEl) concurrentEl.textContent = stats.concurrentProcessing ? 'Yes' : 'No';

        // Update filter counts - with safety checks
        const counts = this.getJobCounts();
        const countAllEl = document.getElementById('count-all');
        const countPendingEl = document.getElementById('count-pending');
        const countProcessingEl = document.getElementById('count-processing');
        const countCompletedEl = document.getElementById('count-completed');
        const countFailedEl = document.getElementById('count-failed');

        if (countAllEl) countAllEl.textContent = counts.all;
        if (countPendingEl) countPendingEl.textContent = counts.pending;
        if (countProcessingEl) countProcessingEl.textContent = counts.processing;
        if (countCompletedEl) countCompletedEl.textContent = counts.completed;
        if (countFailedEl) countFailedEl.textContent = counts.failed;

        const totalJobsEl = document.getElementById('total-jobs-count');
        if (totalJobsEl) totalJobsEl.textContent = counts.all;
    }

    /**
     * Update jobs list display
     */
    updateJobsList() {
        const container = document.getElementById('jobs-container');
        const emptyState = document.getElementById('empty-queue');

        if (!container) return;

        // Filter jobs based on current filter
        const filteredJobs = this.filterJobs(this.jobs, this.currentFilter);

        if (filteredJobs.length === 0) {
            container.innerHTML = '';
            emptyState?.classList.remove('d-none');
            return;
        }

        emptyState?.classList.add('d-none');

        // Sort jobs: processing first, then by creation date (newest first)
        filteredJobs.sort((a, b) => {
            if (a.status === 'processing' && b.status !== 'processing') return -1;
            if (b.status === 'processing' && a.status !== 'processing') return 1;
            return new Date(b.createdAt) - new Date(a.createdAt);
        });

        container.innerHTML = filteredJobs.map((job) => this.createJobItem(job)).join('');
    }

    /**
     * Create HTML for a single job item
     * @param {Object} job - Job data
     * @returns {string} Job item HTML
     */
    createJobItem(job) {
        const statusClass = this.getStatusClass(job.status);
        const statusIcon = this.getStatusIcon(job.status);
        const duration = this.calculateDuration(job);
        const progress = job.progress || 0;

        return `
            <div class="job-item" data-job-id="${job.id}">
                <div class="row align-items-center">
                    <div class="col-md-1">
                        <span class="badge ${statusClass} status-badge">
                            ${statusIcon} ${job.status.toUpperCase()}
                        </span>
                    </div>
                    <div class="col-md-2">
                        <div class="text-light fw-medium">${job.id.slice(-8)}</div>
                        <small class="text-light">${this.formatDate(job.createdAt)}</small>
                    </div>
                    <div class="col-md-3">
                        <div class="text-light">${job.parameters?.genre || 'N/A'} • ${job.parameters?.platform || 'N/A'}</div>
                        <small class="text-light">${job.parameters?.country || 'N/A'}</small>
                    </div>
                    <div class="col-md-2">
                        <div class="progress mb-1" style="height: 6px;">
                            <div class="progress-bar ${this.getProgressClass(progress)}" 
                                 style="width: ${progress}%"></div>
                        </div>
                        <small class="text-light">${progress}% • ${duration}</small>
                    </div>
                    <div class="col-md-2">
                        <div class="text-light">${job.currentStep || 'Queued'}</div>
                        ${job.error ? `<small class="text-danger">${job.error.slice(0, 50)}...</small>` : ''}
                    </div>
                    <div class="col-md-2 text-end">
                        <button class="btn btn-sm btn-outline-primary me-1" onclick="viewJob('${job.id}')">
                            <i class="fas fa-eye"></i>
                        </button>
                        ${
                            job.status === 'failed'
                                ? `
                            <button class="btn btn-sm btn-outline-warning" onclick="retryJob('${job.id}')">
                                <i class="fas fa-redo"></i>
                            </button>
                        `
                                : ''
                        }
                        ${
                            ['pending', 'processing'].includes(job.status)
                                ? `
                            <button class="btn btn-sm btn-outline-danger" onclick="cancelJob('${job.id}')">
                                <i class="fas fa-stop"></i>
                            </button>
                        `
                                : ''
                        }
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Filter buttons
        document.querySelectorAll('.filter-btn').forEach((btn) => {
            btn.addEventListener('click', (e) => {
                const filter = e.currentTarget.dataset.filter;
                this.setFilter(filter);
            });
        });

        // Refresh button
        document.getElementById('refresh-queue')?.addEventListener('click', () => {
            this.refreshQueue();
        });

        // Queue control buttons
        document.getElementById('pause-queue')?.addEventListener('click', () => {
            this.toggleQueue();
        });

        document.getElementById('clear-queue')?.addEventListener('click', () => {
            this.clearFailedJobs();
        });

        // Real-time service updates
        RealtimeService.addEventListener('queueUpdate', (event) => {
            this.handleQueueUpdate(event.detail);
        });
    }

    /**
     * Set current filter
     * @param {string} filter - Filter type
     */
    setFilter(filter) {
        this.currentFilter = filter;

        // Update button states
        document.querySelectorAll('.filter-btn').forEach((btn) => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-filter="${filter}"]`)?.classList.add('active');

        // Update jobs display
        this.updateJobsList();
    }

    /**
     * Filter jobs by status
     * @param {Array} jobs - Jobs array
     * @param {string} filter - Filter type
     * @returns {Array} Filtered jobs
     */
    filterJobs(jobs, filter) {
        if (filter === 'all') return jobs;
        return jobs.filter((job) => job.status === filter);
    }

    /**
     * Get job counts by status
     * @returns {Object} Job counts
     */
    getJobCounts() {
        const counts = {
            all: this.jobs.length,
            pending: 0,
            processing: 0,
            completed: 0,
            failed: 0
        };

        this.jobs.forEach((job) => {
            if (counts[job.status] !== undefined) {
                counts[job.status]++;
            }
        });

        return counts;
    }

    /**
     * Start real-time updates
     */
    startRealTimeUpdates() {
        this.refreshTimer = setInterval(() => {
            this.refreshQueue();
        }, this.refreshInterval);

        // Initialize real-time service if not already done
        if (!RealtimeService.isInitialized) {
            RealtimeService.init();
        }

        console.log('📋 Real-time updates started');
    }

    /**
     * Stop real-time updates
     */
    stopRealTimeUpdates() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
        console.log('📋 Real-time updates stopped');
    }

    /**
     * Refresh queue data
     */
    async refreshQueue() {
        try {
            await this.loadQueueData();
            this.updateUI();
        } catch (error) {
            console.error('📋 Failed to refresh queue:', error);
        }
    }

    /**
     * Handle queue update from real-time service
     * @param {Object} updateData - Update data
     */
    handleQueueUpdate(updateData) {
        console.log('📋 Received queue update:', updateData);
        // Update specific job or refresh entire queue
        this.refreshQueue();
    }

    /**
     * Toggle queue processing
     */
    async toggleQueue() {
        const button = document.getElementById('pause-queue');
        const originalText = button?.innerHTML;

        try {
            // Show loading state
            if (button) {
                button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Processing...';
                button.disabled = true;
            }

            const response = await APIService.post('/api/queue/toggle');
            if (response.success) {
                const action = response.isProcessing ? 'resumed' : 'paused';
                UIManager.addStatusMessage('success', '⏸️', `Queue processing ${action}`);

                // Update button text based on new state
                if (button) {
                    const newText = response.isProcessing
                        ? '<i class="fas fa-pause me-1"></i>Pause Queue'
                        : '<i class="fas fa-play me-1"></i>Resume Queue';
                    button.innerHTML = newText;
                }

                this.refreshQueue();
            }
        } catch (error) {
            console.error('📋 Failed to toggle queue:', error);
            UIManager.addStatusMessage('error', '❌', 'Failed to toggle queue');
        } finally {
            // Restore button state
            if (button) {
                if (originalText) button.innerHTML = originalText;
                button.disabled = false;
            }
        }
    }

    /**
     * Clear failed jobs
     */
    async clearFailedJobs() {
        if (!confirm('Clear all failed jobs? This cannot be undone.')) return;

        try {
            const response = await APIService.post('/api/queue/clear-failed');
            if (response.success) {
                UIManager.addStatusMessage('success', '🗑️', 'Failed jobs cleared');
                this.refreshQueue();
            }
        } catch (error) {
            console.error('📋 Failed to clear failed jobs:', error);
            UIManager.addStatusMessage('error', '❌', 'Failed to clear jobs');
        }
    }

    /**
     * Render error state
     * @param {HTMLElement} container - Container element
     * @param {string} message - Error message
     */
    renderError(container, message) {
        container.innerHTML = `
            <div class="queue-page">
                <div class="container-fluid">
                    <div class="alert alert-danger">
                        <h4 class="alert-heading">❌ Error</h4>
                        <p class="mb-0">${message}</p>
                        <hr>
                        <button onclick="location.reload()" class="btn btn-primary">Retry</button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Page activation
     */
    activate() {
        document.title = 'Queue Management - StreamGank';
        console.log('📋 Queue Page activated');
    }

    /**
     * Page deactivation
     */
    deactivate() {
        this.stopRealTimeUpdates();
        console.log('📋 Queue Page deactivated');
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.stopRealTimeUpdates();
        this.isInitialized = false;
        console.log('📋 Queue Page cleaned up');
    }

    // Helper methods
    getStatusClass(status) {
        const classes = {
            pending: 'bg-warning text-dark',
            processing: 'bg-info text-dark',
            completed: 'bg-success',
            failed: 'bg-danger',
            cancelled: 'bg-secondary'
        };
        return classes[status] || 'bg-secondary';
    }

    getStatusIcon(status) {
        const icons = {
            pending: '⏳',
            processing: '🔄',
            completed: '✅',
            failed: '❌',
            cancelled: '⏹️'
        };
        return icons[status] || '📄';
    }

    getProgressClass(progress) {
        if (progress >= 100) return 'bg-success';
        if (progress >= 75) return 'bg-info';
        if (progress >= 50) return 'bg-warning';
        return 'bg-primary';
    }

    formatDate(dateString) {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleString();
    }

    calculateDuration(job) {
        if (!job.startedAt) return 'Not started';
        const start = new Date(job.startedAt);
        const end = job.completedAt ? new Date(job.completedAt) : new Date();
        const duration = end - start;
        const minutes = Math.floor(duration / 60000);
        const seconds = Math.floor((duration % 60000) / 1000);
        return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
    }
}

// Global functions for button actions
window.viewJob = (jobId) => {
    if (!jobId || jobId === 'undefined') {
        console.error('❌ Invalid jobId:', jobId);
        UIManager.addStatusMessage('error', '❌', 'Invalid job ID');
        return;
    }

    console.log('🔍 Viewing job:', jobId);

    // Use Router from the imported module (not window.Router)
    try {
        Router.navigate(`/job/${jobId}`);
        console.log(`✅ Navigating to job detail page: ${jobId}`);
    } catch (error) {
        console.error('❌ Navigation failed:', error);
        UIManager.addStatusMessage('error', '❌', 'Failed to navigate to job details');
    }
};

window.retryJob = async (jobId) => {
    if (confirm('Retry this job?')) {
        try {
            const response = await APIService.post(`/api/job/${jobId}/retry`);
            if (response.success) {
                UIManager.addStatusMessage('success', '🔄', 'Job retry initiated');
                // Refresh page or update UI
                location.reload();
            }
        } catch (error) {
            UIManager.addStatusMessage('error', '❌', 'Failed to retry job');
        }
    }
};

window.cancelJob = async (jobId) => {
    if (confirm('Cancel this job?')) {
        try {
            const response = await APIService.post(`/api/job/${jobId}/cancel`);
            if (response.success) {
                UIManager.addStatusMessage('success', '⏹️', 'Job cancelled');
                location.reload();
            }
        } catch (error) {
            UIManager.addStatusMessage('error', '❌', 'Failed to cancel job');
        }
    }
};

// Export singleton instance
export default new QueuePage();
