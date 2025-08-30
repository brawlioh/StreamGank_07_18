/**
 * Form Manager - Professional form handling and validation
 * Manages form interactions, validations, dynamic updates, and preview generation
 */
import DOMManager from '../core/DOMManager.js';
import APIService from '../services/APIService.js';
import UIManager from './UIManager.js';

export class FormManager {
    constructor() {
        this.genresByCountry = {};
        this.templatesByGenre = {};
        this.platformsByCountry = {};
        this.formState = {
            country: '',
            platform: '',
            platforms: [],
            genre: '',
            genres: [],
            template: '',
            contentType: ''
        };
        this.isValidating = false;
        this.validationCache = new Map();
        this.isInitialized = false; // Prevent duplicate initialization
    }

    /**
     * Initialize Form Manager with data and event listeners
     */
    async init() {
        // Prevent duplicate initialization
        if (this.isInitialized) {
            console.log('📋 FormManager already initialized, skipping...');
            return;
        }

        await this.loadFormConfiguration();
        this.setupEventListeners();
        this.initializeFormState();

        this.isInitialized = true;
        console.log('✅ FormManager initialized successfully');
    }

    /**
     * Load form configuration data (genres, templates, etc.)
     */
    async loadFormConfiguration() {
        // Load static genre data for countries
        this.loadGenresByCountry();
        this.loadTemplatesByGenre();

        // Initialize platform data from API if needed - MUST AWAIT
        await this.initializePlatformData();
    }

    /**
     * Load genres by country configuration
     */
    loadGenresByCountry() {
        this.genresByCountry = {
            FR: {
                'Action & Aventure': 'Action & Adventure',
                Animation: 'Animation',
                'Crime & Thriller': 'Crime & Thriller',
                Documentaire: 'Documentary',
                Drame: 'Drama',
                Fantastique: 'Fantasy',
                'Film de guerre': 'War Movies',
                Histoire: 'History',
                Horreur: 'Horror',
                'Musique & Musicale': 'Music & Musical',
                'Mystère & Thriller': 'Mystery & Thriller',
                'Pour enfants': 'Kids',
                'Reality TV': 'Reality TV',
                'Réalisé en Europe': 'Made in Europe',
                'Science-Fiction': 'Science Fiction',
                'Sport & Fitness': 'Sport & Fitness',
                Western: 'Western'
            },
            US: {
                'Action & Adventure': 'Action & Adventure',
                Animation: 'Animation',
                Crime: 'Crime',
                Documentary: 'Documentary',
                Drama: 'Drama',
                Fantasy: 'Fantasy',
                History: 'History',
                Horror: 'Horror',
                'Kids & Family': 'Kids & Family',
                'Made in Europe': 'Made in Europe',
                'Music & Musical': 'Music & Musical',
                'Mystery & Thriller': 'Mystery & Thriller',
                'Reality TV': 'Reality TV',
                'Romance Movies': 'Romance Movies',
                'Science Fiction': 'Science Fiction',
                'Sport & Fitness': 'Sport & Fitness',

                Western: 'Western'
            }
        };
    }

    /**
     * Load template mappings for genres
     */
    loadTemplatesByGenre() {
        // Genre-specific HeyGen templates (from memory)
        this.templatesByGenre = {
            // Horror templates (FIXED: Use correct template ID from config/templates.py)
            Horror: 'ed21a309a5c84b0d873fde68642adea3',
            Horreur: 'ed21a309a5c84b0d873fde68642adea3',

            // Action templates
            'Action & Adventure': '7f8db20ddcd94a33a1235599aa8bf473',
            'Action & Aventure': '7f8db20ddcd94a33a1235599aa8bf473',

            // Default template for other genres
            default: 'cc6718c5363e42b282a123f99b94b335'
        };
    }

    /**
     * Initialize platform data
     */
    async initializePlatformData() {
        // Load platforms for current country and populate dropdown
        const countrySelect = document.getElementById('country');
        if (countrySelect) {
            const currentCountry = countrySelect.value || 'US'; // Changed default to US
            await this.updatePlatformDropdown(currentCountry);
        }

        // Load genres for current country
        const currentCountry = countrySelect ? countrySelect.value : 'US'; // Changed default to US
        await this.updateGenreDropdown(currentCountry);

        // Load templates
        this.updateTemplateDropdown();

        // Set defaults once after all dropdowns are populated
        this.setDefaultSelections();

        // Refresh form state once - all dropdowns are now populated
        this.refreshFormState();

        // Initialize Generate button as disabled until movies are loaded
        this.disableGenerateButton();

        console.log('✅ Platform data initialization complete');
    }

    /**
     * Update platform dropdown for country
     * @param {string} country - Country code
     */
    async updatePlatformDropdown(country) {
        // Prevent duplicate API calls
        const cacheKey = `platforms_${country}`;
        if (this.validationCache.has(cacheKey)) {
            return;
        }

        try {
            const response = await APIService.get(`/api/platforms/${country}`);

            if (response.success && response.platforms) {
                this.populatePlatformSelect(response.platforms);

                // Only cache after successful population
                this.validationCache.set(cacheKey, true);
                console.log('✅ Platform dropdown update completed');
            } else {
                console.error('❌ Invalid platform API response:', response);
            }
        } catch (error) {
            console.error('❌ Failed to load platforms:', error);
        }
    }

    /**
     * Update genre dropdown for country
     * @param {string} country - Country code
     */
    async updateGenreDropdown(country) {
        // Prevent duplicate API calls
        const cacheKey = `genres_${country}`;
        if (this.validationCache.has(cacheKey)) {
            console.log(`📋 Using cached genres for ${country}`);
            return;
        }

        try {
            console.log(`📋 Loading genres for ${country}...`);
            const response = await APIService.get(`/api/genres/${country}`);

            if (response.success && response.genres) {
                console.log(`📋 API returned ${response.genres.length} genres:`, response.genres);
                this.populateGenreSelect(response.genres);

                // Only cache after successful population
                this.validationCache.set(cacheKey, true);
                console.log('✅ Genre dropdown update completed');
            } else {
                console.error('❌ Invalid genre API response:', response);
            }
        } catch (error) {
            console.error('❌ Failed to load genres:', error);
        }
    }

    /**
     * Update template dropdown
     */
    updateTemplateDropdown() {
        const templateSelect = document.getElementById('template');
        if (!templateSelect) return;

        // Clear existing options except first
        templateSelect.innerHTML = '<option value="">Select Template...</option>';

        // Add default templates (FIXED: Use correct Horror template ID)
        const templates = [
            { value: 'cc6718c5363e42b282a123f99b94b335', text: 'Default Template' },
            { value: 'ed21a309a5c84b0d873fde68642adea3', text: 'Horror/Thriller Cinematic' },

            { value: 'e44b139a1b94446a997a7f2ac5ac4178', text: 'Action Adventure' }
        ];

        templates.forEach((template) => {
            const option = document.createElement('option');
            option.value = template.value;
            option.textContent = template.text;
            templateSelect.appendChild(option);
        });

        // Set default selection to Default Template
        templateSelect.value = 'cc6718c5363e42b282a123f99b94b335';
    }

    /**
     * Setup comprehensive form event listeners
     */
    setupEventListeners() {
        // Prevent duplicate event listeners
        if (this.eventListenersSetup) {
            return;
        }

        // Country selection - using correct HTML IDs
        const countrySelect = document.getElementById('country');
        if (countrySelect) {
            countrySelect.addEventListener('change', (e) => {
                this.handleCountryChange(e.target.value);
            });
        }

        // Platform selection
        const platformSelect = document.getElementById('platform');
        if (platformSelect) {
            platformSelect.addEventListener('change', (e) => {
                this.handlePlatformChange(e.target.value);
            });
        }

        // Genre selection (checkboxes handled in populateGenreSelect)
        // Event listeners are added dynamically when checkboxes are created

        // Template selection
        const templateSelect = document.getElementById('template');
        if (templateSelect) {
            templateSelect.addEventListener('change', (e) => {
                this.handleTemplateChange(e.target.value);
            });
        }

        // Movie preview refresh button
        const refreshPreviewBtn = document.getElementById('refresh-preview-btn');
        if (refreshPreviewBtn) {
            refreshPreviewBtn.addEventListener('click', () => {
                this.loadMoviePreview();
            });
        }

        // Content type radio buttons
        const contentTypeRadios = document.querySelectorAll('input[name="contentType"]');
        if (contentTypeRadios) {
            Array.from(contentTypeRadios).forEach((radio) => {
                radio.addEventListener('change', (e) => {
                    if (e.target.checked) {
                        this.handleContentTypeChange(e.target.value);
                    }
                });
            });
        }

        // Form validation on submit
        const generateButton = document.getElementById('generate-video');
        if (generateButton) {
            generateButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.handleFormSubmit();
            });
        }

        // Mark event listeners as setup
        this.eventListenersSetup = true;
    }

    /**
     * Initialize form state from current form values
     */
    initializeFormState() {
        // Ensure US is selected by default
        const countrySelect = document.getElementById('country');
        if (countrySelect && !countrySelect.value) {
            countrySelect.value = 'US';
        }

        // FORCE contentType initialization - check the Serie radio button if none is checked
        this.ensureContentTypeSelected();

        console.log('📋 Form state initialization complete');

        // Note: refreshFormState() will be called next to read all DOM values
        // Note: Platform and genre dropdowns are already populated by initializePlatformData()
    }

    /**
     * Ensure a contentType radio button is selected (default to Serie/TV Shows)
     */
    ensureContentTypeSelected() {
        const contentTypeRadios = document.querySelectorAll('input[name="contentType"]');
        const checkedRadio = Array.from(contentTypeRadios).find((radio) => radio.checked);

        console.log('📋 Content Type Radios found:', contentTypeRadios.length);
        console.log('📋 Already checked:', checkedRadio ? checkedRadio.value : 'none');

        if (!checkedRadio && contentTypeRadios.length > 0) {
            // Find Serie radio button and check it
            const serieRadio = Array.from(contentTypeRadios).find((radio) => radio.value === 'Serie');
            if (serieRadio) {
                serieRadio.checked = true;
                console.log('📋 Force-selected Serie (TV Shows) radio button');
            } else {
                // Fallback - check first radio button
                contentTypeRadios[0].checked = true;
                console.log('📋 Force-selected first radio button:', contentTypeRadios[0].value);
            }
        }
    }

    /**
     * Refresh form state from current DOM values and set defaults
     */
    refreshFormState() {
        const formData = DOMManager.getFormData();
        Object.assign(this.formState, formData);

        console.log('📋 Form state updated');
        console.log('📋 Final form data:', this.formState);

        // Update preview with current state and load initial movie preview
        this.updatePreviewWithMovies();
    }

    /**
     * Set default selections for dropdowns that are populated but have no selection
     */
    setDefaultSelections() {
        let hasChanges = false;

        // Set default platform to Netflix if available, otherwise first option
        const platformSelect = document.getElementById('platform');
        if (platformSelect && platformSelect.children.length > 1 && platformSelect.selectedIndex === 0) {
            // Try to find Netflix first
            let netflixIndex = -1;
            for (let i = 1; i < platformSelect.options.length; i++) {
                if (platformSelect.options[i].value.toLowerCase().includes('netflix')) {
                    netflixIndex = i;
                    break;
                }
            }

            // Select Netflix if found, otherwise first non-empty option
            platformSelect.selectedIndex = netflixIndex > 0 ? netflixIndex : 1;
            this.formState.platform = platformSelect.value;
            console.log('📋 Set default platform:', this.formState.platform);
            hasChanges = true;
        }

        // Set default genre to Horror if available, otherwise first option
        const genreSelect = document.getElementById('genre');
        if (genreSelect && genreSelect.children.length > 1 && genreSelect.selectedIndex === 0) {
            // Try to find Horror first
            let horrorIndex = -1;
            for (let i = 1; i < genreSelect.options.length; i++) {
                if (genreSelect.options[i].value.toLowerCase().includes('horror')) {
                    horrorIndex = i;
                    break;
                }
            }

            // Select Horror if found, otherwise first non-empty option
            genreSelect.selectedIndex = horrorIndex > 0 ? horrorIndex : 1;
            this.formState.genre = genreSelect.value;
            console.log('📋 Set default genre:', this.formState.genre);
            hasChanges = true;

            // Update templates based on selected genre
            this.updateTemplates(this.formState.genre);
        }

        // If we made changes, note it (main refresh will read all values after)
        if (hasChanges) {
            console.log('📋 Defaults set');
        }
    }

    /**
     * Manual form state refresh for debugging
     */
    manualRefresh() {
        console.log('📋 Manual form refresh triggered');
        this.refreshFormState();
        return this.formState;
    }

    // === Form Event Handlers ===

    /**
     * Handle country selection change
     * @param {string} countryCode - Selected country code
     */
    async handleCountryChange(countryCode) {
        console.log(`📋 Country changed: ${countryCode}`);

        this.formState.country = countryCode;

        // Reset dependent fields
        this.resetPlatformSelection();
        this.resetGenreSelection();
        this.resetTemplateSelection();

        if (countryCode) {
            await this.updatePlatforms(countryCode);
        }

        this.updatePreview();
    }

    /**
     * Handle platform selection change
     * @param {string} platformValue - Selected platform value
     */
    async handlePlatformChange() {
        // Handle multiple platform selection with checkboxes
        const selectedPlatforms = [];
        const checkboxes = document.querySelectorAll('input[name="platforms"]:checked');

        checkboxes.forEach((checkbox) => {
            selectedPlatforms.push(checkbox.value);
        });

        console.log('📺 Platform selection changed:', selectedPlatforms);

        this.formState.platforms = selectedPlatforms;
        this.formState.platform = selectedPlatforms[0] || ''; // Keep first platform for backward compatibility

        // Reset dependent fields
        this.resetGenreSelection();
        this.resetTemplateSelection();

        // Don't call updateGenres - genres are not platform-dependent
        // Update the preview and reload movies since platform affects movie selection
        this.updatePreviewWithMovies();
    }

    /**
     * Handle genre checkbox changes (multiple selection)
     */
    handleGenreChange() {
        const selectedGenres = [];
        const checkboxes = document.querySelectorAll('input[name="genres"]:checked');

        checkboxes.forEach((checkbox) => {
            selectedGenres.push(checkbox.value);
        });

        console.log('🎭 Genre selection changed:', selectedGenres);

        this.formState.genres = selectedGenres;
        this.formState.genre = selectedGenres[0] || ''; // Keep first genre for backward compatibility

        // Reset template selection when genre changes
        this.resetTemplateSelection();

        if (selectedGenres.length > 0) {
            this.updateTemplates(selectedGenres[0]); // Use first genre for template loading
        }

        this.updatePreviewWithMovies();
    }

    /**
     * Handle template selection change
     * @param {string} templateValue - Selected template value
     */
    handleTemplateChange(templateValue) {
        console.log(`📋 Template changed: ${templateValue}`);

        this.formState.template = templateValue;
        this.updatePreview();
    }

    /**
     * Handle content type change
     * @param {string} contentType - Selected content type
     */
    handleContentTypeChange(contentType) {
        console.log(`📋 Content type changed: ${contentType}`);

        this.formState.contentType = contentType;
        this.updatePreviewWithMovies();
    }

    // === Form Update Methods ===

    /**
     * Update platforms dropdown based on country
     * @param {string} countryCode - Country code
     */
    async updatePlatforms(countryCode) {
        try {
            const result = await APIService.getPlatforms(countryCode);

            if (result.success && result.platforms) {
                this.populatePlatformSelect(result.platforms);
            } else {
                this.populateDefaultPlatforms(countryCode);
            }
        } catch (error) {
            console.error('❌ Failed to load platforms:', error);
            this.populateDefaultPlatforms(countryCode);
        }
    }

    /**
     * Populate platform checkboxes with options
     * @param {Array} platforms - Array of platform strings
     */
    populatePlatformSelect(platforms) {
        const platformContainer = document.getElementById('platform-checkboxes');
        if (!platformContainer) {
            console.error('❌ Platform checkboxes container not found!');
            return;
        }

        console.log('📋 Populating platforms:', platforms);

        // Clear existing checkboxes
        platformContainer.innerHTML = '';

        // Add platform checkboxes
        platforms.forEach((platform, index) => {
            const checkboxItem = document.createElement('div');
            checkboxItem.className = 'checkbox-item';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `platform-${index}`;
            checkbox.value = platform;
            checkbox.name = 'platforms';

            // Pre-select Netflix if available
            if (platform.toLowerCase().includes('netflix')) {
                checkbox.checked = true;
                this.formState.platforms = [platform];
            }

            const label = document.createElement('label');
            label.htmlFor = `platform-${index}`;
            label.textContent = platform;

            // Add change event listener
            checkbox.addEventListener('change', (e) => {
                this.handlePlatformChange();
            });

            checkboxItem.appendChild(checkbox);
            checkboxItem.appendChild(label);
            platformContainer.appendChild(checkboxItem);
        });

        console.log('✅ Platform checkboxes populated with', platforms.length, 'options');
    }

    /**
     * Populate default platforms when API fails
     * @param {string} countryCode - Country code
     */
    populateDefaultPlatforms(countryCode) {
        const defaultPlatforms = [
            { value: 'Netflix', name: 'Netflix' },
            { value: 'Prime Video', name: 'Prime Video' },
            { value: 'Disney+', name: 'Disney+' },
            { value: 'Apple TV+', name: 'Apple TV+' },
            { value: 'HBO Max', name: 'HBO Max' }
        ];

        this.populatePlatformSelect(defaultPlatforms);
    }

    /**
     * Update genres based on country and platform
     * @param {string} countryCode - Country code
     * @param {string} platformValue - Platform value
     */
    async updateGenres(countryCode, platformValue = null) {
        // Use country-specific caching (genres are not platform-specific)
        const cacheKey = `genres_${countryCode}`;
        if (this.validationCache.has(cacheKey)) {
            console.log(`📋 Using cached genres for ${countryCode}`);
            return;
        }

        try {
            console.log(`📋 Loading genres for ${countryCode}...`);
            const result = await APIService.getGenres(countryCode); // Don't pass platform

            if (result.success && result.genres) {
                console.log(`📋 API returned ${result.genres.length} genres for ${countryCode}:`, result.genres);
                this.populateGenreSelect(result.genres);
                this.validationCache.set(cacheKey, true); // Cache successful result
                return;
            }
        } catch (error) {
            console.error('❌ Failed to load genres from API:', error);
        }

        // Fallback to static genre data
        console.log(`📋 Using fallback static genres for ${countryCode}`);
        this.populateGenreSelectFromStatic(countryCode);
    }

    /**
     * Populate genre checkboxes from API data
     * @param {Array} genres - Array of genre strings
     */
    populateGenreSelect(genres) {
        const genreContainer = document.getElementById('genre-checkboxes');
        if (!genreContainer) {
            console.error('❌ Genre checkboxes container not found!');
            return;
        }

        console.log('📋 Populating genres:', genres);

        // Clear existing checkboxes
        genreContainer.innerHTML = '';

        // Add genre checkboxes
        genres.forEach((genre, index) => {
            const checkboxItem = document.createElement('div');
            checkboxItem.className = 'checkbox-item';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `genre-${index}`;
            checkbox.value = genre;
            checkbox.name = 'genres';

            // Pre-select Horror if available
            if (genre.toLowerCase().includes('horror')) {
                checkbox.checked = true;
                this.formState.genres = [genre];
            }

            const label = document.createElement('label');
            label.htmlFor = `genre-${index}`;
            label.textContent = genre;

            // Add change event listener
            checkbox.addEventListener('change', (e) => {
                this.handleGenreChange();
            });

            checkboxItem.appendChild(checkbox);
            checkboxItem.appendChild(label);
            genreContainer.appendChild(checkboxItem);
        });

        console.log('✅ Genre checkboxes populated with', genres.length, 'options');

        // Don't refresh here - will be done once at end of initialization
    }

    /**
     * Populate genre select from static data
     * @param {string} countryCode - Country code
     */
    populateGenreSelectFromStatic(countryCode) {
        const genres = this.genresByCountry[countryCode];
        if (!genres) return;

        const genreSelect = document.getElementById('genre');
        if (!genreSelect) return;

        // Clear existing options (except first)
        while (genreSelect.children.length > 1) {
            genreSelect.removeChild(genreSelect.lastChild);
        }

        // Add genre options
        Object.entries(genres).forEach(([displayName, value]) => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = displayName;
            genreSelect.appendChild(option);
        });
    }

    /**
     * Update templates based on genre
     * @param {string} genreValue - Selected genre value
     */
    updateTemplates(genreValue) {
        const templateSelect = document.getElementById('template');
        if (!templateSelect) return;

        // Get appropriate template ID
        const templateId = this.getTemplateForGenre(genreValue);

        // Find and select the matching template
        Array.from(templateSelect.options).forEach((option) => {
            if (option.value === templateId) {
                option.selected = true;
                this.formState.template = templateId;
            }
        });

        console.log(`📋 Template auto-selected for genre '${genreValue}': ${templateId}`);
    }

    /**
     * Get template ID for specific genre
     * @param {string} genreValue - Genre value
     * @returns {string} Template ID
     */
    getTemplateForGenre(genreValue) {
        // Check for exact match
        if (this.templatesByGenre[genreValue]) {
            return this.templatesByGenre[genreValue];
        }

        // Check for case-insensitive match
        const genreLower = genreValue.toLowerCase();
        for (const [key, templateId] of Object.entries(this.templatesByGenre)) {
            if (key.toLowerCase() === genreLower) {
                return templateId;
            }
        }

        // Return default template
        return this.templatesByGenre.default;
    }

    // === Form Reset Methods ===

    /**
     * Reset platform selection
     */
    resetPlatformSelection() {
        const platformSelect = document.getElementById('platform');
        if (platformSelect) {
            platformSelect.selectedIndex = 0;
            // Clear all options except the first
            while (platformSelect.children.length > 1) {
                platformSelect.removeChild(platformSelect.lastChild);
            }
        }
        this.formState.platform = '';
    }

    /**
     * Reset genre selection
     */
    resetGenreSelection() {
        const genreSelect = document.getElementById('genre');
        if (genreSelect) {
            genreSelect.selectedIndex = 0;
            // Clear all options except the first
            while (genreSelect.children.length > 1) {
                genreSelect.removeChild(genreSelect.lastChild);
            }
        }
        this.formState.genre = '';
    }

    /**
     * Reset template selection
     */
    resetTemplateSelection() {
        const templateSelect = document.getElementById('template');
        if (templateSelect) {
            templateSelect.selectedIndex = 0;
        }
        this.formState.template = '';
    }

    // === Form Validation ===

    /**
     * Validate current form state
     * @returns {Object} Validation result
     */
    validateForm() {
        const errors = [];
        const warnings = [];

        // Required field validation
        if (!this.formState.country) {
            errors.push('Country is required');
        }

        if (!this.formState.platform) {
            errors.push('Platform is required');
        }

        if (!this.formState.genre) {
            errors.push('Genre is required');
        }

        if (!this.formState.contentType) {
            errors.push('Content type is required');
        }

        // Template validation (warning only)
        if (!this.formState.template) {
            warnings.push('No template selected - default will be used');
        }

        return {
            isValid: errors.length === 0,
            errors,
            warnings
        };
    }

    /**
     * Validate StreamGank URL
     * @param {string} url - URL to validate
     * @returns {Promise<Object>} Validation result
     */
    async validateStreamGankUrl(url) {
        if (!url || url.includes('Select all parameters')) {
            return { valid: false, message: 'Please complete the form to generate a valid URL' };
        }

        const cacheKey = `url:${url}`;
        if (this.validationCache.has(cacheKey)) {
            return this.validationCache.get(cacheKey);
        }

        try {
            UIManager.addStatusMessage('info', '🔍', 'Validating URL...');
            this.isValidating = true;

            const result = await APIService.validateUrl(url);

            const validation = {
                valid: result.success,
                message: result.message,
                moviesCount: result.moviesCount,
                timestamp: new Date().toISOString()
            };

            // Cache validation result
            this.validationCache.set(cacheKey, validation);

            if (validation.valid) {
                UIManager.addStatusMessage('success', '✅', `URL validated! Found ${validation.moviesCount} items`);
            } else {
                UIManager.addStatusMessage('error', '❌', `URL validation failed: ${validation.message}`);
            }

            return validation;
        } catch (error) {
            console.error('❌ URL validation error:', error);

            const validation = {
                valid: false,
                message: error.message || 'Validation failed',
                timestamp: new Date().toISOString()
            };

            UIManager.addStatusMessage('error', '❌', `Validation error: ${validation.message}`);
            return validation;
        } finally {
            this.isValidating = false;
        }
    }

    // === Form Submission ===

    /**
     * Handle form submission
     */
    async handleFormSubmit() {
        try {
            // Update form state from DOM
            this.updateFormStateFromDOM();

            // Validate form
            const validation = this.validateForm();

            if (!validation.isValid) {
                validation.errors.forEach((error) => {
                    UIManager.addStatusMessage('error', '❌', error);
                });
                return;
            }

            // Show warnings if any
            validation.warnings.forEach((warning) => {
                UIManager.addStatusMessage('warning', '⚠️', warning);
            });

            // Generate and validate URL
            const previewUrl = this.generateStreamGankUrl();
            const urlValidation = await this.validateStreamGankUrl(previewUrl);

            if (!urlValidation.valid) {
                return; // Error already shown by validation
            }

            // Emit form submission event with data
            document.dispatchEvent(
                new CustomEvent('formSubmit', {
                    detail: {
                        formData: { ...this.formState },
                        previewUrl,
                        validation: urlValidation
                    }
                })
            );
        } catch (error) {
            console.error('❌ Form submission error:', error);
            UIManager.addStatusMessage('error', '❌', `Form submission failed: ${error.message}`);
        }
    }

    /**
     * Update form state from current DOM values
     */
    updateFormStateFromDOM() {
        const formData = DOMManager.getFormData();
        Object.assign(this.formState, formData);
    }

    // === Preview Generation ===

    /**
     * Update form preview display
     */
    updatePreview() {
        // Use form state data for preview (no need to read DOM again)
        UIManager.updateFormPreviewFromState(this.formState);

        console.log('📋 Preview updated');
    }

    /**
     * Update preview and reload movie data (for filter changes)
     */
    updatePreviewWithMovies() {
        // Update the form preview display
        this.updatePreview();

        // Load movie preview when filters change
        this.loadMoviePreview();

        console.log('📋 Preview updated with movie reload');
    }

    /**
     * Load movie preview based on current filters
     */
    async loadMoviePreview() {
        const country = this.formState.country;
        const platforms = this.formState.platforms || [];
        const genres = this.formState.genres || [];
        const contentType = this.formState.contentType;

        // Don't load preview if essential filters are missing
        if (!country || platforms.length === 0 || genres.length === 0) {
            this.hideMoviePreview();
            return;
        }

        console.log('🎬 Loading movie preview:', { country, platforms, genres, contentType });

        this.showMoviePreviewLoading();

        try {
            const response = await fetch('/api/movies/preview', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    country,
                    platforms,
                    genre: genres, // Send as array
                    contentType: contentType === 'All' ? null : contentType // Don't send contentType if "All"
                })
            });

            const data = await response.json();

            if (data.success && data.movies && data.movies.length > 0) {
                this.displayMoviePreview(data.movies);
            } else {
                this.showMoviePreviewEmpty();
            }
        } catch (error) {
            console.error('❌ Failed to load movie preview:', error);
            this.showMoviePreviewEmpty();
        }
    }

    /**
     * Display movie preview cards
     */
    displayMoviePreview(movies) {
        const container = document.getElementById('movie-preview-container');
        const grid = document.getElementById('movie-preview-grid');
        const loading = document.getElementById('movie-preview-loading');
        const empty = document.getElementById('movie-preview-empty');

        if (!container || !grid) return;

        // Hide loading and empty states
        loading.style.display = 'none';
        empty.style.display = 'none';

        // Clear existing content
        grid.innerHTML = '';

        // Create movie cards
        movies.forEach((movie, index) => {
            const movieCard = this.createMovieCard(movie, index);
            grid.appendChild(movieCard);
        });

        // Show the preview container
        container.style.display = 'block';

        // Enable Generate button since we have movies
        this.enableGenerateButton();

        console.log(`✅ Displayed ${movies.length} movie preview cards`);
    }

    /**
     * Create a movie card element
     */
    createMovieCard(movie, index) {
        const col = document.createElement('div');
        col.className = 'col-md-4';

        const card = document.createElement('div');
        card.className = 'movie-card';

        const posterUrl =
            movie.poster_url || movie.backdrop_url || 'https://via.placeholder.com/300x450/333/fff?text=No+Image';
        const title = movie.title || 'Unknown Title';

        card.innerHTML = `
            <img src="${posterUrl}" alt="${title}" class="movie-poster" 
                 onerror="this.src='https://via.placeholder.com/300x450/333/fff?text=No+Image'">
            <div class="movie-title-large">${title}</div>
        `;

        col.appendChild(card);
        return col;
    }

    /**
     * Show movie preview loading state
     */
    showMoviePreviewLoading() {
        const container = document.getElementById('movie-preview-container');
        const loading = document.getElementById('movie-preview-loading');
        const grid = document.getElementById('movie-preview-grid');
        const empty = document.getElementById('movie-preview-empty');

        if (!container || !loading) return;

        container.style.display = 'block';
        loading.style.display = 'block';
        grid.innerHTML = '';
        empty.style.display = 'none';

        // Disable Generate button while loading
        this.disableGenerateButton();
    }

    /**
     * Show movie preview empty state
     */
    showMoviePreviewEmpty() {
        const container = document.getElementById('movie-preview-container');
        const loading = document.getElementById('movie-preview-loading');
        const grid = document.getElementById('movie-preview-grid');
        const empty = document.getElementById('movie-preview-empty');

        if (!container || !empty) return;

        container.style.display = 'block';
        loading.style.display = 'none';
        grid.innerHTML = '';
        empty.style.display = 'block';

        // Disable Generate button since there are no movies
        this.disableGenerateButton();
    }

    /**
     * Hide movie preview section
     */
    hideMoviePreview() {
        const container = document.getElementById('movie-preview-container');
        if (container) {
            container.style.display = 'none';
        }

        // Disable Generate button since preview is hidden
        this.disableGenerateButton();
    }

    /**
     * Enable the Generate Video button
     */
    enableGenerateButton() {
        const generateButton = document.getElementById('generate-video');
        if (generateButton) {
            generateButton.disabled = false;
            generateButton.classList.remove('btn-secondary');
            generateButton.classList.add('btn-primary');
            generateButton.innerHTML = '<span class="icon">🎬</span> Generate Video';
            console.log('✅ Generate button enabled');
        }
    }

    /**
     * Disable the Generate Video button
     */
    disableGenerateButton() {
        const generateButton = document.getElementById('generate-video');
        if (generateButton) {
            generateButton.disabled = true;
            generateButton.classList.remove('btn-primary');
            generateButton.classList.add('btn-secondary');
            generateButton.innerHTML = '<span class="icon">⚠️</span> No Movies Available';
            console.log('🚫 Generate button disabled');
        }
    }

    /**
     * Generate StreamGank URL from current form state
     * @returns {string} Generated URL
     */
    generateStreamGankUrl() {
        if (!this.formState.country || !this.formState.platform || !this.formState.contentType) {
            return 'Select all parameters to generate URL';
        }

        const baseUrl = 'https://streamgank.com';
        const params = new URLSearchParams();

        // Use exact format: country, platforms (plural), genres (plural), type
        if (this.formState.country) params.set('country', this.formState.country);
        if (this.formState.platform) params.set('platforms', this.formState.platform.toLowerCase());

        // Only add genre if not 'all' (use plural 'genres') - map to English
        if (this.formState.genre && this.formState.genre !== 'all') {
            const genreMapping = {
                Horreur: 'Horror',

                'Action & Aventure': 'Action',
                Animation: 'Animation'
            };
            const englishGenre = genreMapping[this.formState.genre] || this.formState.genre;
            params.set('genres', englishGenre);
        }

        // Only add content type if not 'all' - map to clean English
        if (this.formState.contentType && this.formState.contentType !== 'all') {
            const typeMapping = {
                movies: 'Film',
                series: 'Serie',
                tvshows: 'Serie',
                'tv-shows': 'Serie'
            };
            const cleanType = typeMapping[this.formState.contentType.toLowerCase()] || this.formState.contentType;
            params.set('type', cleanType);
        }

        return `${baseUrl}?${params.toString()}`;
    }

    // === Utility Methods ===

    /**
     * Get current form data
     * @returns {Object} Current form state
     */
    getFormData() {
        this.updateFormStateFromDOM();
        return { ...this.formState };
    }

    /**
     * Set form data
     * @param {Object} data - Form data to set
     */
    setFormData(data) {
        Object.assign(this.formState, data);

        // Update DOM elements
        Object.entries(data).forEach(([key, value]) => {
            const element = DOMManager.get(`${key}Select`) || DOMManager.get(key);
            if (element && element.value !== undefined) {
                element.value = value;
            }
        });

        this.updatePreview();
    }

    /**
     * Reset form to initial state
     */
    resetForm() {
        this.formState = {
            country: '',
            platform: '',
            genre: '',
            template: '',
            contentType: ''
        };

        // Reset DOM elements using correct element IDs
        ['country', 'platform', 'genre', 'template'].forEach((elementId) => {
            const select = document.getElementById(elementId);
            if (select) {
                select.selectedIndex = 0;
            }
        });

        // Reset radio buttons
        const contentTypeRadios = DOMManager.get('contentTypeRadios');
        if (contentTypeRadios) {
            Array.from(contentTypeRadios).forEach((radio) => {
                radio.checked = false;
            });
        }

        // Clear validation cache
        this.validationCache.clear();

        this.updatePreview();
        console.log('📋 Form reset');
    }

    /**
     * Get form validation state
     * @returns {Object} Current validation state
     */
    getValidationState() {
        return {
            isValidating: this.isValidating,
            cacheSize: this.validationCache.size,
            lastValidation: null // Could track this if needed
        };
    }

    /**
     * Emit custom events for form actions
     */
    emit(eventName, data) {
        console.log(`📤 FormManager emitting ${eventName}:`, data);
        const event = new CustomEvent(eventName, { detail: data });
        // Dispatch on document to ensure it's caught by main.js
        document.dispatchEvent(event);
    }
}

// Create singleton instance
const formManager = new FormManager();

// Export singleton instance
export default formManager;
