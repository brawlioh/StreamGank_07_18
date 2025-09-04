/**
 * Navigation Component - Professional navigation bar
 * Provides consistent navigation across all pages with active states
 */

import Router from '../core/Router.js';

export class Navigation {
    constructor() {
        this.currentRoute = null;
        this.navigationData = {
            brand: {
                title: 'StreamGank',
                subtitle: 'AMBUSH THE BEST VOD TOGETHER',
                version: 'BETA v1.3'
            },
            links: [
                {
                    path: '/dashboard',
                    label: 'Dashboard',
                    icon: '📊',
                    description: 'Video generation and queue management'
                },
                {
                    path: '/jobs',
                    label: 'Jobs',
                    icon: '📋',
                    description: 'View all jobs and their status'
                }
            ]
        };
    }

    /**
     * Initialize navigation component
     */
    init() {
        this.setupRouterListener();
    }

    /**
     * Setup router event listener to update active states
     */
    setupRouterListener() {
        Router.addEventListener('routeChange', (event) => {
            this.currentRoute = event.detail.path;
            this.updateActiveStates();
        });
    }

    /**
     * Render navigation bar
     * @param {Object} options - Navigation options
     * @returns {string} Navigation HTML
     */
    render(options = {}) {
        const { showBrand = true, showVersion = true, showLogin = true, fixed = false, theme = 'default' } = options;

        return `
            <nav class="streamgank-navbar ${fixed ? 'fixed-top' : ''} ${theme}">
                <div class="container-fluid">
                    <div class="row py-2 align-items-center w-100">
                        <!-- Brand Section -->
                        ${showBrand ? this.renderBrand(showVersion) : ''}
                        
                        <!-- Navigation Links -->
                        <div class="col-auto navigation-links">
                            ${this.renderNavigationLinks()}
                        </div>
                        
                        <!-- Actions Section -->
                        <div class="col-auto ms-auto">
                            <div class="navbar-actions d-flex align-items-center gap-2">
                                ${this.renderStatusIndicator()}
                                ${this.renderQuickActions()}
                                ${showLogin ? this.renderLoginButton() : ''}
                            </div>
                        </div>
                    </div>
                </div>
            </nav>
        `;
    }

    /**
     * Render brand section
     * @param {boolean} showVersion - Whether to show version
     * @returns {string} Brand HTML
     */
    renderBrand(showVersion) {
        return `
            <div class="col">
                <a href="/dashboard" class="brand-container d-flex align-items-center text-decoration-none">
                    <h1 class="brand-title mb-0">
                        ${this.navigationData.brand.title}
                        <span class="text-accent">Gank</span>
                    </h1>
                    ${
                        showVersion
                            ? `
                    <span class="version-badge ms-2">${this.navigationData.brand.version}</span>
                    `
                            : ''
                    }
                </a>
                <span class="brand-subtitle d-block">${this.navigationData.brand.subtitle}</span>
            </div>
        `;
    }

    /**
     * Render navigation links
     * @returns {string} Navigation links HTML
     */
    renderNavigationLinks() {
        return this.navigationData.links
            .map((link) => {
                const isActive = this.isActiveRoute(link.path);

                return `
                <a href="${link.path}" 
                   class="nav-link btn ${isActive ? 'btn-primary' : 'btn-outline-primary'} me-2"
                   data-route="${link.path}"
                   title="${link.description}">
                    <span class="nav-icon">${link.icon}</span>
                    <span class="nav-label">${link.label}</span>
                </a>
            `;
            })
            .join('');
    }

    /**
     * Render status indicator
     * @returns {string} Status indicator HTML
     */
    renderStatusIndicator() {
        return `
            <div class="status-indicator d-none d-md-flex align-items-center me-3">
                <div class="connection-status me-2" id="nav-connection-status">
                    <div class="status-dot bg-success" title="Connected"></div>
                </div>
                <div class="queue-summary" id="nav-queue-summary">
                    <small class="text-muted">
                        Queue: <span id="nav-queue-count" class="badge bg-info">0</span>
                    </small>
                </div>
            </div>
        `;
    }

    /**
     * Render quick actions
     * @returns {string} Quick actions HTML
     */
    renderQuickActions() {
        return `
            <div class="quick-actions d-flex gap-1">
                <button class="btn btn-outline-secondary btn-sm" 
                        id="nav-refresh-btn"
                        title="Refresh Status">
                    🔄
                </button>
                <div class="dropdown">
                    <button class="btn btn-outline-secondary btn-sm dropdown-toggle" 
                            type="button" 
                            data-bs-toggle="dropdown">
                        ⚙️
                    </button>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="#" onclick="toggleQueueDashboard()">Queue Dashboard</a></li>
                        <li><a class="dropdown-item" href="#" onclick="clearAllLogs()">Clear Logs</a></li>
                        <li><hr class="dropdown-divider"></li>
                        <li><a class="dropdown-item" href="#" onclick="showAppStatus()">App Status</a></li>
                    </ul>
                </div>
            </div>
        `;
    }

    /**
     * Render login button
     * @returns {string} Login button HTML
     */
    renderLoginButton() {
        return `
            <button class="btn btn-primary login-btn">
                👤 LOGIN
            </button>
        `;
    }

    /**
     * Check if route is currently active
     * @param {string} path - Path to check
     * @returns {boolean} Whether route is active
     */
    isActiveRoute(path) {
        if (!this.currentRoute) {
            this.currentRoute = window.location.pathname;
        }

        // Exact match
        if (this.currentRoute === path) {
            return true;
        }

        // Special cases
        if (path === '/dashboard' && (this.currentRoute === '/' || this.currentRoute === '')) {
            return true;
        }

        if (path === '/jobs' && this.currentRoute.startsWith('/job/')) {
            return true;
        }

        return false;
    }

    /**
     * Update active states after route change
     */
    updateActiveStates() {
        const navLinks = document.querySelectorAll('.nav-link[data-route]');

        navLinks.forEach((link) => {
            const routePath = link.getAttribute('data-route');
            const isActive = this.isActiveRoute(routePath);

            // Handle professional nav links
            if (link.classList.contains('professional-nav-link')) {
                if (isActive) {
                    link.classList.remove('btn-outline-light');
                    link.classList.add('btn-light', 'active');
                } else {
                    link.classList.remove('btn-light', 'active');
                    link.classList.add('btn-outline-light');
                }
            } else {
                // Legacy nav links
                if (isActive) {
                    link.classList.remove('btn-outline-primary');
                    link.classList.add('btn-primary');
                } else {
                    link.classList.remove('btn-primary');
                    link.classList.add('btn-outline-primary');
                }
            }
        });

        // Update queue counter
        this.updateQueueCounter();
    }

    /**
     * Update queue counter display
     */
    updateQueueCounter() {
        const queueCounter = document.getElementById('nav-queue-count');
        if (queueCounter && this.navigationData.queue) {
            const totalJobs = (this.navigationData.queue.pending || 0) + (this.navigationData.queue.processing || 0);
            queueCounter.textContent = totalJobs;

            // Update counter styling based on job count
            if (totalJobs === 0) {
                queueCounter.className = 'badge bg-secondary ms-2 queue-counter';
                queueCounter.style.display = 'none';
            } else if (totalJobs > 5) {
                queueCounter.className = 'badge bg-danger ms-2 queue-counter';
                queueCounter.style.display = 'flex';
            } else {
                queueCounter.className = 'badge bg-warning ms-2 queue-counter';
                queueCounter.style.display = 'flex';
            }
        }
    }

    /**
     * Update navigation status indicators
     * @param {Object} status - Status data
     */
    updateStatus(status) {
        // Update connection status
        const connectionStatus = document.getElementById('nav-connection-status');
        if (connectionStatus) {
            const dot = connectionStatus.querySelector('.status-dot');
            if (status.connected) {
                dot.className = 'status-dot bg-success';
                dot.title = `Connected via ${status.connectionType || 'unknown'}`;
            } else {
                dot.className = 'status-dot bg-warning';
                dot.title = 'Disconnected - using fallback';
            }
        }

        // Update queue count
        const queueCount = document.getElementById('nav-queue-count');
        if (queueCount && status.queue) {
            const totalJobs = (status.queue.pending || 0) + (status.queue.processing || 0);
            queueCount.textContent = totalJobs;
            queueCount.className = totalJobs > 0 ? 'badge bg-warning' : 'badge bg-info';
        }
    }

    /**
     * Setup navigation event handlers
     */
    setupEventHandlers() {
        // Handle navigation link clicks
        document.addEventListener('click', (event) => {
            const navLink = event.target.closest('.nav-link[data-route]');
            if (navLink) {
                event.preventDefault();
                const route = navLink.getAttribute('data-route');
                Router.navigate(route);
            }
        });

        // Handle refresh button
        const refreshBtn = document.getElementById('nav-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                // Emit refresh event that other components can listen to
                window.dispatchEvent(new CustomEvent('nav-refresh-requested'));
            });
        }
    }

    /**
     * Add custom navigation link
     * @param {Object} linkConfig - Link configuration
     */
    addNavigationLink(linkConfig) {
        this.navigationData.links.push(linkConfig);
    }

    /**
     * Remove navigation link
     * @param {string} path - Path of link to remove
     */
    removeNavigationLink(path) {
        this.navigationData.links = this.navigationData.links.filter((link) => link.path !== path);
    }

    /**
     * Get current navigation state
     * @returns {Object} Navigation state
     */
    getState() {
        return {
            currentRoute: this.currentRoute,
            links: this.navigationData.links
        };
    }

    /**
     * Cleanup navigation resources
     */
    cleanup() {
        // Remove event listeners if needed
        console.log('🧭 Navigation Component cleaned up');
    }
}

// Global functions for dropdown actions
window.toggleQueueDashboard = () => {
    const dashboard = document.getElementById('queue-dashboard');
    if (dashboard) {
        dashboard.style.display = dashboard.style.display === 'none' ? 'block' : 'none';
    }
};

window.clearAllLogs = () => {
    if (confirm('Clear all status messages?')) {
        const statusMessages = document.getElementById('status-messages');
        if (statusMessages) {
            statusMessages.innerHTML = '';
        }
    }
};

window.showAppStatus = () => {
    // This could open a modal with app status information
    alert('App Status: OK\nConnection: Active\nBuild: Production');
};

// Export singleton instance
export default new Navigation();
