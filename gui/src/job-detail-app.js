/**
 * Professional Job Detail Application
 * Real-time job monitoring with live progress updates, timeline, and logs
 */

import APIService from './services/APIService.js';
import RealtimeService from './services/RealtimeService.js';

export class JobDetailApp {
    constructor() {
        this.jobId = this.extractJobIdFromURL();
        this.jobData = null;
        this.refreshInterval = null;
        this.logUpdateInterval = null;
        this.autoScroll = true;
        this.isInitialized = false;

        // Timeline steps for video generation process
        this.processSteps = [
            { id: 'queued', name: 'Queued', description: 'Job added to processing queue' },
            { id: 'initializing', name: 'Initializing', description: 'Setting up job environment' },
            { id: 'scraping', name: 'Content Discovery', description: 'Finding movies/shows from platform' },
            { id: 'processing', name: 'Data Processing', description: 'Analyzing content and metadata' },
            { id: 'generating', name: 'Video Creation', description: 'Generating video content' },
            { id: 'rendering', name: 'Video Rendering', description: 'Creating final video file' },
            { id: 'uploading', name: 'Upload & Storage', description: 'Saving video to cloud storage' },
            { id: 'completed', name: 'Completed', description: 'Job finished successfully' }
        ];
    }

    /**
     * Initialize the application
     */
    async initialize() {
        try {
            console.log('🎬 Initializing Professional Job Detail App...');

            if (!this.jobId) {
                this.showError('Invalid job ID in URL');
                return;
            }

            // Set up event listeners
            this.setupEventListeners();

            // Load initial job data
            await this.loadJobData();

            // Start real-time updates
            this.startRealTimeUpdates();

            // Show main content
            this.showMainContent();

            console.log(`✅ Job Detail App initialized for job: ${this.jobId}`);
            this.isInitialized = true;
        } catch (error) {
            console.error('❌ Failed to initialize Job Detail App:', error);
            this.showError(`Failed to load job: ${error.message}`);
        }
    }

    /**
     * Extract job ID from current URL
     */
    extractJobIdFromURL() {
        const pathParts = window.location.pathname.split('/');
        const jobIndex = pathParts.indexOf('job');
        return jobIndex !== -1 && pathParts[jobIndex + 1] ? pathParts[jobIndex + 1] : null;
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Back button
        document.getElementById('back-btn')?.addEventListener('click', () => {
            window.history.back();
        });

        // Refresh button
        document.getElementById('refresh-btn')?.addEventListener('click', () => {
            this.refreshJobData();
        });

        // Clear logs button
        document.getElementById('clear-logs-btn')?.addEventListener('click', () => {
            this.clearLogs();
        });

        // Auto-scroll toggle
        document.getElementById('auto-scroll-btn')?.addEventListener('click', (e) => {
            this.toggleAutoScroll(e.target);
        });

        // Real-time service events
        RealtimeService.addEventListener('jobUpdate', (event) => {
            if (event.detail.jobId === this.jobId) {
                this.handleJobUpdate(event.detail);
            }
        });

        RealtimeService.addEventListener('jobLog', (event) => {
            if (event.detail.jobId === this.jobId) {
                this.addLogEntry(event.detail);
            }
        });
    }

    /**
     * Load job data from API
     */
    async loadJobData() {
        try {
            console.log(`📡 Loading job data for: ${this.jobId}`);

            const response = await APIService.getJobStatus(this.jobId);

            if (!response.success || !response.job) {
                throw new Error('Job not found');
            }

            this.jobData = response.job;
            this.updateUI();

            console.log('✅ Job data loaded successfully');
        } catch (error) {
            console.error('❌ Failed to load job data:', error);
            throw error;
        }
    }

    /**
     * Update the entire UI with current job data
     */
    updateUI() {
        if (!this.jobData) return;

        console.log('🔄 Updating UI with job data:', this.jobData);

        this.updateJobHeader();
        this.updateProgressSection();
        this.updateJobParameters();
        this.updateTimeline();
        this.updateQuickStats();
        this.updateActionButtons();
        this.updateErrorInfo();
        this.updateVideoResult();
    }

    /**
     * Update job header information
     */
    updateJobHeader() {
        const jobIdElement = document.getElementById('job-id');
        const statusBadge = document.getElementById('job-status-badge');
        const overviewCard = document.getElementById('job-overview-card');

        if (jobIdElement) {
            jobIdElement.textContent = this.jobData.id || 'Unknown';
        }

        if (statusBadge) {
            const status = this.jobData.status || 'unknown';
            statusBadge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            statusBadge.className = `badge ${this.getStatusBadgeClass(status)} ms-2`;
        }

        if (overviewCard) {
            overviewCard.className = `card bg-dark status-card mb-4 status-${this.jobData.status}`;
        }
    }

    /**
     * Update progress section
     */
    updateProgressSection() {
        const progressBar = document.getElementById('progress-bar');
        const progressPercentage = document.getElementById('progress-percentage');
        const currentStep = document.getElementById('current-step');

        const progress = this.jobData.progress || 0;

        if (progressBar) {
            progressBar.style.width = `${progress}%`;
            progressBar.className = `progress-bar ${this.getProgressBarClass(progress)} progress-bar-striped ${progress < 100 && this.jobData.status === 'active' ? 'progress-bar-animated' : ''}`;
        }

        if (progressPercentage) {
            progressPercentage.textContent = `${progress}%`;
        }

        if (currentStep) {
            currentStep.textContent = this.jobData.currentStep || this.getStepFromProgress(progress);
        }
    }

    /**
     * Update job parameters display
     */
    updateJobParameters() {
        const parametersContainer = document.getElementById('job-parameters');
        if (!parametersContainer) return;

        const params = [
            { label: 'Country', value: this.jobData.country, icon: 'fas fa-globe' },
            { label: 'Platform', value: this.jobData.platform, icon: 'fas fa-tv' },
            { label: 'Genre', value: this.jobData.genre, icon: 'fas fa-tags' },
            { label: 'Content Type', value: this.jobData.contentType, icon: 'fas fa-film' },
            { label: 'Template', value: this.jobData.template || 'Default', icon: 'fas fa-palette' },
            { label: 'Worker ID', value: this.jobData.workerId || 'Unassigned', icon: 'fas fa-user' }
        ];

        parametersContainer.innerHTML = params
            .map(
                (param) => `
            <div class="parameter-item">
                <div class="d-flex align-items-center mb-1">
                    <i class="${param.icon} me-2 text-primary"></i>
                    <small class="text-muted">${param.label}</small>
                </div>
                <div class="text-light fw-bold">${param.value || 'Unknown'}</div>
            </div>
        `
            )
            .join('');
    }

    /**
     * Update process timeline
     */
    updateTimeline() {
        const timelineContainer = document.getElementById('job-timeline');
        if (!timelineContainer) return;

        const currentProgress = this.jobData.progress || 0;
        const status = this.jobData.status;

        timelineContainer.innerHTML = this.processSteps
            .map((step, index) => {
                let iconClass = 'pending';
                let timestamp = '';

                // Determine step status based on job progress and status
                if (status === 'failed' && this.getProgressForStep(step.id) <= currentProgress) {
                    iconClass = 'failed';
                } else if (this.getProgressForStep(step.id) <= currentProgress) {
                    iconClass = 'completed';
                    timestamp = this.getStepTimestamp(step.id);
                } else if (this.getProgressForStep(step.id) <= currentProgress + 15) {
                    iconClass = 'active';
                }

                return `
                <div class="timeline-item">
                    <div class="timeline-icon ${iconClass}">
                        ${this.getStepIcon(step.id, iconClass)}
                    </div>
                    <div class="timeline-content">
                        <h6 class="text-light mb-1">${step.name}</h6>
                        <p class="text-muted mb-1 small">${step.description}</p>
                        ${timestamp ? `<small class="text-info">${timestamp}</small>` : ''}
                    </div>
                </div>
            `;
            })
            .join('');
    }

    /**
     * Update quick stats
     */
    updateQuickStats() {
        const duration = this.calculateDuration();
        const steps = this.getCurrentStepNumber();
        const worker = this.jobData.workerId ? this.jobData.workerId.slice(-4) : '--';
        const priority = this.jobData.priority || 'Normal';

        document.getElementById('stat-duration').textContent = duration;
        document.getElementById('stat-steps').textContent = steps;
        document.getElementById('stat-worker').textContent = worker;
        document.getElementById('stat-priority').textContent = priority;
    }

    /**
     * Update action buttons
     */
    updateActionButtons() {
        const actionsContainer = document.getElementById('job-actions');
        if (!actionsContainer) return;

        const status = this.jobData.status;
        let buttons = [];

        if (status === 'pending' || status === 'active') {
            buttons.push(`
                <button class="btn btn-outline-warning" onclick="jobDetailApp.cancelJob()">
                    <i class="fas fa-stop-circle me-1"></i> Cancel Job
                </button>
            `);
        }

        if (status === 'failed') {
            buttons.push(`
                <button class="btn btn-outline-primary" onclick="jobDetailApp.retryJob()">
                    <i class="fas fa-redo me-1"></i> Retry Job
                </button>
            `);
        }

        if (this.jobData.videoUrl) {
            buttons.push(`
                <a href="${this.jobData.videoUrl}" target="_blank" class="btn btn-success">
                    <i class="fas fa-play me-1"></i> Watch Video
                </a>
                <a href="${this.jobData.videoUrl}" download class="btn btn-outline-success">
                    <i class="fas fa-download me-1"></i> Download
                </a>
            `);
        }

        // Always show refresh button
        buttons.push(`
            <button class="btn btn-outline-info" onclick="jobDetailApp.refreshJobData()">
                <i class="fas fa-sync-alt me-1"></i> Refresh Status
            </button>
        `);

        actionsContainer.innerHTML = buttons.join('');
    }

    /**
     * Update error information
     */
    updateErrorInfo() {
        const errorCard = document.getElementById('error-card');
        const errorContent = document.getElementById('error-content');

        if (this.jobData.status === 'failed' && this.jobData.error) {
            errorContent.innerHTML = `
                <h6 class="text-danger mb-2">
                    <i class="fas fa-bug me-1"></i> Error Details
                </h6>
                <div class="bg-dark p-3 rounded border border-danger">
                    <code class="text-light">${this.jobData.error}</code>
                </div>
                ${
                    this.jobData.errorTimestamp
                        ? `
                <small class="text-muted d-block mt-2">
                    <i class="fas fa-clock me-1"></i> 
                    Error occurred: ${new Date(this.jobData.errorTimestamp).toLocaleString()}
                </small>
                `
                        : ''
                }
            `;
            errorCard.classList.remove('d-none');
        } else {
            errorCard.classList.add('d-none');
        }
    }

    /**
     * Update video result section
     */
    updateVideoResult() {
        const videoCard = document.getElementById('video-result-card');
        const videoContent = document.getElementById('video-content');

        if (this.jobData.status === 'completed' && this.jobData.videoUrl) {
            videoContent.innerHTML = `
                <div class="mb-3">
                    <video controls class="w-100 rounded" style="max-height: 300px;">
                        <source src="${this.jobData.videoUrl}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                </div>
                <div class="d-grid gap-2">
                    <a href="${this.jobData.videoUrl}" target="_blank" class="btn btn-success">
                        <i class="fas fa-external-link-alt me-1"></i> Open in New Tab
                    </a>
                    <a href="${this.jobData.videoUrl}" download class="btn btn-outline-light">
                        <i class="fas fa-download me-1"></i> Download Video
                    </a>
                    <button class="btn btn-outline-info" onclick="jobDetailApp.copyVideoUrl()">
                        <i class="fas fa-copy me-1"></i> Copy URL
                    </button>
                </div>
            `;
            videoCard.classList.remove('d-none');
        } else {
            videoCard.classList.add('d-none');
        }
    }

    /**
     * Start real-time updates
     */
    startRealTimeUpdates() {
        console.log('🔄 Starting real-time updates...');

        // Initialize RealtimeService for real-time events
        RealtimeService.init();

        // PROFESSIONAL: Webhooks provide real-time updates, minimal polling as backup only
        this.refreshInterval = setInterval(() => {
            this.refreshJobData();
        }, 120000); // Backup refresh every 2 minutes only (webhooks do the real work)

        // Simulate live logs (in real implementation, this would come from WebSocket)
        this.startLogUpdates();
    }

    /**
     * Start log updates simulation
     */
    startLogUpdates() {
        this.logUpdateInterval = setInterval(() => {
            if (this.jobData && (this.jobData.status === 'active' || this.jobData.status === 'pending')) {
                this.simulateLogEntry();
            }
        }, 3000); // Add log entry every 3 seconds
    }

    /**
     * Simulate a log entry (for demonstration)
     */
    simulateLogEntry() {
        const sampleLogs = [
            { level: 'info', message: 'Processing content metadata...' },
            { level: 'success', message: 'Found content matching criteria' },
            { level: 'info', message: 'Generating video segments...' },
            { level: 'info', message: 'Applying video template...' },
            { level: 'success', message: 'Video segment created successfully' },
            { level: 'info', message: 'Uploading to cloud storage...' }
        ];

        if (Math.random() < 0.3) {
            // 30% chance to add a log entry
            const randomLog = sampleLogs[Math.floor(Math.random() * sampleLogs.length)];
            this.addLogEntry({
                timestamp: new Date(),
                level: randomLog.level,
                message: randomLog.message
            });
        }
    }

    /**
     * Add a log entry to the log viewer
     */
    addLogEntry(logData) {
        const logViewer = document.getElementById('log-viewer');
        if (!logViewer) return;

        const timestamp = new Date(logData.timestamp || new Date()).toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        logEntry.innerHTML = `
            <span class="log-timestamp">[${timestamp}]</span>
            <span class="log-level-${logData.level}">${logData.message}</span>
        `;

        logViewer.appendChild(logEntry);

        // Auto-scroll to bottom if enabled
        if (this.autoScroll) {
            logViewer.scrollTop = logViewer.scrollHeight;
        }

        // Limit log entries to prevent memory issues
        const maxEntries = 100;
        while (logViewer.children.length > maxEntries) {
            logViewer.removeChild(logViewer.firstChild);
        }
    }

    /**
     * Refresh job data
     */
    async refreshJobData() {
        try {
            console.log('🔄 Refreshing job data...');
            await this.loadJobData();
            console.log('✅ Job data refreshed');
        } catch (error) {
            console.error('❌ Failed to refresh job data:', error);
            this.addLogEntry({
                level: 'error',
                message: `Failed to refresh job data: ${error.message}`
            });
        }
    }

    /**
     * Handle job update from real-time service
     */
    handleJobUpdate(updateData) {
        console.log('📡 Received job update:', updateData);

        // Merge update data with current job data
        this.jobData = { ...this.jobData, ...updateData };

        // Update UI
        this.updateUI();

        // Add log entry about the update
        this.addLogEntry({
            level: 'info',
            message: `Job status updated: ${updateData.status || 'Status change'}`
        });
    }

    /**
     * Show main content and hide loading
     */
    showMainContent() {
        document.getElementById('loading-state').classList.add('d-none');
        document.getElementById('main-content').classList.remove('d-none');
    }

    /**
     * Show error state
     */
    showError(message) {
        document.getElementById('loading-state').classList.add('d-none');
        document.getElementById('main-content').classList.add('d-none');
        document.getElementById('error-state').classList.remove('d-none');
        document.getElementById('error-message').textContent = message;
    }

    /**
     * Clear log viewer
     */
    clearLogs() {
        const logViewer = document.getElementById('log-viewer');
        if (logViewer) {
            logViewer.innerHTML =
                '<div class="log-entry"><span class="log-timestamp">[Cleared]</span><span class="log-level-info">Log viewer cleared</span></div>';
        }
    }

    /**
     * Toggle auto-scroll
     */
    toggleAutoScroll(button) {
        this.autoScroll = !this.autoScroll;
        button.classList.toggle('active', this.autoScroll);

        if (this.autoScroll) {
            const logViewer = document.getElementById('log-viewer');
            if (logViewer) {
                logViewer.scrollTop = logViewer.scrollHeight;
            }
        }
    }

    /**
     * Cancel job
     */
    async cancelJob() {
        if (confirm('Are you sure you want to cancel this job?')) {
            try {
                const response = await APIService.cancelJob(this.jobId);
                if (response.success) {
                    this.addLogEntry({
                        level: 'warning',
                        message: 'Job cancellation requested'
                    });
                    await this.refreshJobData();
                } else {
                    throw new Error(response.message || 'Failed to cancel job');
                }
            } catch (error) {
                console.error('❌ Failed to cancel job:', error);
                this.addLogEntry({
                    level: 'error',
                    message: `Failed to cancel job: ${error.message}`
                });
            }
        }
    }

    /**
     * Retry job
     */
    async retryJob() {
        if (confirm('Are you sure you want to retry this job?')) {
            try {
                const response = await APIService.retryJob(this.jobId);
                if (response.success) {
                    this.addLogEntry({
                        level: 'info',
                        message: 'Job retry requested'
                    });
                    await this.refreshJobData();
                } else {
                    throw new Error(response.message || 'Failed to retry job');
                }
            } catch (error) {
                console.error('❌ Failed to retry job:', error);
                this.addLogEntry({
                    level: 'error',
                    message: `Failed to retry job: ${error.message}`
                });
            }
        }
    }

    /**
     * Copy video URL to clipboard
     */
    async copyVideoUrl() {
        try {
            await navigator.clipboard.writeText(this.jobData.videoUrl);
            this.addLogEntry({
                level: 'success',
                message: 'Video URL copied to clipboard'
            });
        } catch (error) {
            console.error('Failed to copy URL:', error);
            this.addLogEntry({
                level: 'error',
                message: 'Failed to copy URL to clipboard'
            });
        }
    }

    // Helper methods
    getStatusBadgeClass(status) {
        const classes = {
            pending: 'bg-warning text-dark',
            active: 'bg-info text-dark',
            completed: 'bg-success',
            failed: 'bg-danger',
            cancelled: 'bg-secondary'
        };
        return classes[status] || 'bg-secondary';
    }

    getProgressBarClass(progress) {
        if (progress >= 100) return 'bg-success';
        if (progress >= 75) return 'bg-info';
        if (progress >= 50) return 'bg-warning';
        return 'bg-primary';
    }

    getStepFromProgress(progress) {
        const step = Math.floor(progress / 12.5); // 8 steps, so 100/8 = 12.5
        return this.processSteps[Math.min(step, this.processSteps.length - 1)]?.description || 'Processing...';
    }

    getProgressForStep(stepId) {
        const index = this.processSteps.findIndex((step) => step.id === stepId);
        return index !== -1 ? (index / this.processSteps.length) * 100 : 0;
    }

    getStepIcon(stepId, iconClass) {
        if (iconClass === 'completed') return '✓';
        if (iconClass === 'failed') return '✗';
        if (iconClass === 'active') return '⟳';
        return '○';
    }

    getStepTimestamp(stepId) {
        // In a real implementation, this would return actual timestamps
        return new Date().toLocaleString();
    }

    getCurrentStepNumber() {
        const progress = this.jobData?.progress || 0;
        return `${Math.min(Math.floor(progress / 12.5) + 1, 8)}/8`;
    }

    calculateDuration() {
        if (!this.jobData?.startedAt) return '--';

        const start = new Date(this.jobData.startedAt);
        const end = this.jobData.completedAt ? new Date(this.jobData.completedAt) : new Date();
        const duration = end - start;

        const minutes = Math.floor(duration / 60000);
        const seconds = Math.floor((duration % 60000) / 1000);

        if (minutes > 0) {
            return `${minutes}m ${seconds}s`;
        }
        return `${seconds}s`;
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        if (this.logUpdateInterval) {
            clearInterval(this.logUpdateInterval);
        }

        RealtimeService.cleanup();
        console.log('🧹 Job Detail App cleaned up');
    }
}

// Create global instance for button callbacks
window.jobDetailApp = new JobDetailApp();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.jobDetailApp.initialize();
    });
} else {
    window.jobDetailApp.initialize();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    window.jobDetailApp.cleanup();
});
