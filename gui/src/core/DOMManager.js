/**
 * DOM Manager - Professional DOM element management and caching
 * Handles all DOM element selection, caching, and basic DOM operations
 */
export class DOMManager {
    constructor() {
        this.elements = new Map();
        this.initialized = false;
    }

    /**
     * Initialize and cache all DOM elements
     */
    init() {
        if (this.initialized) return;

        // Cache all DOM elements using a configuration map
        const elementMap = {
            // Form elements
            countrySelect: 'country',
            platformSelect: 'platform',
            genreSelect: 'genre',
            templateSelect: 'template',
            contentTypeRadios: 'input[name="contentType"]',
            generateButton: 'generate-video',

            // Progress elements
            progressContainer: 'progress-container',
            progressBar: '.progress-bar',

            // Preview elements
            previewCountry: 'preview-country',
            previewPlatform: 'preview-platform',
            previewGenre: 'preview-genre',
            previewTemplate: 'preview-template',
            previewType: 'preview-type',
            previewUrl: 'preview-url',

            // Results elements
            statusMessages: 'status-messages',
            videoResults: 'video-results',
            moviesCount: 'movies-count',
            videosCount: 'videos-count',
            groupId: 'group-id',
            videoGallery: 'video-gallery',
            videosContainer: 'videos-container',
            videoCountBadge: 'video-count-badge',

            // Status and control elements
            renderingStatus: 'rendering-status',
            checkStatusBtn: 'check-status-btn',
            creatomateIdDisplay: 'creatomate-id-display',
            loadVideoBtn: 'load-video-btn',
            clearLogsBtn: 'clear-logs-btn',

            // Queue management elements
            refreshQueueBtn: 'refresh-queue-btn',
            clearQueueBtn: 'clear-queue-btn'
        };

        this.cacheElements(elementMap);
        this.initialized = true;
    }

    /**
     * Cache multiple DOM elements
     * @param {Object} elementMap - Map of element names to selectors
     */
    cacheElements(elementMap) {
        Object.entries(elementMap).forEach(([name, selector]) => {
            this.cacheElement(name, selector);
        });
    }

    /**
     * Cache a single DOM element
     * @param {string} name - Element name for cache key
     * @param {string} selector - CSS selector or ID
     */
    cacheElement(name, selector) {
        try {
            let element;

            if (selector.startsWith('.') || selector.startsWith('[') || selector.includes(' ')) {
                // CSS selector
                element =
                    selector.includes('input[name="') || selector.includes("input[name='")
                        ? document.querySelectorAll(selector)
                        : document.querySelector(selector);
            } else {
                // ID selector
                element = document.getElementById(selector);
            }

            if (element) {
                this.elements.set(name, element);
            } else {
                console.warn(`⚠️ Element not found: ${selector}`);
            }
        } catch (error) {
            console.error(`❌ Failed to cache element ${name}:`, error);
        }
    }

    /**
     * Get cached DOM element
     * @param {string} name - Element name
     * @returns {Element|null} DOM element or null
     */
    get(name) {
        const element = this.elements.get(name);
        if (!element && name !== 'contentTypeRadios') {
            // Don't spam for contentTypeRadios - it's handled specially
            console.warn(`⚠️ Element '${name}' not found in cache`);
        }
        return element;
    }

    /**
     * Check if element exists in cache
     * @param {string} name - Element name
     * @returns {boolean} Whether element exists
     */
    has(name) {
        return this.elements.has(name);
    }

    /**
     * Safely set text content of an element
     * @param {string} name - Element name
     * @param {string} content - Text content
     */
    setText(name, content) {
        const element = this.get(name);
        if (element) {
            element.textContent = content;
        }
    }

    /**
     * Safely set HTML content of an element
     * @param {string} name - Element name
     * @param {string} html - HTML content
     */
    setHTML(name, html) {
        const element = this.get(name);
        if (element) {
            element.innerHTML = html;
        }
    }

    /**
     * Add CSS class to element
     * @param {string} name - Element name
     * @param {string} className - CSS class name
     */
    addClass(name, className) {
        const element = this.get(name);
        if (element && element.classList) {
            element.classList.add(className);
        }
    }

    /**
     * Remove CSS class from element
     * @param {string} name - Element name
     * @param {string} className - CSS class name
     */
    removeClass(name, className) {
        const element = this.get(name);
        if (element && element.classList) {
            element.classList.remove(className);
        }
    }

    /**
     * Show element by removing display none
     * @param {string} name - Element name
     */
    show(name) {
        const element = this.get(name);
        if (element) {
            element.style.display = '';
        }
    }

    /**
     * Hide element by setting display none
     * @param {string} name - Element name
     */
    hide(name) {
        const element = this.get(name);
        if (element) {
            element.style.display = 'none';
        }
    }

    /**
     * Get selected value from content type radios
     * @returns {string|null} Selected content type or null
     */
    getSelectedContentType() {
        const radios = this.get('contentTypeRadios');

        if (radios) {
            const checkedRadio = Array.from(radios).find((radio) => radio.checked);

            // If no radio is checked, default to TV Shows (Serie)
            if (!checkedRadio) {
                const tvShowsRadio = Array.from(radios).find((radio) => radio.value === 'Serie');
                if (tvShowsRadio) {
                    tvShowsRadio.checked = true;
                    return 'Serie';
                }
            }

            return checkedRadio ? checkedRadio.value : null;
        }

        // Try direct DOM query as fallback
        const directRadios = document.querySelectorAll('input[name="contentType"]');

        if (directRadios.length > 0) {
            const checkedRadio = Array.from(directRadios).find((radio) => radio.checked);

            // If no radio is checked, default to TV Shows (Serie)
            if (!checkedRadio) {
                const tvShowsRadio = Array.from(directRadios).find((radio) => radio.value === 'Serie');
                if (tvShowsRadio) {
                    tvShowsRadio.checked = true;
                    return 'Serie';
                }
            }

            return checkedRadio ? checkedRadio.value : null;
        }

        return null;
    }

    /**
     * Get form data as object
     * @returns {Object} Form data
     */
    getFormData() {
        // Get selected platforms (checkboxes)
        const platformCheckboxes = document.querySelectorAll('input[name="platforms"]:checked');
        const platforms = Array.from(platformCheckboxes).map((cb) => cb.value);

        // Get selected genres (checkboxes)
        const genreCheckboxes = document.querySelectorAll('input[name="genres"]:checked');
        const genres = Array.from(genreCheckboxes).map((cb) => cb.value);

        const formData = {
            country: this.get('countrySelect')?.value,
            platform: platforms[0] || '', // Keep backward compatibility
            platforms: platforms,
            genre: genres[0] || '', // Keep backward compatibility
            genres: genres,
            template: this.get('templateSelect')?.value,
            contentType: this.getSelectedContentType()
        };

        return formData;
    }
}

// Export singleton instance
export default new DOMManager();
