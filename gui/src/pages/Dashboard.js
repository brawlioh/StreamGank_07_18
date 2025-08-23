/**
 * Dashboard Page - Main video generation interface
 * Works with existing HTML structure, doesn't replace it
 */

import DOMManager from '../core/DOMManager.js';
import UIManager from '../components/UIManager.js';
import FormManager from '../components/FormManager.js';
import RealtimeService from '../services/RealtimeService.js';

export class DashboardPage {
    constructor() {
        this.isInitialized = false;
    }

    /**
     * Initialize dashboard page
     */
    init() {
        if (this.isInitialized) {
            return;
        }

        // The dashboard uses the existing form and UI managers
        // which are already initialized in main.js
        this.isInitialized = true;
    }

    /**
     * Activate dashboard functionality with existing HTML
     * @param {HTMLElement} _container - Container (optional, uses existing DOM)
     */
    render(_container) {
        // Work with existing DOM structure - don't replace it
        console.log('📊 Dashboard: Activating with existing HTML structure');

        // Re-cache DOM elements from existing structure
        DOMManager.init();

        // UI Manager init (FormManager already initialized in main.js)
        UIManager.init();

        // Start real-time updates if not already running
        if (!RealtimeService.isInitialized) {
            RealtimeService.init();
        }

        console.log('📊 Dashboard functionality activated');
    }

    /**
     * Handle page activation (when navigated to)
     */
    activate() {
        // Update page title
        document.title = 'Dashboard - StreamGank Video Generator';

        // Refresh queue status when dashboard becomes active
        RealtimeService.refreshStatus();

        console.log('📊 Dashboard activated');
    }

    /**
     * Handle page deactivation (when navigating away)
     */
    deactivate() {
        // Optional cleanup when leaving dashboard
        console.log('📊 Dashboard deactivated');
    }

    /**
     * Get current dashboard state
     * @returns {Object} Dashboard state
     */
    getState() {
        const hasFormManager = FormManager && typeof FormManager.getFormData === 'function';
        const hasUIManager = UIManager && typeof UIManager.getState === 'function';

        return {
            initialized: this.isInitialized,
            formData: hasFormManager ? FormManager.getFormData() : null,
            uiState: hasUIManager ? UIManager.getState() : null
        };
    }

    /**
     * Cleanup dashboard resources
     */
    cleanup() {
        this.isInitialized = false;
        console.log('📊 Dashboard Page cleaned up');
    }
}

// Export singleton instance
export default new DashboardPage();
