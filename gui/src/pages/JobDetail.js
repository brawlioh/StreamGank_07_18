/**
 * JobDetail Page - Individual job information and monitoring
 * Shows detailed job progress, logs, and results
 */

import UIManager from '../components/UIManager.js';
import APIService from '../services/APIService.js';
import JobManager from '../services/JobManager.js';

export class JobDetailPage {
    constructor() {
        this.currentJobId = null;
        this.jobData = null;
        this.refreshTimer = null;
        this.refreshInterval = 5000; // 5 seconds
    }

    /**
     * Render the job detail page
     * @param {HTMLElement} container - Container to render into
     * @param {Object} params - Route parameters (contains jobId)
     */
    async render(container, params = {}) {
        console.log('📄 JobDetail.render() called with:', { container: !!container, params });

        const { jobId } = params;
        console.log('📄 JobDetail extracted jobId:', jobId);

        if (!container) {
            console.error('📄 JobDetail: No container provided');
            return;
        }

        if (!jobId) {
            console.error('📄 JobDetail: No job ID provided');
            console.error('📄 JobDetail: Full params received:', JSON.stringify(params, null, 2));
            this.renderError(container, 'No job ID specified');
            return;
        }

        this.currentJobId = jobId;

        // Show loading state first
        container.innerHTML = this.createLoadingTemplate();

        try {
            // Fetch job data
            await this.loadJobData(jobId);

            // Render job details
            container.innerHTML = this.createJobTemplate();

            // Start auto-refresh for active jobs
            this.startAutoRefresh();

            console.log(`📄 JobDetail rendered for job: ${jobId}`);
        } catch (error) {
            console.error('📄 JobDetail render error:', error);
            this.renderError(container, error.message);
        }
    }

    /**
     * Load job data from API or local storage
     * @param {string} jobId - Job ID to load
     */
    async loadJobData(jobId) {
        try {
            // First try to get from JobManager (active jobs)
            let job = JobManager.getJob(jobId);

            if (!job) {
                // If not in JobManager, try API
                const response = await APIService.getJobStatus(jobId);
                if (response.success) {
                    job = response.job;
                }
            }

            if (!job) {
                throw new Error(`Job ${jobId} not found`);
            }

            this.jobData = job;

            // Update page title
            document.title = `Job ${jobId} - StreamGank`;
        } catch (error) {
            throw new Error(`Failed to load job data: ${error.message}`);
        }
    }

    /**
     * Create loading template
     * @returns {string} Loading HTML
     */
    createLoadingTemplate() {
        return `
            <div class="job-detail-page">
                <div class="container-fluid">
                    <!-- Header with navigation -->
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <div>
                            <button class="btn btn-outline-secondary me-3" onclick="history.back()">
                                ← Back
                            </button>
                            <h1 class="h3 mb-0">Loading Job...</h1>
                        </div>
                        <div class="nav-links">
                            <a href="/dashboard" class="btn btn-outline-primary me-2">Dashboard</a>
                        </div>
                    </div>
                    
                    <!-- Loading State -->
                    <div class="text-center py-5">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mt-3 text-light">Loading job details...</p>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Create main job detail template - COPIED FROM job-detail.html
     * @returns {string} Job detail HTML
     */
    createJobTemplate() {
        const job = this.jobData;
        const statusClass = this.getStatusClass(job.status);
        const statusIcon = this.getStatusIcon(job.status);

        return `
            <style>
              /* Fix container overflow */
              .main-content {
                overflow-x: hidden !important;
              }
              
              /* Compact Timeline Styles */
              .timeline-compact {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 0.75rem;
                padding: 0;
              }
              .timeline-step {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid #495057;
                border-radius: 8px;
                padding: 0.75rem;
                text-align: center;
                position: relative;
                transition: all 0.3s ease;
              }
              .timeline-step.completed {
                border-color: #198754;
                background: rgba(25, 135, 84, 0.1);
              }
              .timeline-step.active {
                border-color: #0d6efd;
                background: rgba(13, 110, 253, 0.1);
                animation: pulse 2s infinite;
              }
              .timeline-step.pending {
                border-color: #6c757d;
                background: rgba(108, 117, 125, 0.1);
              }
              .timeline-step.failed {
                border-color: #dc3545;
                background: rgba(220, 53, 69, 0.1);
              }

              .step-icon {
                font-size: 1.5rem;
                margin-bottom: 0.5rem;
              }
              .step-title {
                font-size: 0.8rem;
                font-weight: 600;
                margin: 0;
                color: #fff;
              }
              .step-status {
                font-size: 0.7rem;
                margin-top: 0.25rem;
                opacity: 0.8;
              }

              /* Compact Cards */
              .compact-card {
                margin-bottom: 1rem;
              }
              .compact-card .card-header {
                padding: 0.5rem 1rem;
                font-size: 0.9rem;
              }
              .compact-card .card-body {
                padding: 1rem;
              }

              /* Override for video result section - extra compact */
              #creatomate-section .card-header {
                padding: 0.5rem 0.75rem !important;
              }
              #creatomate-section .card-body {
                padding: 0.5rem 0.75rem !important;
              }

              /* Progress Bar Compact */
              .progress-compact {
                height: 12px;
                border-radius: 6px;
                background: #343a40;
              }

              /* Parameter Inline Display - NO CARDS */
              .param-inline {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                align-items: center;
              }
              .param-badge {
                display: inline-flex;
                align-items: center;
                gap: 0.3rem;
                padding: 0.25rem 0.4rem;
                border-radius: 4px;
                background: rgba(13, 110, 253, 0.1);
                border: 1px solid rgba(13, 110, 253, 0.3);
                font-size: 0.75rem;
                max-width: 100%;
                overflow: hidden;
              }
              .param-badge i {
                font-size: 0.7rem;
                color: #0d6efd;
              }
              .param-badge .label {
                color: #e6edf3;
                margin-right: 0.25rem;
              }
              .param-badge .value {
                color: #fff;
                font-weight: 500;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                max-width: 120px;
              }

              /* Stats Compact */
              .stats-row {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 0.4rem;
              }
              .stat-item {
                text-align: center;
                padding: 0.4rem 0.2rem;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                min-width: 0;
                overflow: hidden;
              }
              .stat-value {
                font-size: 1rem;
                font-weight: bold;
                margin-bottom: 0.25rem;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
              }
              .stat-label {
                font-size: 0.65rem;
                color: #e6edf3;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
              }

              /* Video player fixes */
              #result-video {
                width: 100%;
                height: auto;
                display: block !important;
                background: #000;
                object-fit: contain;
              }

              #result-video::-webkit-media-controls-panel {
                background-color: rgba(0, 0, 0, 0.8);
              }

              /* Video container spacing */
              .video-container {
                max-width: 600px;
                width: 100%;
                position: relative;
                background: #1a1a1a;
                border-radius: 8px;
                overflow: hidden;
                min-height: 200px;
                display: flex;
                align-items: center;
                justify-content: center;
              }

              /* Compact video container for inline display */
              .video-container-compact {
                width: 100%;
                position: relative;
                background: #1a1a1a;
                border-radius: 6px;
                overflow: hidden;
                min-height: 160px;
                display: flex;
                align-items: center;
                justify-content: center;
              }

              /* Collapsible sections */
              .section-toggle {
                cursor: pointer;
                user-select: none;
              }
              .section-toggle:hover {
                background: rgba(255, 255, 255, 0.1);
              }

              @keyframes pulse {
                0%,
                100% {
                  transform: scale(1);
                }
                50% {
                  transform: scale(1.05);
                }
              }

              /* Responsive adjustments */
              @media (max-width: 768px) {
                .timeline-compact {
                  grid-template-columns: repeat(2, 1fr);
                  gap: 0.5rem;
                }
                .param-inline {
                  gap: 0.4rem;
                }
                .stats-row {
                  grid-template-columns: repeat(2, 1fr);
                  gap: 0.3rem;
                }
                .param-badge {
                  font-size: 0.7rem;
                  padding: 0.2rem 0.3rem;
                }
                .stat-value {
                  font-size: 0.9rem;
                }
                .stat-label {
                  font-size: 0.6rem;
                }
              }
              
              @media (max-width: 576px) {
                .timeline-compact {
                  grid-template-columns: 1fr;
                }
                .stats-row {
                  grid-template-columns: repeat(2, 1fr);
                }
                .container-fluid {
                  padding-left: 0.5rem !important;
                  padding-right: 0.5rem !important;
                }
              }
            </style>

            <div id="job-detail-app" class="w-100" style="background-color: #0d1117; overflow-x: hidden;">
              <!-- Main Content -->
              <div id="main-content" style="overflow-x: hidden;">
                <!-- Compact Header -->
                <nav class="navbar navbar-dark bg-dark border-bottom border-secondary py-2">
                  <div class="container-fluid">
                    <div class="d-flex align-items-center">
                      <button onclick="history.back()" class="btn btn-outline-light btn-sm me-2">
                        <i class="fas fa-arrow-left"></i>
                      </button>
                      <span class="navbar-brand mb-0 h6">
                        <i class="fas fa-tasks me-1"></i>
                        Job
                        <span id="job-id">${job.id}</span>
                      </span>
                      <span class="badge ${statusClass} ms-2 fs-6">${statusIcon} ${job.status.toUpperCase()}</span>
                    </div>
                    <div class="d-flex gap-1">
                      <button onclick="location.reload()" class="btn btn-outline-primary btn-sm">
                        <i class="fas fa-sync-alt"></i>
                      </button>
                      <a href="/dashboard" class="btn btn-primary btn-sm">
                        <i class="fas fa-tachometer-alt"></i>
                      </a>
                    </div>
                  </div>
                </nav>

                <div class="container-fluid py-2" style="overflow-x: hidden;">
                  <!-- Progress & Stats Row -->
                  <div class="row g-2 mb-3">
                    <!-- Progress Section -->
                    <div class="col-md-8">
                      <div class="card bg-dark compact-card">
                        <div class="card-header">
                          <i class="fas fa-chart-line me-1"></i>
                          Progress
                          <span class="float-end">${job.progress || 0}%</span>
                        </div>
                        <div class="card-body">
                          <div class="progress progress-compact mb-2">
                            <div
                              class="progress-bar ${this.getProgressClass(job.progress)} progress-bar-striped progress-bar-animated"
                              style="width: ${job.progress || 0}%"
                            ></div>
                          </div>
                          <small class="text-light">${job.currentStep || 'Initializing...'}</small>
                        </div>
                      </div>
                    </div>

                    <!-- Quick Stats -->
                    <div class="col-md-4">
                      <div class="card bg-dark compact-card">
                        <div class="card-header">
                          <i class="fas fa-info-circle me-1"></i>
                          Stats
                        </div>
                        <div class="card-body">
                          <div class="stats-row">
                            <div class="stat-item">
                              <div class="stat-value text-primary">${this.calculateDuration(job)}</div>
                              <div class="stat-label">Duration</div>
                            </div>
                            <div class="stat-item">
                              <div class="stat-value text-info">7/7</div>
                              <div class="stat-label">Steps</div>
                            </div>
                            <div class="stat-item">
                              <div class="stat-value text-warning">ynlv</div>
                              <div class="stat-label">Worker</div>
                            </div>
                            <div class="stat-item">
                              <div class="stat-value text-success">Normal</div>
                              <div class="stat-label">Priority</div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Parameters -->
                  <div class="card bg-dark compact-card">
                    <div class="card-header section-toggle" data-bs-toggle="collapse" data-bs-target="#params-section">
                      <i class="fas fa-cog me-1"></i>
                      Job Parameters
                      <i class="fas fa-chevron-down float-end"></i>
                    </div>
                    <div id="params-section" class="collapse show">
                      <div class="card-body">
                        <div class="param-inline">
                          <div class="param-badge">
                            <i class="fas fa-globe"></i>
                            <span class="label">Country:</span>
                            <span class="value">${job.parameters?.country || job.params?.country || 'N/A'}</span>
                          </div>
                          <div class="param-badge">
                            <i class="fas fa-tv"></i>
                            <span class="label">Platform:</span>
                            <span class="value">${job.parameters?.platform || job.params?.platform || 'N/A'}</span>
                          </div>
                          <div class="param-badge">
                            <i class="fas fa-film"></i>
                            <span class="label">Genre:</span>
                            <span class="value">${job.parameters?.genre || job.params?.genre || 'N/A'}</span>
                          </div>
                          <div class="param-badge">
                            <i class="fas fa-tag"></i>
                            <span class="label">Content Type:</span>
                            <span class="value">${job.parameters?.contentType || job.params?.contentType || 'N/A'}</span>
                          </div>
                          <div class="param-badge">
                            <i class="fas fa-palette"></i>
                            <span class="label">Template:</span>
                            <span class="value">${job.parameters?.template || job.params?.template || 'Default'}</span>
                          </div>
                          ${
                              job.workerId
                                  ? `
                          <div class="param-badge">
                            <i class="fas fa-user"></i>
                            <span class="label">Worker ID:</span>
                            <span class="value">${job.workerId}</span>
                          </div>
                          `
                                  : ''
                          }
                          ${
                              job.creatomateId
                                  ? `
                          <div class="param-badge">
                            <i class="fas fa-video"></i>
                            <span class="label">Creatomate ID:</span>
                            <span class="value">${job.creatomateId}</span>
                          </div>
                          `
                                  : ''
                          }
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Process Timeline -->
                  <div class="card bg-dark compact-card">
                    <div class="card-header section-toggle" data-bs-toggle="collapse" data-bs-target="#timeline-section">
                      <i class="fas fa-list-check me-1"></i>
                      Process Timeline
                      <i class="fas fa-chevron-down float-end"></i>
                    </div>
                    <div id="timeline-section" class="collapse show">
                      <div class="card-body">
                        <div class="timeline-compact">
                          <div class="timeline-step completed">
                            <div class="step-icon">📊</div>
                            <div class="step-title">Database Extraction</div>
                            <div class="step-status">Done 9/2/2025, 12:45:21 AM</div>
                          </div>
                          <div class="timeline-step completed">
                            <div class="step-icon">📝</div>
                            <div class="step-title">Script Generation</div>
                            <div class="step-status">Done 9/2/2025, 12:45:21 AM</div>
                          </div>
                          <div class="timeline-step completed">
                            <div class="step-icon">🎨</div>
                            <div class="step-title">Asset Preparation</div>
                            <div class="step-status">Done 9/2/2025, 12:45:21 AM</div>
                          </div>
                          <div class="timeline-step completed">
                            <div class="step-icon">🎬</div>
                            <div class="step-title">HeyGen Video Creation</div>
                            <div class="step-status">Done 9/2/2025, 12:45:21 AM</div>
                          </div>
                          <div class="timeline-step completed">
                            <div class="step-icon">⏳</div>
                            <div class="step-title">HeyGen Processing</div>
                            <div class="step-status">Done 9/2/2025, 12:45:21 AM</div>
                          </div>
                          <div class="timeline-step completed">
                            <div class="step-icon">📱</div>
                            <div class="step-title">Scroll Video Generation</div>
                            <div class="step-status">Done 9/2/2025, 12:45:21 AM</div>
                          </div>
                          <div class="timeline-step completed">
                            <div class="step-icon">🎞️</div>
                            <div class="step-title">Creatomate Assembly</div>
                            <div class="step-status">Ready</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Compact Video Result Section -->
                  ${
                      job.videoUrl || job.creatomateId
                          ? `
                  <div class="card bg-dark compact-card">
                    <div class="card-header py-2">
                      <div class="d-flex align-items-center justify-content-between">
                        <div class="d-flex align-items-center">
                          <i class="fas fa-film me-2 text-primary"></i>
                          <span class="fw-bold">Video Result</span>
                          <span class="badge bg-success ms-2">Ready</span>
                        </div>
                        <div class="d-flex gap-1">
                          <button class="btn btn-sm btn-outline-primary">
                            <i class="fas fa-sync-alt me-1"></i>
                            Refresh Status
                          </button>
                        </div>
                      </div>
                    </div>
                    <div class="card-body py-2">
                      ${
                          job.creatomateId
                              ? `
                      <!-- Compact Creatomate Info -->
                      <div class="mb-2">
                        <div class="d-flex align-items-center text-sm">
                          <span class="text-light me-2">ID:</span>
                          <code class="text-info small">${job.creatomateId}</code>
                        </div>
                      </div>
                      `
                              : ''
                      }

                      ${
                          job.videoUrl
                              ? `
                      <!-- Compact Video Player -->
                      <div class="row g-2">
                        <div class="col-md-7">
                          <div class="video-container-compact">
                            <video
                              controls
                              preload="metadata"
                              muted
                              playsinline
                              class="w-100"
                              style="max-height: 580px; border-radius: 6px; position: relative; z-index: 2"
                            >
                              <source src="${job.videoUrl}" type="video/mp4" />
                              Your browser does not support the video tag.
                            </video>
                          </div>
                        </div>
                        <div class="col-md-5">
                          <div class="d-grid gap-1">
                            <a href="${job.videoUrl}" download class="btn btn-sm btn-success">
                              <i class="fas fa-download me-1"></i>
                              Download
                            </a>
                            <button onclick="navigator.clipboard.writeText('${job.videoUrl}')" class="btn btn-sm btn-outline-info">
                              <i class="fas fa-copy me-1"></i>
                              Copy URL
                            </button>
                            <button onclick="document.querySelector('video').requestFullscreen()" class="btn btn-sm btn-outline-secondary">
                              <i class="fas fa-expand me-1"></i>
                              Fullscreen
                            </button>
                          </div>
                        </div>
                      </div>
                      `
                              : ''
                      }
                    </div>
                  </div>
                  `
                          : ''
                  }

                  <!-- Error Information -->
                  ${
                      job.error
                          ? `
                  <div class="card bg-dark border-danger compact-card">
                    <div class="card-header bg-danger">
                      <i class="fas fa-exclamation-triangle me-1"></i>
                      Error Details
                    </div>
                    <div class="card-body">
                      <div class="text-light" style="font-size: 0.8rem">
                        ${job.error}
                      </div>
                    </div>
                  </div>
                  `
                          : ''
                  }
                </div>
              </div>
            </div>
        `;
    }

    /**
     * Create action buttons based on job status
     * @param {Object} job - Job data
     * @returns {string} Action buttons HTML
     */
    createActionButtons(job) {
        const buttons = [];

        if (job.status === 'processing' || job.status === 'pending') {
            buttons.push(`
                <button class="btn btn-warning me-2" onclick="cancelJob('${job.id}')">
                    ⏹️ Cancel Job
                </button>
            `);
        }

        if (job.status === 'failed') {
            buttons.push(`
                <button class="btn btn-primary me-2" onclick="retryJob('${job.id}')">
                    🔄 Retry Job
                </button>
            `);
        }

        buttons.push(`
            <button class="btn btn-outline-secondary me-2" onclick="refreshJobData('${job.id}')">
                🔄 Refresh
            </button>
        `);

        return buttons.join('');
    }

    /**
     * Create timeline HTML
     * @param {Object} job - Job data
     * @returns {string} Timeline HTML
     */
    createTimeline(job) {
        const events = [];

        events.push({
            time: job.createdAt,
            status: 'created',
            message: 'Job created and queued'
        });

        if (job.startedAt) {
            events.push({
                time: job.startedAt,
                status: 'started',
                message: 'Job processing started'
            });
        }

        if (job.completedAt) {
            events.push({
                time: job.completedAt,
                status: 'completed',
                message: 'Job completed successfully'
            });
        }

        return events
            .map(
                (event) => `
            <div class="timeline-item mb-3">
                <div class="d-flex align-items-start">
                    <div class="timeline-icon me-3">
                        ${this.getStatusIcon(event.status)}
                    </div>
                    <div class="timeline-content">
                        <p class="mb-1 fw-medium">${event.message}</p>
                        <small class="text-light">${this.formatDate(event.time)}</small>
                    </div>
                </div>
            </div>
        `
            )
            .join('');
    }

    /**
     * Create video result section
     * @param {Object} job - Job data
     * @returns {string} Video result HTML
     */
    createVideoResult(job) {
        return `
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0">🎬 Video Result</h5>
                </div>
                <div class="card-body">
                    <video controls class="w-100 mb-3" style="max-height: 400px;">
                        <source src="${job.videoUrl}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                    <div class="d-flex gap-2">
                        <a href="${job.videoUrl}" target="_blank" class="btn btn-primary">
                            🔗 Open Video
                        </a>
                        <a href="${job.videoUrl}" download class="btn btn-outline-secondary">
                            💾 Download
                        </a>
                        <button class="btn btn-outline-info" onclick="copyToClipboard('${job.videoUrl}')">
                            📋 Copy URL
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Start auto-refresh timer for active jobs
     */
    startAutoRefresh() {
        this.stopAutoRefresh();

        if (this.jobData && ['pending', 'processing'].includes(this.jobData.status)) {
            this.refreshTimer = setInterval(() => {
                this.refreshJobData(this.currentJobId);
            }, this.refreshInterval);

            console.log(`📄 Auto-refresh started for job ${this.currentJobId}`);
        }
    }

    /**
     * Stop auto-refresh timer
     */
    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    /**
     * Refresh job data
     * @param {string} jobId - Job ID to refresh
     */
    async refreshJobData(jobId) {
        try {
            await this.loadJobData(jobId);

            // Re-render if we're still on the same job
            if (this.currentJobId === jobId) {
                const container = document.querySelector('.job-detail-page').parentElement;
                await this.render(container, { jobId });
            }
        } catch (error) {
            console.error('📄 Failed to refresh job data:', error);
        }
    }

    /**
     * Render error state
     * @param {HTMLElement} container - Container element
     * @param {string} message - Error message
     */
    renderError(container, message) {
        container.innerHTML = `
            <div class="job-detail-page">
                <div class="container-fluid">
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <div>
                            <button class="btn btn-outline-secondary me-3" onclick="history.back()">
                                ← Back
                            </button>
                            <h1 class="h3 mb-0">Job Not Found</h1>
                        </div>
                        <div class="nav-links">
                            <a href="/dashboard" class="btn btn-outline-primary me-2">Dashboard</a>
                        </div>
                    </div>
                    
                    <div class="alert alert-danger">
                        <h4 class="alert-heading">❌ Error</h4>
                        <p class="mb-0">${message}</p>
                        <hr>
                        <a href="/dashboard" class="btn btn-primary">Return to Dashboard</a>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Handle page activation
     */
    activate(params) {
        console.log(`📄 JobDetail activated for job: ${params.jobId}`);
    }

    /**
     * Handle page deactivation
     */
    deactivate() {
        this.stopAutoRefresh();
        console.log('📄 JobDetail deactivated');
    }

    /**
     * Get status CSS class
     * @param {string} status - Job status
     * @returns {string} CSS class
     */
    getStatusClass(status) {
        const classes = {
            pending: 'bg-warning',
            processing: 'bg-info',
            completed: 'bg-success',
            failed: 'bg-danger',
            cancelled: 'bg-secondary'
        };
        return classes[status] || 'bg-secondary';
    }

    /**
     * Get status icon
     * @param {string} status - Job status
     * @returns {string} Icon
     */
    getStatusIcon(status) {
        const icons = {
            created: '➕',
            started: '▶️',
            pending: '⏳',
            processing: '🔄',
            completed: '✅',
            failed: '❌',
            cancelled: '⏹️'
        };
        return icons[status] || '📄';
    }

    /**
     * Get progress bar CSS class
     * @param {number} progress - Progress percentage
     * @returns {string} CSS class
     */
    getProgressClass(progress) {
        if (progress >= 100) {
            return 'bg-success';
        }
        if (progress >= 75) {
            return 'bg-info';
        }
        if (progress >= 50) {
            return 'bg-warning';
        }
        return 'bg-primary';
    }

    /**
     * Format date for display
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted date
     */
    formatDate(dateString) {
        if (!dateString) {
            return 'N/A';
        }
        return new Date(dateString).toLocaleString();
    }

    /**
     * Calculate job duration
     * @param {Object} job - Job data
     * @returns {string} Duration string
     */
    calculateDuration(job) {
        if (!job.startedAt) {
            return 'Not started';
        }

        const start = new Date(job.startedAt);
        const end = job.completedAt ? new Date(job.completedAt) : new Date();
        const duration = end - start;

        return UIManager.formatDuration(duration);
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.stopAutoRefresh();
        console.log('📄 JobDetail Page cleaned up');
    }
}

// Global functions for button actions (called from template)
window.cancelJob = async (jobId) => {
    if (confirm('Are you sure you want to cancel this job?')) {
        try {
            const result = await JobManager.cancelJob(jobId);
            if (result) {
                location.reload();
            }
        } catch (error) {
            alert(`Failed to cancel job: ${error.message}`);
        }
    }
};

window.retryJob = (_jobId) => {
    alert('Retry functionality not yet implemented');
};

window.refreshJobData = (_jobId) => {
    location.reload();
};

window.checkCreatomateStatus = async (creatomateId) => {
    try {
        const result = await APIService.getCreatomateStatus(creatomateId);
        if (result.success) {
            alert(`Creatomate Status: ${result.status}\nProgress: ${result.progress || 'N/A'}%`);
        } else {
            alert(`Error: ${result.message}`);
        }
    } catch (error) {
        alert(`Error checking status: ${error.message}`);
    }
};

window.copyToClipboard = async (text) => {
    try {
        await navigator.clipboard.writeText(text);
        alert('URL copied to clipboard!');
    } catch (error) {
        alert('Failed to copy URL');
    }
};

// Export singleton instance
export default new JobDetailPage();
