document.addEventListener('DOMContentLoaded', function () {
    // Get all form elements
    const countrySelect = document.getElementById('country');
    const platformSelect = document.getElementById('platform');
    const genreSelect = document.getElementById('genre');
    const templateSelect = document.getElementById('template');
    const contentTypeRadios = document.querySelectorAll('input[name="contentType"]');
    const generateButton = document.getElementById('generate-video');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.querySelector('.progress-bar');

    // Preview elements
    const previewCountry = document.getElementById('preview-country');
    const previewPlatform = document.getElementById('preview-platform');
    const previewGenre = document.getElementById('preview-genre');
    const previewTemplate = document.getElementById('preview-template');
    const previewType = document.getElementById('preview-type');
    const previewUrl = document.getElementById('preview-url');

    // Results elements
    const statusMessages = document.getElementById('status-messages');
    const videoResults = document.getElementById('video-results');
    const moviesCount = document.getElementById('movies-count');
    const videosCount = document.getElementById('videos-count');
    const groupId = document.getElementById('group-id');
    const videoGallery = document.getElementById('video-gallery');
    const videosContainer = document.getElementById('videos-container');
    const videoCountBadge = document.getElementById('video-count-badge');
    const renderingStatus = document.getElementById('rendering-status');
    const checkStatusBtn = document.getElementById('check-status-btn');
    const creatomateIdDisplay = document.getElementById('creatomate-id-display');
    const loadVideoBtn = document.getElementById('load-video-btn');
    const clearLogsBtn = document.getElementById('clear-logs-btn');

    // Track if video ready message has been shown for current video
    let videoReadyMessageShown = false;

    // Track current job monitoring state
    let currentJobMonitoring = null;
    let isGenerationActive = false;

    // Track completed videos
    let completedVideos = [];

    // Video event handlers (defined once to prevent duplicates)
    function videoLoadStartHandler() {
        if (!videoReadyMessageShown) {
            addStatusMessage('info', '📥', 'Video started loading...');
        }
    }

    function videoCanPlayHandler() {
        if (!videoReadyMessageShown) {
            addStatusMessage('success', '🎬', 'Video is ready to play!');
            videoReadyMessageShown = true;
        }
    }

    function videoErrorHandler(e) {
        addStatusMessage('error', '❌', 'Video failed to load. Please try the direct link.');
        console.error('Video load error:', e);
    }

    // Genre data organized by country - Updated to match StreamGank exact genres
    const genresByCountry = {
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
            Romance: 'Romance',
            'Science-Fiction': 'Science-Fiction',
            Sport: 'Sport',
            'War & Military': 'War & Military',
            Western: 'Western'
        },
        // For other countries, default to English genres
        GB: {
            Action: 'Action',
            Animation: 'Animation',
            Crime: 'Crime',
            Documentary: 'Documentary',
            Drama: 'Drama',
            Family: 'Family',
            Fantasy: 'Fantasy',
            History: 'History',
            Horror: 'Horror',
            Music: 'Music',
            Mystery: 'Mystery',
            Romance: 'Romance',
            SF: 'Science Fiction',
            Thriller: 'Thriller',
            Western: 'Western'
        },
        CA: {
            Action: 'Action',
            Animation: 'Animation',
            Crime: 'Crime',
            Documentary: 'Documentary',
            Drama: 'Drama',
            Family: 'Family',
            Fantasy: 'Fantasy',
            History: 'History',
            Horror: 'Horror',
            Music: 'Music',
            Mystery: 'Mystery',
            Romance: 'Romance',
            SF: 'Science Fiction',
            Thriller: 'Thriller',
            Western: 'Western'
        },
        AU: {
            Action: 'Action',
            Animation: 'Animation',
            Crime: 'Crime',
            Documentary: 'Documentary',
            Drama: 'Drama',
            Family: 'Family',
            Fantasy: 'Fantasy',
            History: 'History',
            Horror: 'Horror',
            Music: 'Music',
            Mystery: 'Mystery',
            Romance: 'Romance',
            SF: 'Science Fiction',
            Thriller: 'Thriller',
            Western: 'Western'
        }
    };

    // HeyGen Template configurations matching the backend
    const heygenTemplates = {
        horror: {
            id: 'ed21a309a5c84b0d873fde68642adea3',
            name: 'Horror/Thriller Cinematic',
            description: 'Specialized template for horror and thriller content',
            genres: ['Horror', 'Horreur', 'Thriller', 'Mystery & Thriller', 'Mystère & Thriller']
        },

        action: {
            id: '7f8db20ddcd94a33a1235599aa8bf473',
            name: 'Action/Adventure Dynamic',
            description: 'High-energy template for action and adventure content',
            genres: ['Action', 'Action & Adventure', 'Action & Aventure']
        },
        default: {
            id: 'cc6718c5363e42b282a123f99b94b335',
            name: 'Universal Default',
            description: 'General-purpose template for all other content types',
            genres: ['*'] // Wildcard for all other genres
        }
    };

    // Platform value mapping (display name -> URL parameter value)
    const platformMapping = {
        Prime: 'amazon',
        'Apple TV+': 'apple',
        'Disney+': 'disney',
        Hulu: 'hulu', // US only
        Max: 'max',
        Netflix: 'netflix',
        Free: 'free'
    };

    // Genre value mapping (display name -> URL parameter value)
    const genreMapping = {
        // French genres (note: first entry has Family prefix as per StreamGank data)
        'Action & Aventure': 'Family%2CAction+%26+Aventure',
        Animation: 'Animation',

        'Crime & Thriller': 'Crime+%26+Thriller',
        Documentaire: 'Documentaire',
        Drame: 'Drame',
        Fantastique: 'Fantastique',
        'Film de guerre': 'Film+de+guerre',
        Histoire: 'Histoire',
        Horreur: 'Horreur',
        'Musique & Musicale': 'Musique+%26+Musicale',
        'Mystère & Thriller': 'Myst%C3%A8re+%26+Thriller',
        'Pour enfants': 'Pour+enfants',
        'Reality TV': 'Reality+TV',
        'Réalisé en Europe': 'R%C3%A9alis%C3%A9+en+Europe',
        'Science-Fiction': 'Science-Fiction',
        'Sport & Fitness': 'Sport+%26+Fitness',
        Western: 'Western',

        // US genres
        'Action & Adventure': 'Action+%26+Adventure',
        Animation: 'Animation',

        Crime: 'Crime',
        Documentary: 'Documentary',
        Drama: 'Drama',
        Fantasy: 'Fantasy',
        History: 'History',
        Horror: 'Horror',
        'Kids & Family': 'Kids+%26+Family',
        'Made in Europe': 'Made+in+Europe',
        'Music & Musical': 'Music+%26+Musical',
        'Mystery & Thriller': 'Mystery+%26+Thriller',
        'Reality TV': 'Reality+TV',
        Romance: 'Romance',
        'Science-Fiction': 'Science-Fiction',
        Sport: 'Sport',
        'War & Military': 'War+%26+Military',
        Western: 'Western'
    };

    // Content type mapping (HTML values -> StreamGank URL parameter values)
    const contentTypeMapping = {
        Film: 'Film', // Movies
        Serie: 'Série', // TV Shows - needs proper French accent for URL
        all: 'all' // All content
    };

    // Function to update platforms based on selected country (user-defined data)
    async function updatePlatforms() {
        const selectedCountry = countrySelect.value;

        // Store current selection
        const currentSelection = platformSelect.value;

        try {
            // Show loading state
            platformSelect.innerHTML = '<option value="">Loading platforms...</option>';
            platformSelect.disabled = true;

            // Fetch platforms from database API
            const response = await fetch(`/api/platforms/${selectedCountry}`);
            const data = await response.json();

            if (!data.success) {
                throw new Error(data.message || 'Failed to fetch platforms');
            }

            console.log(`📊 Loaded ${data.platforms.length} platforms for ${selectedCountry} from ${data.source}`);

            // Clear existing options
            platformSelect.innerHTML = '';

            // Add new options based on database data
            data.platforms.forEach((platformName) => {
                const option = document.createElement('option');
                // Use display name as value, URL parameter will be generated in buildStreamGankUrl
                option.value = platformName;
                option.textContent = platformName;
                platformSelect.appendChild(option);
            });

            // Try to restore previous selection if it exists in the new list
            if (currentSelection && data.platforms.includes(currentSelection)) {
                platformSelect.value = currentSelection;
            } else {
                // Set default selection (Netflix is usually available)
                if (data.platforms.includes('Netflix')) {
                    platformSelect.value = 'Netflix';
                } else if (data.platforms.length > 0) {
                    platformSelect.value = data.platforms[0];
                }
            }

            // Ensure a platform is always selected
            if (!platformSelect.value && platformSelect.options.length > 0) {
                platformSelect.selectedIndex = 0;
            }

            platformSelect.disabled = false;

            // Trigger preview update after platform selection
            updatePreview();
        } catch (error) {
            console.error('❌ Error fetching platforms:', error);

            // Fallback to hardcoded data
            console.log('🔄 Falling back to hardcoded platform data');
            const fallbackPlatforms = {
                FR: ['Prime', 'Apple TV+', 'Disney+', 'Max', 'Netflix', 'Free'],
                US: ['Prime', 'Apple TV+', 'Disney+', 'Hulu', 'Max', 'Netflix', 'Free']
            };

            const platforms = fallbackPlatforms[selectedCountry] || fallbackPlatforms['US'];

            platformSelect.innerHTML = '';
            platforms.forEach((platformName) => {
                const option = document.createElement('option');
                option.value = platformName;
                option.textContent = platformName;
                platformSelect.appendChild(option);
            });

            // Restore selection or default to netflix
            if (currentSelection && platforms.includes(currentSelection)) {
                platformSelect.value = currentSelection;
            } else {
                // Try to set Netflix, otherwise use first available
                if (platforms.includes('Netflix')) {
                    platformSelect.value = 'Netflix';
                } else if (platforms.length > 0) {
                    platformSelect.value = platforms[0];
                }
            }

            // Ensure a platform is always selected
            if (!platformSelect.value && platformSelect.options.length > 0) {
                platformSelect.selectedIndex = 0;
            }

            platformSelect.disabled = false;

            // Trigger preview update after platform selection
            updatePreview();
        }
    }

    // Helper function to convert platform display name to value
    function getPlatformValue(platformName) {
        // Direct lookup in platformMapping (key is display name, value is URL param)
        return platformMapping[platformName] || platformName.toLowerCase().replace(/[^a-z0-9]/g, '');
    }

    // Function to get HeyGen template for a genre
    function getTemplateForGenre(genre) {
        if (!genre) {
            return heygenTemplates['default'];
        }

        // Check each template category for genre match
        for (const [templateKey, templateInfo] of Object.entries(heygenTemplates)) {
            if (templateKey === 'default') continue; // Skip default, it's the fallback

            // Case-insensitive genre matching
            for (const templateGenre of templateInfo.genres) {
                if (genre.toLowerCase() === templateGenre.toLowerCase()) {
                    return templateInfo;
                }
            }
        }

        // No specific match found, use default
        return heygenTemplates['default'];
    }

    // Function to update templates based on selected genre
    function updateTemplates() {
        const selectedGenre = genreSelect.value;

        // Clear existing options
        templateSelect.innerHTML = '';

        // Get all available templates and mark which one is recommended for this genre
        const recommendedTemplate = getTemplateForGenre(selectedGenre);

        // Add all templates as options
        Object.entries(heygenTemplates).forEach(([templateKey, templateInfo]) => {
            if (templateKey === 'default') return; // Skip adding default separately, it will be added at the end

            const option = document.createElement('option');
            option.value = templateInfo.id;
            option.textContent = templateInfo.name;

            // Mark recommended template
            if (templateInfo.id === recommendedTemplate.id) {
                option.textContent += ' (Recommended)';
                option.selected = true;
            }

            templateSelect.appendChild(option);
        });

        // Always add default template at the end
        const defaultOption = document.createElement('option');
        defaultOption.value = heygenTemplates['default'].id;
        defaultOption.textContent = heygenTemplates['default'].name;

        // Select default if no other template was recommended
        if (recommendedTemplate.id === heygenTemplates['default'].id) {
            defaultOption.selected = true;
            defaultOption.textContent += ' (Recommended)';
        }

        templateSelect.appendChild(defaultOption);
    }

    // Function to update genres based on selected country
    function updateGenres() {
        const selectedCountry = countrySelect.value;
        const genres = genresByCountry[selectedCountry] || genresByCountry['US']; // Default to US

        // Clear existing options
        genreSelect.innerHTML = '';

        // Add new options based on country
        Object.entries(genres).forEach(([value, display]) => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = display;
            genreSelect.appendChild(option);
        });

        // Set default selection based on country
        if (selectedCountry === 'FR') {
            genreSelect.value = 'Horreur'; // French default
        } else {
            genreSelect.value = 'Horror'; // English default
        }

        // Update templates after genres are updated
        updateTemplates();
    }

    // Update preview when form elements change
    countrySelect.addEventListener('change', function () {
        updatePlatforms();
        updateGenres();
        updatePreview();
    });
    platformSelect.addEventListener('change', updatePreview);
    genreSelect.addEventListener('change', function () {
        updateTemplates();
        updatePreview();
    });
    templateSelect.addEventListener('change', updatePreview);
    contentTypeRadios.forEach((radio) => {
        radio.addEventListener('change', updatePreview);
    });

    // Initial setup
    updatePlatforms();
    updateGenres();
    updateTemplates();
    updatePreview();

    // Handle form submission
    generateButton.addEventListener('click', startVideoGeneration);

    // Copy URL functionality is now handled individually for each video in the gallery

    // Function to update preview
    function updatePreview() {
        // Get selected values
        const country = countrySelect.options[countrySelect.selectedIndex];
        const platform = platformSelect.options[platformSelect.selectedIndex];
        const genre = genreSelect.options[genreSelect.selectedIndex];
        const template = templateSelect.options[templateSelect.selectedIndex];
        const contentType = document.querySelector('input[name="contentType"]:checked');

        // Update preview text
        previewCountry.textContent = country.text;
        previewPlatform.textContent = platform.text;
        previewGenre.textContent = genre.text;
        previewTemplate.textContent = template ? template.text : 'Universal Default';

        if (contentType) {
            previewType.textContent =
                contentType.id === 'all' ? 'All' : contentType.id === 'movie' ? 'Movies' : 'TV Shows';
        } else {
            previewType.textContent = 'TV Shows'; // Default
        }

        // Build and update URL - pass genre.value (French key) for correct mapping
        const url = buildStreamGankUrl(
            country.value,
            genre.value,
            platform.text,
            contentType ? contentType.value : 'Serie'
        );
        previewUrl.textContent = url;
    }

    // Function to build StreamGank URL
    function buildStreamGankUrl(country, genre, platform, type) {
        let url = `https://streamgank.com/?country=${country}`;

        if (genre) {
            // Use French genre mapping for URL parameter (already properly encoded)
            const genreParam = genreMapping[genre] || encodeURIComponent(genre);
            // Don't double-encode: genreMapping values are already URL-encoded
            url += `&genres=${genreParam}`;
        }

        if (platform) {
            // Use platform mapping for URL parameter
            const platformParam = platformMapping[platform] || platform.toLowerCase().replace(/[^a-z0-9]/g, '');
            url += `&platforms=${platformParam}`;
        }

        if (type && type !== 'all' && type !== 'All') {
            // Use French content type mapping for URL parameter
            const typeParam = contentTypeMapping[type] || type;
            // URL encode to handle accents (e.g., "Série" -> "S%C3%A9rie")
            url += `&type=${encodeURIComponent(typeParam)}`;
        }

        return url;
    }

    // Function to validate StreamGank URL before generation
    async function validateStreamGankUrl(url) {
        try {
            addStatusMessage('info', '🔍', 'Checking if movies are available for selected parameters...');

            // Since we can't directly access the StreamGang site due to CORS,
            // we'll implement a server-side validation endpoint
            const response = await fetch('/api/validate-url', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url: url })
            });

            if (!response.ok) {
                throw new Error(`Validation request failed: ${response.status}`);
            }

            const result = await response.json();
            return result;
        } catch (error) {
            // If validation fails, log warning but continue
            console.warn('URL validation failed, continuing with generation:', error);
            addStatusMessage(
                'warning',
                '⚠️',
                'Could not pre-validate URL due to technical limitations, proceeding with generation...'
            );
            addStatusMessage('info', 'ℹ️', 'If no movies are found, the process will stop with a clear error message.');
            return {
                valid: true,
                reason: 'Validation skipped - will check during generation'
            };
        }
    }

    // Function to stop video generation process
    // This only stops the current video generation job, not the entire CLI/server
    function stopVideoGeneration() {
        if (window.currentJobId) {
            addStatusMessage('warning', '🛑', `Stopping current video generation job: ${window.currentJobId}`);
            console.log(`🔍 Attempting to cancel job: ${window.currentJobId}`);

            // Call API to cancel the job
            fetch(`/api/job/${window.currentJobId}/cancel`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
                .then((response) => response.json())
                .then((data) => {
                    if (data.success) {
                        addStatusMessage('success', '✅', 'Process stopped successfully');
                    } else {
                        addStatusMessage('error', '❌', 'Failed to stop process: ' + data.message);
                    }
                })
                .catch((error) => {
                    addStatusMessage('error', '❌', 'Error stopping process: ' + error.message);
                });
        } else {
            addStatusMessage('warning', '⚠️', 'No active job to stop');
            console.log('⚠️ No currentJobId available for cancellation');
        }

        // Clear monitoring
        if (currentJobMonitoring) {
            clearTimeout(currentJobMonitoring);
            currentJobMonitoring = null;
        }

        // Reset UI state
        isGenerationActive = false;
        // Stop continuous log fetching
        stopContinuousLogFetching();

        generateButton.disabled = false;
        generateButton.innerHTML = '<span class="icon">🎬</span> Generate Video';
        const stopBtn = document.getElementById('stop-process-btn');
        if (stopBtn) stopBtn.style.display = 'none';
        progressContainer.classList.add('d-none');
        progressBar.style.width = '0%';

        addStatusMessage('info', 'ℹ️', 'Job stopped. Ready to generate a new video.');
    }

    // Function to start video generation process
    async function startVideoGeneration() {
        // Clear previous status messages
        statusMessages.innerHTML = '';

        // Reset processed log signatures for new job
        processedLogSignatures.clear();

        // Reset video ready message flag for new video
        videoReadyMessageShown = false;

        // Set generation active state
        isGenerationActive = true;

        // Show progress bar and reset color
        progressContainer.classList.remove('d-none');
        progressBar.style.width = '0%';
        progressBar.classList.remove('bg-success'); // Reset to default color

        // Disable generate button and show stop button
        generateButton.disabled = true;
        generateButton.innerHTML =
            '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
        const stopBtn = document.getElementById('stop-process-btn');
        if (stopBtn) stopBtn.style.display = 'inline-block';

        // Get selected options
        const country = countrySelect.value;

        // Get selected platforms (multiple checkboxes)
        const selectedPlatforms = [];
        const platformCheckboxes = document.querySelectorAll('input[name="platforms"]:checked');
        platformCheckboxes.forEach((checkbox) => {
            selectedPlatforms.push(checkbox.value);
        });
        const platform = selectedPlatforms.length > 0 ? selectedPlatforms : []; // Send as array

        // Get selected genres (multiple checkboxes)
        const selectedGenres = [];
        const genreCheckboxes = document.querySelectorAll('input[name="genres"]:checked');
        genreCheckboxes.forEach((checkbox) => {
            selectedGenres.push(checkbox.value);
        });
        const genre = selectedGenres.length > 0 ? selectedGenres : []; // Send as array
        const template = templateSelect.value; // Get selected template ID
        const contentTypeElement = document.querySelector('input[name="contentType"]:checked');
        let contentType = contentTypeElement ? contentTypeElement.value : 'Série';

        // Handle "All" - don't send contentType parameter if "All" is selected
        if (contentType === 'All') {
            contentType = null; // This will be handled in the backend
        }
        const pauseAfterExtraction = document.getElementById('pauseAfterExtraction').checked;

        // Build target URL for validation
        const country_obj = countrySelect.options[countrySelect.selectedIndex];
        const platform_obj = platformSelect.options[platformSelect.selectedIndex];
        const genre_obj = genreSelect.options[genreSelect.selectedIndex];
        const contentType_obj = document.querySelector('input[name="contentType"]:checked') || { value: 'Serie' };

        const targetUrl = buildStreamGankUrl(
            country_obj.value,
            genre_obj.text,
            platform_obj.text,
            contentType_obj.value
        );

        // Validate the URL before proceeding
        addStatusMessage('info', '🚀', 'Starting video generation process...');
        const validation = await validateStreamGankUrl(targetUrl);

        if (!validation.valid) {
            // Stop the process and show error
            addStatusMessage('error', '❌', `Process stopped: ${validation.reason}`);
            addStatusMessage('info', 'ℹ️', `Target URL: ${targetUrl}`);
            addStatusMessage(
                'info',
                '💡',
                'Please try different parameters (genre, platform, or content type) to find available movies.'
            );

            // Re-enable generate button
            generateButton.disabled = false;
            generateButton.innerHTML = 'Generate Video';

            // Hide progress bar
            progressContainer.classList.add('d-none');
            return;
        }

        addStatusMessage('info', 'ℹ️', `Target URL: ${targetUrl}`);

        // Call the actual API endpoint (demo mode disabled)
        callGenerateAPI(country, platform, genre, contentType, template, pauseAfterExtraction);
    }

    // Function to simulate video generation (in production would call the Python script)
    function simulateVideoGeneration(country, platform, genre, contentType) {
        const steps = [
            { message: '🔍 Connecting to database and extracting movies...', time: 2000 },
            { message: '✅ Successfully extracted 3 movies', time: 1000 },
            { message: '📸 Capturing StreamGank screenshots...', time: 3000 },
            { message: '📷 Screenshot 1/3 saved', time: 1000 },
            { message: '📷 Screenshot 2/3 saved', time: 1000 },
            { message: '📷 Screenshot 3/3 saved', time: 1000 },
            { message: '☁️ Uploading 3 files to Cloudinary...', time: 3000 },
            { message: '✅ 3 files uploaded successfully', time: 1000 },
            { message: '🤖 Enriching movie data with AI descriptions...', time: 5000 },
            { message: '✅ All movies enriched', time: 1000 },
            { message: '📝 Generating AI-powered scripts...', time: 3000 },
            { message: '✅ Script generation completed', time: 1000 },
            { message: '🎬 Creating HeyGen avatar videos...', time: 3000 },
            { message: '⏳ Waiting for HeyGen video completion...', time: 10000 },
            { message: '✅ HeyGen video creation completed: 3 videos', time: 1000 },
            { message: '🎥 Creating final video with Creatomate...', time: 8000 },
            { message: '✅ Video generation complete!', time: 1000, isSuccess: true }
        ];

        let progressValue = 0;
        const progressIncrement = 100 / steps.length;
        let currentStep = 0;

        // Function to process each step
        function processStep() {
            if (currentStep < steps.length) {
                const step = steps[currentStep];

                // Add status message
                const messageType = step.isSuccess ? 'success' : step.isError ? 'error' : 'info';
                addStatusMessage(messageType, step.isSuccess ? '✅' : '🔄', step.message);

                // Update progress bar
                progressValue += progressIncrement;
                progressBar.style.width = `${progressValue}%`;
                progressBar.setAttribute('aria-valuenow', progressValue);

                currentStep++;

                // Schedule next step
                setTimeout(processStep, step.time);
            } else {
                // All steps completed
                finishGeneration();
            }
        }

        // Start processing steps
        processStep();
    }

    // Function to finish generation process
    function finishGeneration(data, showVideo = false) {
        // Reset generation state
        isGenerationActive = false;

        // Re-enable generate button and hide stop button
        generateButton.disabled = false;
        generateButton.innerHTML = '<span class="icon">🎬</span> Generate Video';
        const stopBtn = document.getElementById('stop-process-btn');
        if (stopBtn) stopBtn.style.display = 'none';

        // Show results
        videoResults.classList.remove('d-none');

        // Set data from API response or use defaults
        moviesCount.textContent = data && data.moviesCount ? data.moviesCount : '3';
        videosCount.textContent = data && data.videosCount ? data.videosCount : '3';
        groupId.textContent = data && data.groupId ? data.groupId : generateTimestampId();

        // Handle video completion and gallery
        if (showVideo && data && data.videoUrl) {
            // Ensure progress bar is at 100% when showing video
            progressBar.style.width = '100%';
            progressBar.classList.add('bg-success'); // Make it green when complete

            // Hide rendering status
            renderingStatus.classList.add('d-none');

            // Add video to gallery
            addVideoToGallery({
                videoUrl: data.videoUrl,
                creatomateId: data.creatomateId,
                jobId: data.jobId || window.currentJobId || generateTimestampId(),
                timestamp: new Date().toISOString()
            });

            addStatusMessage('success', '🎉', 'Video rendering completed! Added to video gallery below.');
            addStatusMessage('info', '📺', `Total videos generated: ${completedVideos.length}`);
        } else if (showVideo) {
            // Video was supposed to be ready but no URL available
            renderingStatus.classList.add('d-none');
            addStatusMessage(
                'warning',
                '⚠️',
                'Video generation completed but final video URL not available yet. Check status manually.'
            );
        } else if (data && data.creatomateId) {
            // Video is being processed - show rendering status
            renderingStatus.classList.remove('d-none');
            creatomateIdDisplay.textContent = data.creatomateId;
            addStatusMessage('success', '✅', 'Video generation submitted successfully! Monitoring render progress...');
        } else {
            // No video processing
            renderingStatus.classList.add('d-none');
            addStatusMessage('success', '✅', 'Video generation completed!');
        }
    }

    // Function to generate a timestamp ID similar to Python script
    function generateTimestampId() {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hour = String(now.getHours()).padStart(2, '0');
        const minute = String(now.getMinutes()).padStart(2, '0');
        const second = String(now.getSeconds()).padStart(2, '0');

        return `${year}${month}${day}_${hour}${minute}${second}`;
    }

    // Function to create a video item in the gallery
    function createVideoItem(videoData) {
        const videoItem = document.createElement('div');
        videoItem.className = 'video-item';
        videoItem.dataset.jobId = videoData.jobId || 'unknown';

        // Get current form values for context
        const country = countrySelect.options[countrySelect.selectedIndex]?.text || 'Unknown';
        const platform = platformSelect.options[platformSelect.selectedIndex]?.text || 'Unknown';
        const genre = genreSelect.options[genreSelect.selectedIndex]?.text || 'Unknown';
        const contentType = document.querySelector('input[name="contentType"]:checked')?.id || 'unknown';
        const contentTypeText = contentType === 'all' ? 'All' : contentType === 'movie' ? 'Movies' : 'TV Shows';

        const timestamp = new Date().toLocaleString();

        videoItem.innerHTML = `
            <h4>
                <span>🎬</span> 
                Video ${completedVideos.length + 1}
                <span class="job-badge badge bg-success">${videoData.jobId || 'N/A'}</span>
                <span class="timestamp">${timestamp}</span>
            </h4>
            <div class="video-info">
                <strong>${country}</strong> • ${platform} • ${genre} • ${contentTypeText}
                ${videoData.creatomateId ? `• ID: ${videoData.creatomateId}` : ''}
            </div>
            <video controls preload="metadata">
                <source src="${videoData.videoUrl}" type="video/mp4" />
                Your browser does not support the video tag.
            </video>
            <div class="video-actions">
                <a href="${videoData.videoUrl}" target="_blank" class="btn btn-outline-primary btn-sm">
                    <span>🔗</span> Open Video
                </a>
                <a href="${videoData.videoUrl}" download="streamgankvideos_video_${videoData.jobId || 'unknown'}.mp4" class="btn btn-outline-success btn-sm">
                    <span>💾</span> Download
                </a>
                <button class="btn btn-outline-secondary btn-sm copy-video-url" data-url="${videoData.videoUrl}">
                    <span>📋</span> Copy URL
                </button>
                <button class="btn btn-outline-danger btn-sm remove-video" data-job-id="${videoData.jobId}">
                    <span>🗑️</span> Remove
                </button>
            </div>
            <div class="video-url">
                <strong>URL:</strong> ${videoData.videoUrl}
            </div>
        `;

        // Add event listeners for the buttons
        const copyBtn = videoItem.querySelector('.copy-video-url');
        const removeBtn = videoItem.querySelector('.remove-video');

        copyBtn.addEventListener('click', async function () {
            try {
                await navigator.clipboard.writeText(videoData.videoUrl);
                copyBtn.innerHTML = '<span>✅</span> Copied!';
                setTimeout(() => {
                    copyBtn.innerHTML = '<span>📋</span> Copy URL';
                }, 2000);
            } catch (err) {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = videoData.videoUrl;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);

                copyBtn.innerHTML = '<span>✅</span> Copied!';
                setTimeout(() => {
                    copyBtn.innerHTML = '<span>📋</span> Copy URL';
                }, 2000);
            }
        });

        removeBtn.addEventListener('click', function () {
            if (confirm('Are you sure you want to remove this video from the gallery?')) {
                videoItem.remove();
                // Remove from completedVideos array
                completedVideos = completedVideos.filter((v) => v.jobId !== videoData.jobId);
                updateVideoCount();
            }
        });

        return videoItem;
    }

    // Function to add video to gallery
    function addVideoToGallery(videoData) {
        // Add to completed videos array
        completedVideos.push(videoData);

        // Create and add video item
        const videoItem = createVideoItem(videoData);
        videosContainer.appendChild(videoItem);

        // Show gallery and update count
        videoGallery.classList.remove('d-none');
        updateVideoCount();

        // Scroll to the new video
        videoItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // Function to update video count badge
    function updateVideoCount() {
        videoCountBadge.textContent = completedVideos.length;
    }

    // Function to call the generate API - now adds to Redis queue
    async function callGenerateAPI(country, platform, genre, contentType, template, pauseAfterExtraction) {
        try {
            // Set progress bar to 10%
            progressBar.style.width = '10%';

            // Add different message based on pause flag
            if (pauseAfterExtraction) {
                addStatusMessage(
                    'info',
                    '📋',
                    'Adding movie extraction job to queue (will pause after finding movies)...'
                );
            } else {
                addStatusMessage('info', '📋', 'Adding video to Redis queue...');
            }

            // Prepare the request data
            const requestData = {
                country: country,
                platform: platform,
                genre: genre,
                contentType: contentType,
                template: template, // Include selected template ID
                pauseAfterExtraction: pauseAfterExtraction // Include pause flag
            };

            // Call the API endpoint to add to queue
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `Server error: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                addStatusMessage('success', '✅', 'Video added to queue successfully!');
                addStatusMessage('info', '🆔', `Job ID: ${data.jobId}`);
                addStatusMessage('info', '📊', `Queue position: ${data.queuePosition}`);
                addStatusMessage(
                    'info',
                    '📈',
                    `Queue stats - Pending: ${data.queueStatus.pending}, Processing: ${data.queueStatus.processing}`
                );

                // Store job ID for reference
                window.currentJobId = data.jobId;

                // Start log fetching immediately when job is queued
                console.log(`🚀 Starting log fetching for new job: ${data.jobId}`);
                startContinuousLogFetching(data.jobId);

                // Set progress bar to 20% (queued)
                progressBar.style.width = '20%';

                // NO individual job monitoring on dashboard - only refresh queue status
                // Individual job monitoring only happens on dedicated job detail pages
                console.log(`📋 Job ${data.jobId} added to queue - view details at /job/${data.jobId}`);

                // Refresh queue status to show new job in Process Management
                setTimeout(refreshQueueStatus, 1000);
            } else {
                throw new Error(data.message || 'Unknown error occurred');
            }
        } catch (error) {
            console.error('❌ Error adding to queue:', error);
            addStatusMessage('error', '❌', `Error: ${error.message}`);

            // Reset the generate button
            generateButton.disabled = false;
            generateButton.innerHTML = '<span class="icon">🎬</span> Generate Video';
            progressBar.style.width = '0%';
        }
    }

    // REMOVED: Individual job monitoring function - only available on job detail pages
    async function startJobMonitoring(jobId) {
        console.log(`📋 Individual job monitoring disabled on dashboard - view details at /job/${jobId}`);
        return; // No monitoring on dashboard
    }

    // Function to monitor Creatomate status (legacy - may not be needed with Redis queue)
    async function monitorCreatomateStatus(creatomateId, initialData) {
        let attempts = 0;
        const maxAttempts = 60; // Monitor for up to 10 minutes (10 second intervals)
        let lastCreatomateStatus = null;
        let creatomateMessages = new Set(); // Track shown messages to avoid duplicates

        async function checkStatus() {
            try {
                attempts++;

                // Show status check message every attempt (every 30 seconds)
                addStatusMessage('info', '🔍', `Step 7: Checking render status... (${attempts}/${maxAttempts})`);

                // Show time elapsed
                const timeElapsed = Math.floor((attempts * 30) / 60); // Convert to minutes
                if (timeElapsed > 0) {
                    addStatusMessage(
                        'info',
                        '⏱️',
                        `Rendering time: ${timeElapsed} minute${timeElapsed > 1 ? 's' : ''}`
                    );
                }

                const response = await fetch(`/api/status/${creatomateId}`);
                const result = await response.json();

                if (!result.success) {
                    addStatusMessage('error', '❌', 'Failed to get job status');
                    return;
                }

                const job = result.job;
                console.log(`📊 Job ${jobId} status:`, job);

                // Update progress based on job status and progress
                if (job.status === 'pending') {
                    progressBar.style.width = '20%';

                    // Only show message if status changed
                    if (lastStatus !== 'pending') {
                        addStatusMessage(
                            'info',
                            '⏳',
                            `Job is pending in queue (position: ${job.queuePosition || 'unknown'})`
                        );
                        lastStatus = 'pending';
                    }
                } else if (job.status === 'processing') {
                    const progress = Math.max(30, job.progress || 30);
                    progressBar.style.width = `${progress}%`;

                    // Check if this is a new job starting (different job ID)
                    if (lastStatus !== 'processing' || window.currentJobId !== job.id) {
                        if (window.currentJobId && window.currentJobId !== job.id) {
                            addStatusMessage('info', '📋', `Queue: Starting next job ${job.id}`);
                            addStatusMessage('info', '🔄', `Processing job ${job.queuePosition || 'unknown'} in queue`);
                        }
                        window.currentJobId = job.id;

                        // Start continuous log fetching for new processing job
                        console.log(`🔄 Starting log fetching for processing job: ${job.id}`);
                        startContinuousLogFetching(job.id);
                    }

                    // Show current step only if it changed
                    const stepMessage = job.currentStep || `Processing (${progress}% complete)`;
                    if (lastStep !== stepMessage) {
                        // Determine the appropriate icon based on the step message
                        let icon = '🔄';
                        let type = 'info';

                        if (stepMessage.includes('✅') || stepMessage.includes('completed')) {
                            icon = '✅';
                            type = 'success';
                        } else if (stepMessage.includes('🗃️')) {
                            icon = '🗃️';
                        } else if (stepMessage.includes('🤖')) {
                            icon = '🤖';
                        } else if (stepMessage.includes('🎨')) {
                            icon = '🎨';
                        } else if (stepMessage.includes('🎭')) {
                            icon = '🎭';
                        } else if (stepMessage.includes('⏳')) {
                            icon = '⏳';
                        } else if (stepMessage.includes('📱')) {
                            icon = '📱';
                        } else if (stepMessage.includes('🎬')) {
                            icon = '🎬';
                        } else if (stepMessage.includes('🎉')) {
                            icon = '🎉';
                            type = 'success';
                        }

                        addStatusMessage(type, icon, stepMessage);
                        lastStep = stepMessage;
                    }

                    // Check if we should show extracted movies immediately (after Step 1)
                    if (job.showExtractedMovies && !shownMessages.has('extracted-movies')) {
                        if (job.extractedMovies) {
                            addStatusMessage('info', '📋', 'Movies extracted from database:');
                            const movieLines = job.extractedMovies.split('\n').filter((line) => line.trim());
                            movieLines.forEach((movieLine) => {
                                const cleanLine = movieLine.trim().replace(/^\d+\.\s*/, '');
                                if (cleanLine) {
                                    addStatusMessage('info', '🎬', cleanLine);
                                }
                            });
                            shownMessages.add('extracted-movies');
                        }
                    }
                } else if (job.status === 'completed') {
                    progressBar.style.width = '90%';

                    // Check if this was a paused extraction job
                    if (job.pausedAfterExtraction) {
                        // Only show completion message once
                        if (lastStatus !== 'completed') {
                            addStatusMessage('success', '✅', 'Movie extraction completed successfully!');
                            addStatusMessage('info', '⏸️', 'Process paused after extraction as requested');

                            // Display extracted movie names if available
                            if (job.extractedMovies) {
                                addStatusMessage('info', '📋', 'Movies found:');
                                const movieLines = job.extractedMovies.split('\n').filter((line) => line.trim());
                                movieLines.forEach((movieLine) => {
                                    const cleanLine = movieLine.trim().replace(/^\d+\.\s*/, '');
                                    if (cleanLine) {
                                        addStatusMessage('info', '🎬', cleanLine);
                                    }
                                });
                            }

                            addStatusMessage(
                                'success',
                                '✅',
                                'You can now adjust filters and generate again, or continue with these movies'
                            );
                            lastStatus = 'completed';
                        }

                        // Stop continuous log fetching
                        stopContinuousLogFetching();

                        // Reset generate button - user can start new jobs
                        generateButton.disabled = false;
                        generateButton.innerHTML = '<span class="icon">🎬</span> Generate Video';
                        const stopBtn = document.getElementById('stop-process-btn');
                        if (stopBtn) stopBtn.style.display = 'none';
                        isGenerationActive = false;
                        progressBar.style.width = '100%';
                        progressBar.classList.add('bg-success');
                        return; // Stop monitoring
                    }

                    // Only show completion message once for non-paused jobs
                    if (lastStatus !== 'completed') {
                        addStatusMessage('success', '✅', 'Python script completed successfully!');

                        // Display extracted movie names if available (for normal workflow)
                        if (job.extractedMovies) {
                            addStatusMessage('info', '📋', 'Movies used for video generation:');
                            const movieLines = job.extractedMovies.split('\n').filter((line) => line.trim());
                            movieLines.forEach((movieLine) => {
                                const cleanLine = movieLine.trim().replace(/^\d+\.\s*/, '');
                                if (cleanLine) {
                                    addStatusMessage('info', '🎬', cleanLine);
                                }
                            });
                        }

                        lastStatus = 'completed';
                    }

                    if (job.creatomateId && !job.videoUrl) {
                        // Python script is done but video is still rendering in Creatomate
                        if (!shownMessages.has('creatomate-started')) {
                            addStatusMessage('info', '🎬', `Creatomate ID: ${job.creatomateId}`);
                            addStatusMessage('info', '⏳', 'Video is now being rendered by Creatomate...');
                            shownMessages.add('creatomate-started');
                        }

                        // Start monitoring Creatomate status
                        finishGeneration(
                            {
                                creatomateId: job.creatomateId,
                                jobId: job.id,
                                groupId: job.id,
                                moviesCount: 3,
                                videosCount: 3
                            },
                            false
                        ); // Don't show video yet

                        // Add detailed Creatomate status logs
                        addStatusMessage('info', '🎬', 'Step 7: Final video rendering started');
                        addStatusMessage('info', '🎞️', `Creatomate is now composing the final video...`);
                        addStatusMessage('info', '⚙️', `Render ID: ${job.creatomateId}`);
                        addStatusMessage(
                            'info',
                            '⏳',
                            'This process typically takes 2-5 minutes depending on video complexity'
                        );

                        // Start Creatomate monitoring
                        setTimeout(() => {
                            monitorCreatomateStatus(job.creatomateId, {
                                jobId: job.id,
                                groupId: job.id,
                                moviesCount: 3,
                                videosCount: 3
                            });
                        }, 5000);

                        // Reset generate button but continue monitoring
                        generateButton.disabled = false;
                        generateButton.innerHTML = '<span class="icon">🎬</span> Generate Video';
                        return; // Stop job monitoring, start Creatomate monitoring
                    } else if (job.videoUrl) {
                        // Both Python script and Creatomate are complete
                        progressBar.style.width = '100%';

                        // Only show final completion messages once
                        if (!shownMessages.has('video-ready')) {
                            addStatusMessage('success', '🎬', `Video URL: ${job.videoUrl}`);
                            addStatusMessage('success', '🎥', `Creatomate ID: ${job.creatomateId}`);
                            addStatusMessage('success', '🎉', 'Video is ready! Check the video player below.');
                            shownMessages.add('video-ready');
                        }

                        // Show the final video
                        finishGeneration(
                            {
                                videoUrl: job.videoUrl,
                                creatomateId: job.creatomateId,
                                jobId: job.id,
                                groupId: job.id,
                                moviesCount: 3,
                                videosCount: 3
                            },
                            true
                        ); // Show video immediately
                    } else {
                        // Completed but no Creatomate ID or video URL
                        if (!shownMessages.has('no-video-info')) {
                            addStatusMessage('warning', '⚠️', 'Script completed but no video information available.');
                            shownMessages.add('no-video-info');
                        }
                    }

                    // Reset generate button
                    generateButton.disabled = false;
                    generateButton.innerHTML = '<span class="icon">🎬</span> Generate Video';
                    return; // Stop monitoring
                } else if (job.status === 'failed') {
                    progressBar.style.width = '0%';

                    // Only show failure message once
                    if (lastStatus !== 'failed') {
                        const errorMessage = job.error || 'Unknown error';

                        // Check for specific error types and provide better UI feedback
                        if (errorMessage.includes('💳 Insufficient Creatomate credits')) {
                            addStatusMessage('error', '💳', 'Creatomate Credits Exhausted');
                            addStatusMessage('error', '❌', errorMessage);
                            addStatusMessage('info', '💡', 'To resolve this issue:');
                            addStatusMessage('info', '💰', '• Check your Creatomate account balance');
                            addStatusMessage('info', '📈', '• Upgrade your Creatomate subscription');
                            addStatusMessage('info', '🔄', '• Wait for your credits to reset (monthly plans)');
                            addStatusMessage('info', '🔗', '• Visit: https://creatomate.com/account/billing');
                            addStatusMessage('success', '✅', 'Fix your credits and try again - the system is ready!');
                        } else if (errorMessage.includes('🔐 Creatomate authentication failed')) {
                            addStatusMessage('error', '🔐', 'Creatomate Authentication Problem');
                            addStatusMessage('error', '❌', errorMessage);
                            addStatusMessage('info', '💡', 'To resolve this issue:');
                            addStatusMessage('info', '🔑', '• Check your Creatomate API key configuration');
                            addStatusMessage('info', '⚙️', '• Verify API key permissions in your account');
                            addStatusMessage('info', '🔗', '• Visit: https://creatomate.com/account/api-keys');
                        } else if (errorMessage.includes('⏳ Creatomate rate limit exceeded')) {
                            addStatusMessage('error', '⏳', 'Creatomate Rate Limit Exceeded');
                            addStatusMessage('error', '❌', errorMessage);
                            addStatusMessage('info', '💡', 'To resolve this issue:');
                            addStatusMessage('info', '⏰', '• Wait a few minutes before retrying');
                            addStatusMessage('info', '📈', '• Consider upgrading your plan for higher limits');
                            addStatusMessage('success', '✅', 'Wait a bit and try again - the system is ready!');
                        } else if (errorMessage.includes('🎭 HeyGen API error')) {
                            addStatusMessage('error', '🎭', 'HeyGen API Problem');
                            addStatusMessage('error', '❌', errorMessage);
                            addStatusMessage('info', '💡', 'To resolve this issue:');
                            addStatusMessage('info', '🔑', '• Check your HeyGen API credentials');
                            addStatusMessage('info', '💰', '• Verify your HeyGen account has sufficient credits');
                            addStatusMessage('info', '🔗', '• Visit: https://app.heygen.com/settings');
                        } else if (errorMessage.includes('📸 Screenshot capture failed')) {
                            addStatusMessage('error', '📸', 'Screenshot Capture Failed');
                            addStatusMessage('error', '❌', errorMessage);
                            addStatusMessage('info', '💡', 'To resolve this issue:');
                            addStatusMessage('info', '🌐', '• Check your internet connection');
                            addStatusMessage('info', '🔄', '• Try again in a few minutes');
                            addStatusMessage('info', '🎭', '• Try different genre/platform combination');
                            addStatusMessage('success', '✅', 'Network issues are usually temporary - try again!');
                        } else if (errorMessage.includes('🌐 Database connection failed')) {
                            addStatusMessage('error', '🌐', 'Database Connection Problem');
                            addStatusMessage('error', '❌', errorMessage);
                            addStatusMessage('info', '💡', 'To resolve this issue:');
                            addStatusMessage('info', '📡', '• Check your internet connection');
                            addStatusMessage('info', '🔄', '• Try refreshing the page and retry');
                            addStatusMessage('success', '✅', 'Connection issues are usually temporary!');
                        } else if (
                            errorMessage.includes('🎬 Not enough movies available') ||
                            (errorMessage.includes('only') && errorMessage.includes('found with current filters'))
                        ) {
                            addStatusMessage('warning', '🎬', 'Insufficient Movies Found');

                            // Extract and display the main error message
                            const mainError = errorMessage.split('Found movies:')[0].trim();
                            addStatusMessage('error', '❌', mainError);

                            // Extract and display found movies if available
                            const movieMatch = errorMessage.match(/Found movies: ([^.]+)\./);
                            if (movieMatch && movieMatch[1]) {
                                addStatusMessage('info', '🎭', `Movies available: ${movieMatch[1]}`);
                            }

                            addStatusMessage('info', '💡', 'Try these suggestions:');
                            addStatusMessage('info', '🎭', '• Select a different genre');
                            addStatusMessage('info', '📺', '• Try a different platform (Netflix, Prime, etc.)');
                            addStatusMessage('info', '🎥', '• Switch between Movies and TV Shows');
                            addStatusMessage('info', '🌍', '• Try a different country');
                            addStatusMessage(
                                'success',
                                '✅',
                                'You can immediately try new settings - the system is ready!'
                            );
                        } else {
                            // Generic error handling for other failures
                            addStatusMessage('error', '❌', 'Process Failed');
                            addStatusMessage('error', '⚠️', errorMessage);
                            addStatusMessage('info', '💡', 'You can try again with the same or different settings');
                            addStatusMessage('success', '✅', 'The system is ready for your next attempt!');
                        }

                        if (job.retryCount < job.maxRetries) {
                            addStatusMessage(
                                'info',
                                '🔄',
                                `Job will be retried (attempt ${job.retryCount + 1}/${job.maxRetries})`
                            );
                        }

                        lastStatus = 'failed';
                    }

                    // Stop continuous log fetching
                    stopContinuousLogFetching();

                    // Reset generate button and hide stop button
                    generateButton.disabled = false;
                    generateButton.innerHTML = '<span class="icon">🎬</span> Generate Video';
                    document.getElementById('stop-process-btn').style.display = 'none';
                    isGenerationActive = false;
                    return; // Stop monitoring
                } else if (job.status === 'cancelled') {
                    progressBar.style.width = '0%';

                    // Only show cancellation message once
                    if (lastStatus !== 'cancelled') {
                        addStatusMessage('warning', '🛑', 'Job was cancelled');
                        lastStatus = 'cancelled';
                    }

                    // Stop continuous log fetching
                    stopContinuousLogFetching();

                    // Reset generate button and hide stop button
                    generateButton.disabled = false;
                    generateButton.innerHTML = '<span class="icon">🎬</span> Generate Video';
                    document.getElementById('stop-process-btn').style.display = 'none';
                    isGenerationActive = false;
                    return; // Stop monitoring
                }

                // Fetch detailed logs for processing jobs with high frequency
                if (job.status === 'processing' && job.id) {
                    fetchJobLogs(job.id);
                }

                // Continue monitoring if job is still in progress
                if (attempts < maxAttempts && (job.status === 'pending' || job.status === 'processing')) {
                    // Use much shorter interval for processing jobs to catch fast CLI output
                    const interval = job.status === 'processing' ? 500 : 2000; // 0.5s for processing, 2s for pending
                    currentJobMonitoring = setTimeout(monitorJob, interval);
                } else if (attempts >= maxAttempts) {
                    if (!shownMessages.has('timeout')) {
                        addStatusMessage('warning', '⚠️', 'Job monitoring timeout reached');
                        shownMessages.add('timeout');
                    }
                    generateButton.disabled = false;
                    generateButton.innerHTML = '<span class="icon">🎬</span> Generate Video';
                }
            } catch (error) {
                console.error('❌ Error monitoring job:', error);

                // Only show error message once per error type
                const errorKey = `error-${error.message}`;
                if (!shownMessages.has(errorKey)) {
                    addStatusMessage('error', '❌', `Monitoring error: ${error.message}`);
                    shownMessages.add(errorKey);
                }

                // Retry monitoring if not too many attempts
                if (attempts < maxAttempts) {
                    currentJobMonitoring = setTimeout(monitorJob, 15000); // Retry in 15 seconds
                } else {
                    generateButton.disabled = false;
                    generateButton.innerHTML = '<span class="icon">🎬</span> Generate Video';
                }
            }
        }

        // Start monitoring after 5 seconds
        currentJobMonitoring = setTimeout(monitorJob, 5000);
    }

    // Function to monitor Creatomate status (legacy - may not be needed with Redis queue)
    async function monitorCreatomateStatus(creatomateId, initialData) {
        let attempts = 0;
        const maxAttempts = 60; // Monitor for up to 10 minutes (10 second intervals)
        let lastCreatomateStatus = null;
        let creatomateMessages = new Set(); // Track shown messages to avoid duplicates

        async function checkStatus() {
            try {
                attempts++;

                // Show status check message every attempt (every 30 seconds)
                addStatusMessage('info', '🔍', `Step 7: Checking render status... (${attempts}/${maxAttempts})`);

                // Show time elapsed
                const timeElapsed = Math.floor((attempts * 30) / 60); // Convert to minutes
                if (timeElapsed > 0) {
                    addStatusMessage(
                        'info',
                        '⏱️',
                        `Rendering time: ${timeElapsed} minute${timeElapsed > 1 ? 's' : ''}`
                    );
                }

                const response = await fetch(`/api/status/${creatomateId}`);
                const statusData = await response.json();

                console.log('Status check response:', statusData); // Debug log

                if (statusData.success) {
                    const status = statusData.status.toLowerCase();

                    // Only show status update if it changed
                    if (lastCreatomateStatus !== status) {
                        // Show detailed status messages based on Creatomate status
                        if (status === 'planned' || status === 'queued') {
                            addStatusMessage('info', '📋', `Step 7: Video queued for rendering (${status})`);
                        } else if (status === 'processing' || status === 'rendering') {
                            addStatusMessage('info', '🎬', `Step 7: Video is being rendered (${status})`);
                            addStatusMessage('info', '⚙️', 'Compositing video layers, audio, and effects...');
                        } else if (status === 'completed' || status === 'succeeded') {
                            addStatusMessage('success', '✅', `Step 7: Video rendering completed successfully!`);
                        } else if (status === 'failed' || status === 'error') {
                            addStatusMessage('error', '❌', `Step 7: Video rendering failed (${status})`);
                        } else {
                            addStatusMessage('info', '📊', `Step 7: Creatomate status - ${status}`);
                        }
                        lastCreatomateStatus = status;
                    }

                    if (status === 'completed' || status === 'succeeded') {
                        // Set progress bar to 100% and make it green
                        progressBar.style.width = '100%';
                        progressBar.classList.add('bg-success');

                        // Only show completion messages once
                        if (!creatomateMessages.has('completed')) {
                            addStatusMessage('success', '🎉', 'Step 7: Video rendering completed successfully!');
                            addStatusMessage('success', '🎬', 'Final video is ready for viewing and download!');
                            addStatusMessage(
                                'info',
                                '💾',
                                'Video has been added to the gallery below with download link'
                            );
                            addStatusMessage('success', '📊', 'Progress: 100% - Complete workflow finished!');
                            creatomateMessages.add('completed');
                        }

                        // Update the job in Redis with the final video URL
                        if (initialData.jobId && statusData.videoUrl) {
                            try {
                                const updateResponse = await fetch(`/api/job/${initialData.jobId}/complete`, {
                                    method: 'POST',
                                    headers: {
                                        'Content-Type': 'application/json'
                                    },
                                    body: JSON.stringify({
                                        videoUrl: statusData.videoUrl
                                    })
                                });

                                if (updateResponse.ok) {
                                    if (!creatomateMessages.has('redis-updated')) {
                                        addStatusMessage('success', '💾', 'Job updated with final video URL');
                                        creatomateMessages.add('redis-updated');
                                    }
                                } else {
                                    console.error('Failed to update job with video URL');
                                }
                            } catch (error) {
                                console.error('Error updating job:', error);
                            }
                        }

                        // Update the initial data with the final video URL
                        const finalData = {
                            ...initialData,
                            videoUrl: statusData.videoUrl,
                            creatomateId: creatomateId
                        };

                        // Show the video immediately
                        finishGeneration(finalData, true);
                        return; // Exit the monitoring loop
                    } else if (status === 'failed' || status === 'error') {
                        if (!creatomateMessages.has('failed')) {
                            addStatusMessage('error', '❌', 'Video rendering failed. Please try again.');
                            creatomateMessages.add('failed');
                        }
                        finishGeneration(initialData, false);
                        return; // Exit the monitoring loop
                    } else if (attempts < maxAttempts) {
                        // Still processing, check again in 10 seconds
                        const statusText = status.charAt(0).toUpperCase() + status.slice(1);

                        // Only show status every 3 attempts to reduce spam
                        if (attempts % 3 === 1 || attempts === 1) {
                            addStatusMessage(
                                'info',
                                '⏳',
                                `Video status: ${statusText}... (${attempts}/${maxAttempts})`
                            );
                        }

                        // Update progress bar based on status
                        let progressPercent = 90; // Start at 90% (Python script done)
                        if (status.includes('render') || status.includes('process')) {
                            progressPercent = 95; // Rendering in progress
                        }
                        progressBar.style.width = `${progressPercent}%`;

                        // Schedule next check every 30 seconds
                        setTimeout(() => checkStatus(), 30000);
                    } else {
                        // Max attempts reached
                        if (!creatomateMessages.has('timeout')) {
                            addStatusMessage(
                                'warning',
                                '⚠️',
                                'Video monitoring timeout. Use "Check Status" button to check manually.'
                            );
                            creatomateMessages.add('timeout');
                        }
                        // Don't call finishGeneration here - keep the check status button available
                    }
                } else {
                    const errorKey = `status-check-failed-${statusData.message}`;
                    if (!creatomateMessages.has(errorKey)) {
                        addStatusMessage(
                            'error',
                            '❌',
                            `Status check failed: ${statusData.message || 'Unknown error'}`
                        );
                        creatomateMessages.add(errorKey);
                    }

                    if (attempts < maxAttempts) {
                        if (!creatomateMessages.has('retrying-status')) {
                            addStatusMessage('warning', '⚠️', 'Retrying status check in 30 seconds...');
                            creatomateMessages.add('retrying-status');
                        }
                        setTimeout(() => checkStatus(), 30000);
                    } else {
                        if (!creatomateMessages.has('max-attempts-status')) {
                            addStatusMessage('error', '❌', 'Unable to check video status after multiple attempts.');
                            creatomateMessages.add('max-attempts-status');
                        }
                    }
                }
            } catch (error) {
                console.error('Status check error:', error);
                const networkErrorKey = `network-error-${error.message}`;
                if (!creatomateMessages.has(networkErrorKey)) {
                    addStatusMessage('error', '❌', `Network error: ${error.message}`);
                    creatomateMessages.add(networkErrorKey);
                }

                if (attempts < maxAttempts) {
                    if (!creatomateMessages.has('retrying-network')) {
                        addStatusMessage('warning', '⚠️', 'Retrying in 30 seconds...');
                        creatomateMessages.add('retrying-network');
                    }
                    setTimeout(() => checkStatus(), 30000);
                } else {
                    if (!creatomateMessages.has('network-persist')) {
                        addStatusMessage('error', '❌', 'Status monitoring failed after multiple attempts.');
                        creatomateMessages.add('network-persist');
                    }
                }
            }
        }

        // Start checking status after 5 seconds (shorter delay)
        addStatusMessage('info', '🔄', `Starting status monitoring for video: ${creatomateId}`);
        addStatusMessage('info', '⏳', 'Status will be checked every 30 seconds until completion...');
        setTimeout(() => checkStatus(), 5000);
    }

    // Store processed logs to avoid duplicates
    let processedLogSignatures = new Set();

    // Function to organize logs into steps and display them sequentially
    function processLogMessages(logs) {
        // Processing log messages (reduced debugging)

        // Parse and organize logs into structured steps
        const organizedSteps = organizeLogsIntoSteps(logs);

        // Fallback for unorganized logs
        if (organizedSteps.length === 0) {
            // Fallback: display raw logs if no steps found
            logs.forEach((log, index) => {
                if (log.trim()) {
                    setTimeout(() => {
                        addStatusMessage('info', '📝', log.trim());
                    }, index * 300);
                }
            });
            return;
        }

        // Display steps sequentially with nice timing
        displayStepsSequentially(organizedSteps);
    }

    // Function to organize raw logs into structured steps
    function organizeLogsIntoSteps(logs) {
        const steps = [];
        let currentStep = null;

        logs.forEach((log) => {
            if (!log.trim()) return;

            const logText = log.trim();

            // Create signature to avoid duplicates
            const signature = logText.substring(0, 100);
            if (processedLogSignatures.has(signature)) {
                return; // Skip duplicate
            }
            processedLogSignatures.add(signature);

            // Step header detection
            if (logText.includes('[STEP')) {
                const stepHeaderMatch = logText.match(/\[STEP (\d+)\/(\d+)\]\s+(.+)/);
                if (stepHeaderMatch) {
                    const [, stepNum, totalSteps, stepName] = stepHeaderMatch;
                    currentStep = {
                        number: parseInt(stepNum),
                        total: parseInt(totalSteps),
                        name: stepName,
                        messages: [],
                        completed: false,
                        timing: null
                    };
                    steps.push(currentStep);
                }
            }
            // Step completion detection
            else if (logText.includes('✅ STEP') && logText.includes('COMPLETED')) {
                const completedMatch = logText.match(/✅ STEP (\d+) COMPLETED\s*-\s*(.+)/);
                if (completedMatch && currentStep && currentStep.number === parseInt(completedMatch[1])) {
                    currentStep.completed = true;
                    currentStep.timing = completedMatch[2];
                }
            }
            // Movie entries
            else if (logText.match(/^\s*\d+\.\s+.+\(\d{4}\)/)) {
                if (currentStep) {
                    currentStep.messages.push({
                        type: 'movie',
                        icon: '🎬',
                        text: logText
                    });
                }
            }
            // Settings and cache messages
            else if (
                logText.includes('Using settings') ||
                logText.includes('smooth_scroll') ||
                logText.includes('cached')
            ) {
                if (currentStep) {
                    currentStep.messages.push({
                        type: 'info',
                        icon: logText.includes('cached') ? '💾' : '⚙️',
                        text: logText
                    });
                }
            }
            // Other messages
            else if (logText.includes('SUCCESS') || logText.includes('Loaded')) {
                if (currentStep) {
                    currentStep.messages.push({
                        type: 'info',
                        icon: '✅',
                        text: logText
                    });
                }
            }
        });

        console.log(
            `📋 Organized into ${steps.length} steps:`,
            steps.map((s) => `Step ${s.number}: ${s.name}`)
        );
        return steps;
    }

    // Function to display steps sequentially with nice timing
    function displayStepsSequentially(steps) {
        console.log(`🎬 displayStepsSequentially called with ${steps.length} steps`);
        let stepIndex = 0;

        function displayNextStep() {
            console.log(`📋 Displaying step ${stepIndex + 1}/${steps.length}`);

            if (stepIndex >= steps.length) {
                console.log('✅ All steps displayed');
                return;
            }

            const step = steps[stepIndex];
            console.log(`🔍 Processing step:`, step);

            // Display step header
            console.log(`📝 Adding step header: Step ${step.number}/${step.total}: ${step.name}`);
            addStatusMessage('info', '📋', `Step ${step.number}/${step.total}: ${step.name}`);

            // Update progress bar
            const progressPercent = Math.min(10 + (step.number / step.total) * 80, 90);
            progressBar.style.width = `${progressPercent}%`;

            // Display step messages with small delays
            let messageIndex = 0;
            function displayNextMessage() {
                if (messageIndex >= step.messages.length) {
                    // Display completion message if step is completed
                    if (step.completed && step.timing) {
                        setTimeout(() => {
                            addStatusMessage('success', '✅', `Step ${step.number} Completed: ${step.timing}`);

                            // Move to next step after a brief pause
                            setTimeout(() => {
                                stepIndex++;
                                displayNextStep();
                            }, 800); // Pause between steps
                        }, 300);
                    } else {
                        // Move to next step
                        setTimeout(() => {
                            stepIndex++;
                            displayNextStep();
                        }, 500);
                    }
                    return;
                }

                const message = step.messages[messageIndex];
                addStatusMessage(message.type, message.icon, message.text);

                messageIndex++;
                setTimeout(displayNextMessage, 200); // Small delay between messages
            }

            // Start displaying messages after step header
            setTimeout(displayNextMessage, 400);
        }

        // Start displaying steps
        displayNextStep();
    }

    // Track the last log count to avoid re-processing same logs
    let lastLogCount = 0;
    let logFetchInterval = null;

    // Function to fetch job logs for real-time display
    async function fetchJobLogs(jobId) {
        try {
            const response = await fetch(`/api/job/${jobId}/logs`);
            const result = await response.json();

            // Only log when there are actual new logs to process
            if (result.logs && result.logs.length > lastLogCount) {
                console.log(
                    `📝 New logs for ${jobId.slice(-8)}: ${result.logs.length} total (+${result.logs.length - lastLogCount} new)`
                );
            }

            if (result.success && result.logs && result.logs.length > 0) {
                // Only process new logs to avoid duplicates
                if (result.logs.length > lastLogCount) {
                    const newLogs = result.logs.slice(lastLogCount);
                    // Process new logs (reduced logging)

                    const logMessages = newLogs.map((log) => log.message || log.toString());
                    processLogMessages(logMessages);
                    lastLogCount = result.logs.length;
                }
                // Removed repetitive "no new logs" messages to keep Docker logs clean
            }
        } catch (error) {
            console.log('Could not fetch job logs:', error.message);
        }
    }

    // Start continuous log fetching for processing jobs
    function startContinuousLogFetching(jobId) {
        // Clear any existing interval
        if (logFetchInterval) {
            clearInterval(logFetchInterval);
        }

        // Reset log count and processed signatures for new job
        lastLogCount = 0;
        processedLogSignatures.clear();

        // Start with slower polling to let CLI complete chunks
        logFetchInterval = setInterval(() => {
            fetchJobLogs(jobId);
        }, 1000); // 1 second intervals for more stable collection

        console.log(`🔄 Started continuous log fetching for job ${jobId} (every 1000ms)`);
    }

    // Stop continuous log fetching
    function stopContinuousLogFetching() {
        if (logFetchInterval) {
            clearInterval(logFetchInterval);
            logFetchInterval = null;
            lastLogCount = 0;
            console.log('⏹️ Stopped continuous log fetching');
        }
    }

    // Function to add a status message
    function addStatusMessage(type, icon, message) {
        console.log(`💬 addStatusMessage called: ${type} ${icon} ${message}`);

        // Skip individual job progress messages on dashboard - only show on job detail page
        // BUT allow our formatted step messages through
        const isJobProgressMessage =
            (message.includes('Job ID:') ||
                message.includes('Queue position:') ||
                message.includes('Starting job monitoring') ||
                message.includes('Starting video generation') ||
                message.includes('Queue stats') ||
                message.includes('Processing job') ||
                message.includes('Queue: Starting next job')) &&
            !(
                message.startsWith('Step ') || // Allow "Step X/Y:" messages through
                message.includes('Database Extraction') ||
                message.includes('Script Generation') ||
                message.includes('Asset Preparation') ||
                message.includes('HeyGen Video Creation') ||
                message.includes('Video Processing') ||
                message.includes('Scroll Video Generation') ||
                message.includes('Creatomate') ||
                message.includes('Movies extracted') ||
                message.includes('cached script') ||
                message.includes('cached asset') ||
                message.includes('COMPLETED')
            ); // Allow CLI workflow messages through

        // Don't show individual job progress on dashboard - use Process Management table instead
        // But allow these messages to be logged for job detail pages
        if (isJobProgressMessage) {
            console.log(`📊 Job progress (for job detail page): ${message}`);
            return;
        }

        const messageElement = document.createElement('div');
        messageElement.className = `status-message ${type}`;

        // Add data attributes for enhanced CLI-style styling
        if (message.includes('Step') && (message.includes('Completed') || message.includes(':'))) {
            messageElement.setAttribute('data-step', 'true');
        } else if (message.match(/^\d+\.\s+.+\(\d{4}\)/)) {
            messageElement.setAttribute('data-movie', 'true');
        } else if (
            message.includes('Using settings') ||
            message.includes('smooth_scroll') ||
            message.includes('cached') ||
            message.includes('Loaded')
        ) {
            messageElement.setAttribute('data-settings', 'true');
        }

        // Add special styling for percentage progress messages
        const isProgressMessage =
            message.includes('%') &&
            (message.includes('Processing') ||
                message.includes('Downloading') ||
                message.includes('Uploading') ||
                message.includes('Rendering') ||
                message.includes('Generating') ||
                message.includes('Converting') ||
                message.includes('Extracting') ||
                message.includes('Creating') ||
                message.includes('Capturing'));

        if (isProgressMessage) {
            messageElement.classList.add('progress-message');
            // Extract percentage for visual emphasis
            const percentMatch = message.match(/(\d{1,3})%/);
            if (percentMatch) {
                const percent = percentMatch[1];
                message = message.replace(/(\d{1,3})%/, `<strong class="progress-percent">${percent}%</strong>`);
            }
        }

        messageElement.innerHTML = `
            <span class="status-icon">${icon}</span>
            <span class="status-text">${message}</span>
        `;
        statusMessages.appendChild(messageElement);

        // Scroll to the bottom of the status messages
        statusMessages.scrollTop = statusMessages.scrollHeight;
    }

    // Handle manual status check button
    checkStatusBtn.addEventListener('click', async function () {
        const creatomateId = creatomateIdDisplay.textContent;
        if (creatomateId && creatomateId !== '-') {
            checkStatusBtn.disabled = true;
            checkStatusBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Checking...';

            try {
                const response = await fetch(`/api/status/${creatomateId}`);
                const statusData = await response.json();

                if (statusData.success) {
                    const status = statusData.status.toLowerCase();
                    addStatusMessage('info', '🔄', `Manual status check: ${status}`);

                    if (status === 'completed' || status === 'succeeded') {
                        addStatusMessage('success', '🎉', 'Step 7: Video rendering completed! Loading video...');
                        addStatusMessage('success', '💾', 'Video ready for download and viewing');

                        // Create final data object and finish generation
                        const finalData = {
                            videoUrl: statusData.videoUrl,
                            creatomateId: creatomateId,
                            jobId: window.currentJobId || 'manual_check_' + Date.now()
                        };

                        finishGeneration(finalData, true);
                    } else if (status === 'failed' || status === 'error') {
                        addStatusMessage('error', '❌', 'Step 7: Video rendering failed.');
                    } else if (status === 'processing' || status === 'rendering') {
                        addStatusMessage('info', '🎬', `Step 7: Video is being rendered (${status})`);
                        addStatusMessage('info', '⚙️', 'Compositing video layers, audio, and effects...');
                    } else if (status === 'planned' || status === 'queued') {
                        addStatusMessage('info', '📋', `Step 7: Video queued for rendering (${status})`);
                    } else {
                        addStatusMessage('info', '⏳', `Step 7: Status - ${status} (Still processing...)`);
                    }
                } else {
                    addStatusMessage('error', '❌', 'Failed to check status: ' + statusData.message);
                }
            } catch (error) {
                addStatusMessage('error', '❌', 'Error checking status: ' + error.message);
            }

            checkStatusBtn.disabled = false;
            checkStatusBtn.innerHTML = '<span>🔄</span> Check Status';
        }
    });

    // Handle manual video load button
    loadVideoBtn.addEventListener('click', async function () {
        // For your current video - load it directly
        const currentVideoData = {
            videoUrl:
                'https://f002.backblazeb2.com/file/creatomate-c8xg3hsxdu/4a4588bd-d92a-46a1-924d-428d27710c19.mp4',
            creatomateId: '4a4588bd-d92a-46a1-924d-428d27710c19',
            jobId: 'demo_video_' + Date.now(),
            moviesCount: 3,
            videosCount: 3,
            groupId: 'workflow_20250729_113801'
        };

        addStatusMessage('success', '🎬', 'Loading your completed video...');
        finishGeneration(currentVideoData, true);
    });

    // Handle clear logs button
    clearLogsBtn.addEventListener('click', function () {
        statusMessages.innerHTML =
            '<div class="status-message info"><span class="status-icon">🗑️</span><span class="status-text">Logs cleared.</span></div>';
        // Reset video ready message flag when clearing logs
        videoReadyMessageShown = false;
    });

    // Add stop button to control video generation process
    const stopButton = document.createElement('button');
    stopButton.textContent = '🛑 Stop Process';
    stopButton.className = 'btn btn-danger btn-sm ms-2';
    stopButton.id = 'stop-process-btn';
    stopButton.style.display = 'none'; // Initially hidden
    stopButton.addEventListener('click', function () {
        stopVideoGeneration();
    });

    // Add stop button next to clear logs
    document.getElementById('clear-logs-btn').parentNode.appendChild(stopButton);

    // Queue status button event listener
    document.getElementById('queue-status-btn').addEventListener('click', function () {
        const dashboard = document.getElementById('queue-dashboard');
        if (dashboard.style.display === 'none') {
            dashboard.style.display = 'block';
            refreshQueueStatus();
        } else {
            dashboard.style.display = 'none';
        }
    });

    // Refresh queue button event listener
    document.getElementById('refresh-queue-btn').addEventListener('click', refreshQueueStatus);

    // Smart refresh management to prevent overlapping API calls
    let refreshInProgress = false;
    let lastRefreshTime = 0;
    const REFRESH_INTERVAL = 10000; // Set to 10 seconds as requested

    async function smartRefreshQueueStatus() {
        const now = Date.now();

        // Prevent overlapping requests
        if (refreshInProgress || now - lastRefreshTime < 8000) {
            return;
        }

        refreshInProgress = true;
        lastRefreshTime = now;

        try {
            await refreshQueueStatus();
        } finally {
            refreshInProgress = false;
        }
    }

    // Use smart refresh with longer intervals
    setInterval(smartRefreshQueueStatus, REFRESH_INTERVAL);

    // Clear queue button event listener
    document.getElementById('clear-queue-btn').addEventListener('click', async function () {
        if (
            confirm(
                'Are you sure you want to clear all queues? This will remove all pending, processing, completed, and failed jobs.'
            )
        ) {
            try {
                const response = await fetch('/api/queue/clear', { method: 'POST' });
                const result = await response.json();

                if (result.success) {
                    addStatusMessage('success', '✅', 'All queues cleared successfully');
                    refreshQueueStatus();
                } else {
                    addStatusMessage('error', '❌', 'Failed to clear queues');
                }
            } catch (error) {
                addStatusMessage('error', '❌', `Error clearing queues: ${error.message}`);
            }
        }
    });

    // Function to refresh queue status with multi-worker support
    async function refreshQueueStatus() {
        try {
            const response = await fetch('/api/queue/status');
            const result = await response.json();

            if (result.success) {
                const stats = result.stats;

                // Update basic queue stats
                document.getElementById('queue-pending').textContent = stats.pending || 0;
                document.getElementById('queue-processing').textContent = stats.processing || 0;
                document.getElementById('queue-completed').textContent = stats.completed || 0;
                document.getElementById('queue-failed').textContent = stats.failed || 0;

                // Update worker pool information
                document.getElementById('queue-active-workers').textContent = stats.activeWorkers || 0;
                document.getElementById('queue-available-workers').textContent =
                    stats.availableWorkers || stats.maxWorkers || 3;
                document.getElementById('queue-max-workers').textContent = stats.maxWorkers || 3;
                document.getElementById('queue-concurrent-enabled').textContent = stats.concurrentProcessing
                    ? 'Yes'
                    : 'No';
                document.getElementById('queue-concurrent-enabled').className =
                    `badge ${stats.concurrentProcessing ? 'bg-info' : 'bg-secondary'}`;

                // Update professional process management interface (basic stats only - no individual job fetching)
                updateProcessManagement(stats);

                console.log('📊 Queue stats updated:', stats);
            } else {
                console.error('❌ Failed to get queue status');
            }
        } catch (error) {
            console.error('❌ Error getting queue status:', error);
        }
    }

    // Professional Process Management System
    let processData = new Map(); // Store all process information
    let filteredProcesses = []; // Currently filtered processes
    let activeProcessMonitoring = new Map(); // Track active process monitoring

    // Main function to update process management interface
    function updateProcessManagement(stats) {
        const processContainer = document.getElementById('process-management-container');
        const processTableBody = document.getElementById('process-table-body');
        const emptyState = document.getElementById('empty-process-state');

        // Get active jobs and all jobs for comprehensive display
        const activeJobIds = stats.activeJobs || [];
        const hasActiveJobs = activeJobIds.length > 0;

        // Always show process container with job list
        processContainer.style.display = 'block';

        if (hasActiveJobs) {
            // Show basic active job entries in table (without detailed API calls)
            emptyState.style.display = 'none';

            // Create basic job entries for active jobs (no detailed fetching)
            activeJobIds.forEach((jobId) => {
                if (!processData.has(jobId)) {
                    // Create basic process entry with minimal data from stats only
                    processData.set(jobId, {
                        id: jobId,
                        status: 'processing', // Default for active jobs
                        progress: 50, // Estimated progress for active jobs
                        startedAt: new Date().toISOString(),
                        parameters: { country: 'Processing...', platform: 'Active', genre: 'Job' },
                        currentStep: 'Processing in background...',
                        workerId: 'Active'
                    });
                }
            });

            // Remove jobs that are no longer active
            for (let [jobId] of processData.entries()) {
                if (!activeJobIds.includes(jobId) && processData.get(jobId)?.status === 'processing') {
                    // Only remove if it was a basic processing entry (not completed/failed jobs)
                    if (processData.get(jobId)?.currentStep === 'Processing in background...') {
                        processData.delete(jobId);
                    }
                }
            }

            updateProcessTable();
        } else {
            // Show Process Management table with recent jobs when no active jobs
            if (processData.size > 0) {
                emptyState.style.display = 'none';
                updateProcessTable();
            } else {
                // Show empty state only when no jobs at all
                emptyState.style.display = 'block';

                // Add job ID input section to empty state for manual access
                const emptyStateDiv = document.getElementById('empty-process-state');
                if (emptyStateDiv && !emptyStateDiv.querySelector('.job-id-input')) {
                    const jobAccessHTML = `
                        <div class="job-id-input" style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid var(--border-color);">
                            <h6 style="color: var(--text-light); margin-bottom: 1rem;">Access Individual Job Page</h6>
                            <div style="display: flex; gap: 0.5rem; align-items: center; justify-content: center;">
                                <input 
                                    type="text" 
                                    id="manual-job-id" 
                                    placeholder="Enter Job ID (e.g., job_1755341793_diondawkv)" 
                                    onkeypress="if(event.key === 'Enter') openJobPage()"
                                    style="background: var(--dark-bg); border: 1px solid var(--border-color); color: var(--text-light); padding: 0.5rem; border-radius: 4px; width: 300px; font-size: 0.875rem;"
                                />
                                <button 
                                    onclick="openJobPage()" 
                                    style="background: var(--primary-color); color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; font-size: 0.875rem;"
                                >
                                    👁️ View
                                </button>
                            </div>
                            <div id="recent-jobs-list" style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.5rem;">
                                Recent Job IDs: Loading...
                            </div>
                        </div>
                    `;
                    emptyStateDiv.innerHTML += jobAccessHTML;
                }
            }
        }
    }

    // Function to start monitoring individual process (DISABLED for dashboard - only used on individual job pages)
    function startProcessMonitoring(jobId) {
        console.log(
            `🔍 Process monitoring disabled for dashboard - view individual job page for details: /job/${jobId}`
        );
        // Individual job monitoring is now only done on dedicated job detail pages
        // Dashboard only shows basic Process Management table without API calls
    }

    // Function to update the process table
    function updateProcessTable() {
        const processTableBody = document.getElementById('process-table-body');
        const emptyState = document.getElementById('empty-process-state');

        console.log(`📊 updateProcessTable called - processData has ${processData.size} jobs`);
        processData.forEach((job, jobId) => {
            console.log(`  - ${jobId.slice(-12)}: ${job.status} (${job.parameters?.country})`);
        });

        // Apply current filters
        applyProcessFilters();

        console.log(`📊 After filtering: ${filteredProcesses.length} jobs to display`);
        filteredProcesses.forEach((process, index) => {
            console.log(`  ${index + 1}. ${process.id.slice(-12)}: ${process.status}`);
        });

        if (filteredProcesses.length === 0) {
            console.log('📊 No filtered processes to display - showing empty state');
            processTableBody.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }

        emptyState.style.display = 'none';

        // Generate table rows
        const rows = filteredProcesses.map((process) => createProcessRow(process)).join('');
        processTableBody.innerHTML = rows;

        console.log(`📊 Process table updated with ${filteredProcesses.length} rows`);

        // Add click event listeners for navigation
        processTableBody.querySelectorAll('tr[data-job-id]').forEach((row) => {
            row.addEventListener('click', (e) => {
                // Don't trigger row click if clicking on action buttons
                if (e.target.closest('.process-actions-cell')) return;

                const jobId = row.dataset.jobId;
                window.open(`/job/${jobId}?id=${jobId}`, '_blank');
            });
        });
    }

    // Function to create a process table row
    function createProcessRow(process) {
        const jobId = process.id;
        const shortId = jobId.slice(-8);
        const workerId = process.workerId ? process.workerId.slice(-5) : '-';
        const progress = process.progress || 0;
        const status = process.status || 'pending';

        // Format parameters for display
        const params = process.parameters || {};
        const paramDisplay = `
             <div class="process-params">
                 <div class="param-row">
                     <span class="param-flag">CN</span>
                     <span class="param-value">${params.country || '-'}</span>
                 </div>
                 <div class="param-row">
                     <span class="param-flag">PL</span>
                     <span class="param-value">${params.platform || '-'}</span>
                 </div>
                 <div class="param-row">
                     <span class="param-flag">GN</span>
                     <span class="param-value">${(params.genre || '-').slice(0, 15)}${params.genre && params.genre.length > 15 ? '...' : ''}</span>
                 </div>
             </div>
         `;

        // Format start time and duration
        const startTime = process.startedAt ? new Date(process.startedAt).toLocaleTimeString() : '-';
        const duration = process.startedAt ? formatDuration(Date.now() - new Date(process.startedAt).getTime()) : '-';

        // Determine if process is active for styling
        const isActive = ['pending', 'processing'].includes(status);
        const rowClass = isActive ? 'clickable' : '';

        return `
             <tr data-job-id="${jobId}" class="${rowClass}">
                 <td>
                     <span class="process-status-badge ${status}">
                         ${status === 'processing' ? '🔄' : status === 'completed' ? '✅' : status === 'failed' ? '❌' : '⏳'}
                         ${status}
                     </span>
                 </td>
                 <td>
                     <code class="process-id" title="${jobId}">${shortId}</code>
                 </td>
                 <td>
                     <span class="worker-id">${workerId}</span>
                 </td>
                 <td>
                     <div class="table-progress-container">
                         <div class="table-progress-bar" style="width: ${progress}%"></div>
                         <div class="progress-text-small">${progress}%</div>
                     </div>
                 </td>
                 <td>${paramDisplay}</td>
                 <td>
                     <span class="time-display">${startTime}</span>
                 </td>
                 <td>
                     <span class="duration-display">${duration}</span>
                 </td>
                 <td>
                     <div class="process-actions-cell">
                         <a href="/job/${jobId}?id=${jobId}" target="_blank" class="process-action-btn view">
                             👁️ View
                         </a>
                         ${isActive ? `<button onclick="cancelProcessFromTable('${jobId}')" class="process-action-btn cancel">❌ Cancel</button>` : ''}
                     </div>
                 </td>
             </tr>
         `;
    }

    // Function to apply filters to process list
    function applyProcessFilters() {
        const statusFilter = document.getElementById('status-filter')?.value || 'all';
        const searchTerm = document.getElementById('search-processes')?.value.toLowerCase() || '';

        filteredProcesses = Array.from(processData.values()).filter((process) => {
            // Status filter
            if (statusFilter !== 'all' && process.status !== statusFilter) {
                return false;
            }

            // Search filter
            if (searchTerm) {
                const searchableText = [
                    process.id,
                    process.workerId,
                    process.parameters?.country,
                    process.parameters?.platform,
                    process.parameters?.genre,
                    process.parameters?.contentType,
                    process.currentStep
                ]
                    .filter(Boolean)
                    .join(' ')
                    .toLowerCase();

                if (!searchableText.includes(searchTerm)) {
                    return false;
                }
            }

            return true;
        });

        // Sort by status priority and start time
        filteredProcesses.sort((a, b) => {
            const statusPriority = { processing: 0, pending: 1, failed: 2, completed: 3 };
            const priorityA = statusPriority[a.status] || 999;
            const priorityB = statusPriority[b.status] || 999;

            if (priorityA !== priorityB) {
                return priorityA - priorityB;
            }

            // Sort by start time (newest first)
            const timeA = a.startedAt ? new Date(a.startedAt).getTime() : 0;
            const timeB = b.startedAt ? new Date(b.startedAt).getTime() : 0;
            return timeB - timeA;
        });
    }

    // Utility function to format duration
    function formatDuration(ms) {
        if (ms < 1000) return '0s';

        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);

        if (hours > 0) {
            return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds % 60}s`;
        } else {
            return `${seconds}s`;
        }
    }

    // Function to open job page from manual input
    window.openJobPage = function () {
        const jobIdInput = document.getElementById('manual-job-id');
        const jobId = jobIdInput?.value.trim();

        if (!jobId) {
            alert('Please enter a Job ID');
            return;
        }

        // Clean job ID (remove any extra spaces or prefixes)
        const cleanJobId = jobId.replace(/^job_/, 'job_');

        // Open job detail page
        const jobUrl = `/job/${cleanJobId}?id=${cleanJobId}`;
        window.open(jobUrl, '_blank');

        // Clear input after opening
        jobIdInput.value = '';
    };

    // Function to cancel process from table
    window.cancelProcessFromTable = async function (jobId) {
        if (confirm(`Are you sure you want to cancel process ${jobId.slice(-8)}?`)) {
            try {
                const response = await fetch(`/api/job/${jobId}/cancel`, { method: 'POST' });
                const result = await response.json();

                if (result.success) {
                    console.log(`Process ${jobId} cancelled successfully`);
                    // Update will happen automatically through monitoring
                } else {
                    console.error(`Cancel failed: ${result.message}`);
                }
            } catch (error) {
                console.error(`Cancel error: ${error.message}`);
            }
        }
    };

    // Initialize process management event listeners
    function initializeProcessManagement() {
        // Filter change events
        const statusFilter = document.getElementById('status-filter');
        const searchInput = document.getElementById('search-processes');
        const refreshButton = document.getElementById('refresh-processes');
        const clearCompletedButton = document.getElementById('clear-completed');

        if (statusFilter) {
            // Ensure status filter is set to "all" to show completed and failed processes
            statusFilter.value = 'all';
            statusFilter.addEventListener('change', updateProcessTable);
            console.log(`📊 Status filter set to: ${statusFilter.value}`);
        }

        if (searchInput) {
            searchInput.addEventListener('input', updateProcessTable);
        }

        if (refreshButton) {
            refreshButton.addEventListener('click', () => {
                refreshQueueStatus();
                console.log('🔄 Process list refreshed');
            });
        }

        if (clearCompletedButton) {
            clearCompletedButton.addEventListener('click', () => {
                // Remove completed and failed processes from display
                for (let [jobId, process] of processData.entries()) {
                    if (process.status === 'completed' || process.status === 'failed') {
                        processData.delete(jobId);

                        // Stop monitoring if still active
                        if (activeProcessMonitoring.has(jobId)) {
                            clearInterval(activeProcessMonitoring.get(jobId).intervalId);
                            activeProcessMonitoring.delete(jobId);
                        }
                    }
                }
                updateProcessTable();
                console.log('🗑️ Completed processes cleared');
            });
        }
    }

    // Initialize recent jobs data for Process Management table
    async function initializeRecentJobs() {
        try {
            const response = await fetch('/api/queue/jobs');
            const result = await response.json();

            if (result.success && result.jobs) {
                // Convert jobs object to array and get recent jobs (last 10)
                const jobsArray = Object.values(result.jobs);
                const recentJobs = jobsArray.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt)).slice(0, 10); // Show last 10 jobs

                // Populate processData with recent jobs (including completed and failed)
                recentJobs.forEach((job) => {
                    processData.set(job.id, job);
                    console.log(
                        `📋 Added job to processData: ${job.id.slice(-12)} | Status: ${job.status} | Country: ${job.parameters?.country}`
                    );
                });

                // Update the recent jobs list in empty state
                const recentJobsList = document.getElementById('recent-jobs-list');
                if (recentJobsList && recentJobs.length > 0) {
                    const jobLinks = recentJobs
                        .slice(0, 5)
                        .map((job) => {
                            const shortId = job.id.slice(-12);
                            const statusIcon =
                                job.status === 'completed'
                                    ? '✅'
                                    : job.status === 'failed'
                                      ? '❌'
                                      : job.status === 'processing'
                                        ? '🔄'
                                        : '⏳';
                            return `<span 
                            style="cursor: pointer; color: var(--primary-color); text-decoration: underline; margin-right: 1rem;" 
                            onclick="window.open('/job/${job.id}?id=${job.id}', '_blank')"
                            title="${job.status} - ${job.parameters?.country || 'Unknown'} ${job.parameters?.platform || ''}"
                        >${statusIcon} ${shortId}</span>`;
                        })
                        .join('');

                    recentJobsList.innerHTML = `Recent Jobs (clickable): ${jobLinks}`;
                }

                // Update the process table to show recent jobs
                updateProcessTable();

                // Force show the process management container since we have jobs
                const processContainer = document.getElementById('process-management-container');
                if (processContainer && recentJobs.length > 0) {
                    processContainer.style.display = 'block';
                    const emptyState = document.getElementById('empty-process-state');
                    if (emptyState) {
                        emptyState.style.display = 'none';
                    }
                }

                console.log(`📊 Loaded ${recentJobs.length} recent jobs for Process Management`);
            }
        } catch (error) {
            console.error('❌ Failed to load recent jobs:', error);
            const recentJobsList = document.getElementById('recent-jobs-list');
            if (recentJobsList) {
                recentJobsList.innerHTML = 'Recent Job IDs: Failed to load - use manual input above';
            }
        }
    }

    // Initialize everything when DOM is loaded
    document.addEventListener('DOMContentLoaded', function () {
        initializeProcessManagement();

        // Always show Process Management container on page load
        setTimeout(() => {
            const processContainer = document.getElementById('process-management-container');
            if (processContainer) {
                processContainer.style.display = 'block';
                console.log('📋 Process Management container forced to show');
            }
        }, 100);

        initializeRecentJobs(); // Load recent jobs to populate table
        console.log('🎯 Professional Process Management Interface initialized');
    });
});
