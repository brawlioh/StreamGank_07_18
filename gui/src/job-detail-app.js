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
        this.lastRefreshTime = 0; // Track last refresh for smart intervals

        // Timeline steps for video generation process - MATCHES ACTUAL WORKFLOW.PY
        this.processSteps = [
            { id: 'database_extraction', name: 'Database Extraction', description: 'Extracting movies from database' },
            { id: 'script_generation', name: 'Script Generation', description: 'Generating AI scripts for content' },
            {
                id: 'asset_preparation',
                name: 'Asset Preparation',
                description: 'Creating enhanced posters and movie clips'
            },
            { id: 'heygen_creation', name: 'HeyGen Video Creation', description: 'Generating AI avatar videos' },
            { id: 'heygen_processing', name: 'HeyGen Processing', description: 'Waiting for video completion' },
            {
                id: 'scroll_generation',
                name: 'Scroll Video Generation',
                description: 'Creating StreamGank scroll overlay'
            },
            { id: 'creatomate_assembly', name: 'Creatomate Assembly', description: 'Creating final video' }
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
            this.lastRefreshTime = Date.now(); // Initialize refresh tracking
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

        // PRODUCTION FIX: Always show 100% for completed jobs with video URL
        let progress = this.jobData.progress || 0;

        // Override progress for truly completed jobs
        if (this.jobData.status === 'completed' && this.jobData.videoUrl) {
            progress = 100;
        }
        // Show actual progress for completed jobs without video (still rendering)
        else if (this.jobData.status === 'completed' && !this.jobData.videoUrl) {
            // Keep the actual progress to show it's not truly done yet
            progress = this.jobData.progress || 0;
        }
        // Also ensure failed/cancelled jobs show their actual progress, not stuck at partial
        else if (this.jobData.status === 'failed' || this.jobData.status === 'cancelled') {
            // Keep original progress for failed/cancelled to show where it stopped
            progress = this.jobData.progress || 0;
        }

        if (progressBar) {
            progressBar.style.width = `${progress}%`;
            progressBar.className = `progress-bar ${this.getProgressBarClass(progress)} progress-bar-striped ${progress < 100 && ['active', 'processing', 'rendering'].includes(this.jobData.status) ? 'progress-bar-animated' : ''}`;
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

        // Add Creatomate ID if available
        if (this.jobData.creatomateId) {
            params.push({
                label: 'Creatomate ID',
                value: this.jobData.creatomateId,
                icon: 'fas fa-video'
            });
        }

        parametersContainer.innerHTML = params
            .map(
                (param) => `
            <div class="param-badge">
                <i class="${param.icon}"></i>
                <span class="label">${param.label}:</span>
                <span class="value">${param.value || 'Unknown'}</span>
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
                <div class="timeline-step ${iconClass}">
                    <div class="step-icon">
                        ${this.getStepIcon(step.id, iconClass)}
                    </div>
                    <div class="step-title">${step.name}</div>
                    <div class="step-status text-muted">${this.getStepStatusText(iconClass, timestamp)}</div>
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

        // Show monitoring button for completed jobs with Creatomate ID but no video URL
        if (status === 'completed' && this.jobData.creatomateId && !this.jobData.videoUrl) {
            if (this.jobData.workflowIncomplete) {
                // Workflow was incomplete - show warning button with different action
                buttons.push(`
                    <button class="btn btn-outline-danger" onclick="jobDetailApp.showWorkflowWarning()">
                        <i class="fas fa-exclamation-triangle me-1"></i> Workflow Issue
                    </button>
                `);
            } else {
                // Normal case - show monitoring button
                buttons.push(`
                    <button class="btn btn-outline-warning" onclick="jobDetailApp.monitorCreatomate()">
                        <i class="fas fa-eye me-1"></i> Check Video Status
                    </button>
                `);
            }
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
        console.log('🔄 Starting webhook-optimized updates (reduced polling)...');

        // Initialize RealtimeService for real-time events
        RealtimeService.init();

        // WEBHOOK-OPTIMIZED: Much longer intervals since webhooks provide real-time updates
        this.refreshInterval = setInterval(() => {
            // Stop refreshing if job is finished (but continue during rendering)
            if (['completed', 'failed', 'cancelled'].includes(this.jobData?.status) && this.jobData?.videoUrl) {
                // Only stop if truly completed (has video URL or is failed/cancelled)
                console.log('🛑 Job finished, stopping polling');
                this.stopRealTimeUpdates();
                return;
            }

            // WEBHOOK-OPTIMIZED: Reduced polling since webhooks handle real-time updates
            const isActive = this.jobData?.status === 'active' || this.jobData?.status === 'processing';
            const isRendering = this.jobData?.status === 'rendering';

            if (isActive || isRendering) {
                // Active/rendering jobs: only refresh every 2 minutes (webhooks handle real-time)
                const timeSinceLastUpdate = Date.now() - this.lastRefreshTime;
                if (timeSinceLastUpdate > 120000) {
                    // 2 minutes
                    this.refreshJobData();
                }
            } else {
                // Pending jobs: refresh every 5 minutes (webhooks handle transitions)
                const timeSinceLastUpdate = Date.now() - this.lastRefreshTime;
                if (timeSinceLastUpdate > 300000) {
                    // 5 minutes
                    this.refreshJobData();
                }
            }
        }, 60000); // Check every 1 minute instead of 15 seconds (major reduction!)

        // Start fetching real job logs from the server (also reduced frequency)
        this.startLogUpdates();
    }

    /**
     * Stop real-time updates when job is finished
     */
    stopRealTimeUpdates() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
            console.log('🛑 Stopped job refresh interval');
        }

        if (this.logUpdateInterval) {
            clearInterval(this.logUpdateInterval);
            this.logUpdateInterval = null;
            console.log('🛑 Stopped log update interval');
        }
    }

    /**
     * Start real log updates from server
     */
    startLogUpdates() {
        // Initial log fetch
        this.fetchRealLogs();

        // WEBHOOK-OPTIMIZED: Poll for logs every 30 seconds (webhooks add logs in real-time)
        this.logUpdateInterval = setInterval(() => {
            if (this.jobData && ['active', 'pending', 'processing', 'rendering'].includes(this.jobData.status)) {
                this.fetchRealLogs();
            } else if (['completed', 'failed', 'cancelled'].includes(this.jobData?.status)) {
                // Job finished - fetch final logs once and stop polling
                this.fetchRealLogs();
                clearInterval(this.logUpdateInterval);
                console.log('🛑 Job finished, stopped log polling');
            }
        }, 30000); // 30 seconds instead of 2 seconds (major reduction!)
    }

    /**
     * Fetch real logs from server
     */
    async fetchRealLogs() {
        try {
            const response = await fetch(`/api/queue/job/${this.jobId}/logs`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            if (result.success && result.data.logs) {
                this.updateLogDisplay(result.data.logs);
            }
        } catch (error) {
            console.error('❌ Failed to fetch job logs:', error);
            // Only show error if we haven't shown logs yet
            const logViewer = document.getElementById('log-viewer');
            if (logViewer && logViewer.children.length <= 1) {
                this.addLogEntry({
                    timestamp: new Date(),
                    level: 'error',
                    message: `Failed to fetch logs: ${error.message}\n\nThis could be due to network issues or the job not being found. Try refreshing the page.`
                });
            }
        }
    }

    /**
     * Update log display with real logs from server
     */
    updateLogDisplay(logs) {
        const logViewer = document.getElementById('log-viewer');
        if (!logViewer) return;

        // Clear existing logs first
        logViewer.innerHTML = '';

        if (logs.length === 0) {
            logViewer.innerHTML = `
                <div class="log-entry level-info">
                    <div class="log-icon">
                        <i class="fas fa-info-circle"></i>
                    </div>
                    <div class="log-timestamp">--:--:--</div>
                    <div class="log-content">
                        <strong>No logs available yet</strong><br>
                        Job processing hasn't started or logs are still being initialized.
                    </div>
                </div>
            `;
            return;
        }

        // Add all logs
        logs.forEach((logData) => {
            this.addLogEntry({
                timestamp: logData.timestamp,
                level: logData.type || 'info',
                message: logData.message
            });
        });

        // Auto-scroll to bottom if enabled
        if (this.autoScroll) {
            logViewer.scrollTop = logViewer.scrollHeight;
        }
    }

    /**
     * Add a professional log entry to the log viewer
     */
    addLogEntry(logData) {
        const logViewer = document.getElementById('log-viewer');
        if (!logViewer) return;

        const timestamp = new Date(logData.timestamp || new Date()).toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });

        const level = logData.level || 'info';
        const message = this.formatLogMessage(logData.message || '');
        const icon = this.getLogIcon(level);

        const logEntry = document.createElement('div');
        logEntry.className = `log-entry level-${level}`;
        logEntry.innerHTML = `
            <div class="log-icon">
                <i class="${icon}"></i>
            </div>
            <div class="log-timestamp">${timestamp}</div>
            <div class="log-content">${message}</div>
        `;

        logViewer.appendChild(logEntry);

        // Auto-scroll to bottom if enabled
        if (this.autoScroll) {
            logViewer.scrollTop = logViewer.scrollHeight;
        }

        // Keep only last 150 log entries for performance
        const maxEntries = 150;
        while (logViewer.children.length > maxEntries) {
            logViewer.removeChild(logViewer.firstChild);
        }
    }

    /**
     * Get icon for log level
     */
    getLogIcon(level) {
        const icons = {
            info: 'fas fa-info-circle',
            success: 'fas fa-check-circle',
            warning: 'fas fa-exclamation-triangle',
            error: 'fas fa-times-circle',
            step: 'fas fa-cog fa-spin',
            debug: 'fas fa-bug'
        };
        return icons[level] || icons.info;
    }

    /**
     * Format log message for better readability
     */
    formatLogMessage(message) {
        if (!message || typeof message !== 'string') return '';

        // Clean up the message
        let formattedMessage = message
            .trim()
            .replace(/\r\n/g, '\n') // Normalize line endings
            .replace(/\r/g, '\n') // Handle remaining \r
            .replace(/\n{3,}/g, '\n\n'); // Limit consecutive newlines

        // Highlight important patterns
        formattedMessage = formattedMessage
            // Highlight file paths and URLs
            .replace(/(\/[^\s]+\.(py|js|json|mp4|jpg|png|webp))/g, '<code>$1</code>')
            // Highlight URLs
            .replace(/(https?:\/\/[^\s]+)/g, '<code>$1</code>')
            // Highlight step indicators
            .replace(/Step (\d+)\/(\d+):/g, '<strong>Step $1/$2:</strong>')
            // Highlight success indicators
            .replace(/(✅|✓|SUCCESS|COMPLETED|DONE)/gi, '<strong style="color: #3fb950;">$1</strong>')
            // Highlight error indicators
            .replace(/(❌|✗|ERROR|FAILED|FAILURE)/gi, '<strong style="color: #f85149;">$1</strong>')
            // Highlight warning indicators
            .replace(/(⚠️|WARNING|WARN)/gi, '<strong style="color: #d29922;">$1</strong>')
            // Highlight processing indicators
            .replace(/(🎬|📝|🎨|🤖|⏳|📱)/g, '<strong>$1</strong>')
            // Highlight file sizes and durations
            .replace(/(\d+(?:\.\d+)?\s*(?:MB|KB|GB|s|ms|minutes?|seconds?))/gi, '<strong>$1</strong>')
            // Highlight percentages
            .replace(/(\d+(?:\.\d+)?%)/g, '<strong>$1</strong>');

        return formattedMessage;
    }

    /**
     * Refresh job data
     */
    async refreshJobData() {
        try {
            console.log('🔄 Refreshing job data...');

            // Store previous status to detect completion
            const previousStatus = this.jobData?.status;

            await this.loadJobData();
            this.lastRefreshTime = Date.now(); // Track refresh time for smart intervals
            console.log('✅ Job data refreshed');

            // Stop real-time updates if job just completed with video URL
            if (
                previousStatus &&
                ['active', 'pending', 'processing', 'rendering'].includes(previousStatus) &&
                this.jobData?.status === 'completed' &&
                this.jobData?.videoUrl
            ) {
                console.log('🏁 Job completed during refresh, stopping real-time updates');
                this.stopRealTimeUpdates();
            }
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

        // Store previous status to detect completion
        const previousStatus = this.jobData?.status;

        // Merge update data with current job data
        this.jobData = { ...this.jobData, ...updateData };

        // Update UI
        this.updateUI();

        // Stop real-time updates if job just completed with video
        if (
            previousStatus &&
            ['active', 'pending', 'processing', 'rendering'].includes(previousStatus) &&
            this.jobData.status === 'completed' &&
            this.jobData.videoUrl
        ) {
            console.log('🏁 Job completed with video, stopping real-time updates');
            this.stopRealTimeUpdates();
        }

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
            const timestamp = new Date().toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });

            logViewer.innerHTML = `
                <div class="log-entry level-info">
                    <div class="log-icon">
                        <i class="fas fa-broom"></i>
                    </div>
                    <div class="log-timestamp">${timestamp}</div>
                    <div class="log-content">
                        <strong>Log viewer cleared</strong><br>
                        Previous log entries have been removed from display.
                    </div>
                </div>
            `;
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

    /**
     * Manually trigger Creatomate monitoring for this job
     */
    async monitorCreatomate() {
        try {
            console.log(`🎬 Manual Creatomate monitoring trigger for job ${this.jobId}`);

            this.addLogEntry({
                level: 'info',
                message: 'Checking video render status with Creatomate...'
            });

            const response = await fetch(`/api/queue/job/${this.jobId}/monitor-creatomate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const result = await response.json();

            if (result.success) {
                this.addLogEntry({
                    level: 'success',
                    message: `Started monitoring Creatomate render ID: ${result.creatomateId}`
                });

                this.addLogEntry({
                    level: 'info',
                    message:
                        'Video status will be checked every 30 seconds. This page will update automatically when ready.'
                });

                // Refresh job data to show new status
                await this.refreshJobData();
            } else {
                this.addLogEntry({
                    level: 'error',
                    message: `Failed to start monitoring: ${result.message}`
                });

                if (result.details) {
                    this.addLogEntry({
                        level: 'warning',
                        message: result.details
                    });
                }
            }
        } catch (error) {
            console.error('❌ Failed to trigger Creatomate monitoring:', error);
            this.addLogEntry({
                level: 'error',
                message: `Failed to trigger monitoring: ${error.message}`
            });
        }
    }

    /**
     * Show workflow warning information
     */
    showWorkflowWarning() {
        this.addLogEntry({
            level: 'warning',
            message: '⚠️ Workflow Incomplete - The Python script did not complete all 7 steps properly'
        });

        this.addLogEntry({
            level: 'info',
            message: 'This job has a Creatomate ID but the workflow may not have submitted the video correctly.'
        });

        if (this.jobData.creatomateId) {
            this.addLogEntry({
                level: 'info',
                message: `Manual check: python main.py --check-creatomate ${this.jobData.creatomateId}`
            });
        }

        this.addLogEntry({
            level: 'info',
            message: 'Consider retrying this job to ensure all 7 workflow steps complete properly.'
        });
    }

    // Helper methods
    getStatusBadgeClass(status) {
        const classes = {
            pending: 'bg-warning text-dark',
            active: 'bg-info text-dark',
            processing: 'bg-info text-dark',
            rendering: 'bg-primary', // New rendering status
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
        const stepSize = 100 / this.processSteps.length; // Dynamic step size
        const step = Math.floor(progress / stepSize);
        return this.processSteps[Math.min(step, this.processSteps.length - 1)]?.description || 'Processing...';
    }

    getStepStatusText(iconClass, timestamp) {
        const statusTexts = {
            pending: 'Waiting...',
            active: 'In Progress',
            completed: timestamp ? `Done ${timestamp}` : 'Completed',
            failed: 'Failed'
        };
        return statusTexts[iconClass] || 'Unknown';
    }

    getProgressForStep(stepId) {
        const index = this.processSteps.findIndex((step) => step.id === stepId);
        return index !== -1 ? (index / this.processSteps.length) * 100 : 0;
    }

    getStepIcon(stepId, iconClass) {
        // Status-based icons
        if (iconClass === 'completed') return '✓';
        if (iconClass === 'failed') return '✗';
        if (iconClass === 'active') return '⟳';

        // Step-specific icons for pending state
        const stepIcons = {
            database_extraction: '🗄️',
            script_generation: '📝',
            asset_preparation: '🎨',
            heygen_creation: '🤖',
            heygen_processing: '⏳',
            scroll_generation: '📱',
            creatomate_assembly: '🎬'
        };

        return stepIcons[stepId] || '○';
    }

    getStepTimestamp(stepId) {
        // In a real implementation, this would return actual timestamps
        return new Date().toLocaleString();
    }

    getCurrentStepNumber() {
        const progress = this.jobData?.progress || 0;
        const stepNumber = Math.min(
            Math.floor(progress / (100 / this.processSteps.length)) + 1,
            this.processSteps.length
        );
        return `${stepNumber}/${this.processSteps.length}`;
    }

    calculateDuration() {
        if (!this.jobData?.startedAt) return '--';

        const start = new Date(this.jobData.startedAt);

        // For completed, failed, or cancelled jobs, use completedAt timestamp
        // Otherwise use current time for active jobs
        let end;
        if (['completed', 'failed', 'cancelled'].includes(this.jobData.status)) {
            end = this.jobData.completedAt ? new Date(this.jobData.completedAt) : new Date(this.jobData.startedAt);
        } else {
            end = new Date(); // Keep timer running for active jobs
        }

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
