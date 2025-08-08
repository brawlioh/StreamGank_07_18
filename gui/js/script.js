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
    const videoPlayer = document.querySelector('.video-player');
    const finalVideo = document.getElementById('final-video');
    const renderingStatus = document.getElementById('rendering-status');
    const videoUrlLink = document.getElementById('video-url-link');
    const copyUrlBtn = document.getElementById('copy-url-btn');
    const videoUrlDisplay = document.getElementById('video-url-display');
    const checkStatusBtn = document.getElementById('check-status-btn');
    const creatomateIdDisplay = document.getElementById('creatomate-id-display');
    const loadVideoBtn = document.getElementById('load-video-btn');
    const clearLogsBtn = document.getElementById('clear-logs-btn');

    // Track if video ready message has been shown for current video
    let videoReadyMessageShown = false;

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

    // Genre data organized by country
    const genresByCountry = {
        FR: {
            'Action & Aventure': 'Action & Aventure',
            Animation: 'Animation',
            Comédie: 'Comédie',
            'Comédie Romantique': 'Comédie Romantique',
            'Crime & Thriller': 'Crime & Thriller',
            Documentaire: 'Documentaire',
            Drame: 'Drame',
            Fantastique: 'Fantastique',
            'Film de guerre': 'Film de guerre',
            Histoire: 'Histoire',
            Horreur: 'Horreur',
            'Musique & Comédie Musicale': 'Musique & Comédie Musicale',
            'Mystère & Thriller': 'Mystère & Thriller',
            'Pour enfants': 'Pour enfants',
            'Reality TV': 'Reality TV',
            'Réalisé en Europe': 'Réalisé en Europe',
            'Science-Fiction': 'Science-Fiction',
            'Sport & Fitness': 'Sport & Fitness',
            Western: 'Western',
        },
        US: {
            Action: 'Action',
            Animation: 'Animation',
            Comedy: 'Comedy',
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
            Western: 'Western',
        },
        // For other countries, default to English genres
        GB: {
            Action: 'Action',
            Animation: 'Animation',
            Comedy: 'Comedy',
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
            Western: 'Western',
        },
        CA: {
            Action: 'Action',
            Animation: 'Animation',
            Comedy: 'Comedy',
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
            Western: 'Western',
        },
        AU: {
            Action: 'Action',
            Animation: 'Animation',
            Comedy: 'Comedy',
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
            Western: 'Western',
        },
    };

    // HeyGen Template configurations matching the backend
    const heygenTemplates = {
        horror: {
            id: 'ed21a309a5c84b0d873fde68642adea3',
            name: 'Horror/Thriller Cinematic',
            description: 'Specialized template for horror and thriller content',
            genres: ['Horror', 'Horreur', 'Thriller', 'Mystery & Thriller', 'Mystère & Thriller'],
        },
        comedy: {
            id: '15d9eadcb46a45dbbca1834aa0a23ede',
            name: 'Comedy/Light Entertainment',
            description: 'Optimized template for comedy and humorous content',
            genres: ['Comedy', 'Comédie', 'Comédie Romantique'],
        },
        action: {
            id: 'e44b139a1b94446a997a7f2ac5ac4178',
            name: 'Action/Adventure Dynamic',
            description: 'High-energy template for action and adventure content',
            genres: ['Action', 'Action & Adventure', 'Action & Aventure'],
        },
        default: {
            id: 'cc6718c5363e42b282a123f99b94b335',
            name: 'Universal Default',
            description: 'General-purpose template for all other content types',
            genres: ['*'], // Wildcard for all other genres
        },
    };

    // Platform value mapping for FR (display name -> URL parameter value)
    const platformMapping = {
        Prime: 'amazon',
        'Apple TV+': 'apple',
        'Disney+': 'disney',
        Max: 'max',
        Netflix: 'netflix',
        Free: 'free',
    };

    // Genre value mapping for FR (display name -> URL parameter value)
    const genreMapping = {
        'Action & Aventure': 'Action+%26+Aventure',
        Animation: 'Animation',
        Comédie: 'Comédie',
        'Comédie Romantique': 'Comédie+Romantique',
        'Crime & Thriller': 'Crime+%26+Thriller',
        Documentaire: 'Documentaire',
        Drame: 'Drame',
        Fantastique: 'Fantastique',
        'Film de guerre': 'Film+de+guerre',
        Histoire: 'Histoire',
        Horreur: 'Horreur',
        'Musique & Comédie Musicale': 'Musique+%26+Comédie+Musicale',
        'Mystère & Thriller': 'Mystère+%26+Thriller',
        'Pour enfants': 'Pour+enfants',
        'Reality TV': 'Reality+TV',
        'Réalisé en Europe': 'Réalisé+en+Europe',
        'Science-Fiction': 'Science-Fiction',
        'Sport & Fitness': 'Sport+%26+Fitness',
        Western: 'Western',
    };

    // Content type mapping (HTML values -> StreamGank URL parameter values)
    const contentTypeMapping = {
        Film: 'Film', // Movies
        Serie: 'Série', // TV Shows - needs proper French accent for URL
        all: 'all', // All content
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
                // Convert platform name to value format (reverse of platformMapping)
                const platformValue = getPlatformValue(platformName);
                option.value = platformValue;
                option.textContent = platformName;
                platformSelect.appendChild(option);
            });

            // Try to restore previous selection if it exists in the new list
            const availableValues = data.platforms.map((name) => getPlatformValue(name));
            if (currentSelection && availableValues.includes(currentSelection)) {
                platformSelect.value = currentSelection;
            } else {
                // Set default selection (Netflix is usually available)
                const netflixValue = getPlatformValue('Netflix');
                if (availableValues.includes(netflixValue)) {
                    platformSelect.value = netflixValue;
                } else if (availableValues.length > 0) {
                    platformSelect.value = availableValues[0];
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
                US: ['Prime', 'Apple TV+', 'Disney+', 'Hulu', 'Max', 'Netflix'],
            };

            const platforms = fallbackPlatforms[selectedCountry] || fallbackPlatforms['US'];

            platformSelect.innerHTML = '';
            platforms.forEach((platformName) => {
                const option = document.createElement('option');
                const platformValue = getPlatformValue(platformName);
                option.value = platformValue;
                option.textContent = platformName;
                platformSelect.appendChild(option);
            });

            // Restore selection or default to netflix
            const availableValues = platforms.map((name) => getPlatformValue(name));
            if (currentSelection && availableValues.includes(currentSelection)) {
                platformSelect.value = currentSelection;
            } else {
                // Try to set Netflix, otherwise use first available
                const netflixValue = getPlatformValue('Netflix');
                if (availableValues.includes(netflixValue)) {
                    platformSelect.value = netflixValue;
                } else if (availableValues.length > 0) {
                    platformSelect.value = availableValues[0];
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
        // Reverse lookup in platformMapping
        for (const [value, display] of Object.entries(platformMapping)) {
            if (display === platformName) {
                return value;
            }
        }
        // If not found, create value from name
        return platformName.toLowerCase().replace(/[^a-z0-9]/g, '_');
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

    // Handle copy URL button
    copyUrlBtn.addEventListener('click', async function () {
        const videoUrl = videoUrlLink.href;
        if (videoUrl && videoUrl !== '#') {
            try {
                await navigator.clipboard.writeText(videoUrl);
                copyUrlBtn.innerHTML = '<span>✅</span> Copied!';
                setTimeout(() => {
                    copyUrlBtn.innerHTML = '<span>📋</span> Copy URL';
                }, 2000);
            } catch (err) {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = videoUrl;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);

                copyUrlBtn.innerHTML = '<span>✅</span> Copied!';
                setTimeout(() => {
                    copyUrlBtn.innerHTML = '<span>📋</span> Copy URL';
                }, 2000);
            }
        }
    });

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
        previewType.textContent = contentType.id === 'all' ? 'All' : contentType.id === 'movie' ? 'Movies' : 'TV Shows';

        // Build and update URL - pass actual radio button values for correct mapping
        const url = buildStreamGankUrl(country.value, genre.text, platform.text, contentType.value);
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
            // Use French platform mapping for URL parameter
            const platformParam = platformMapping[platform] || platform.toLowerCase().replace('_', '');
            url += `&platforms=${platformParam}`;
        }

        if (type && type !== 'All') {
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
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url }),
            });

            if (!response.ok) {
                throw new Error(`Validation request failed: ${response.status}`);
            }

            const result = await response.json();
            return result;
        } catch (error) {
            // If validation fails, log warning but continue
            console.warn('URL validation failed, continuing with generation:', error);
            addStatusMessage('warning', '⚠️', 'Could not pre-validate URL due to technical limitations, proceeding with generation...');
            addStatusMessage('info', 'ℹ️', 'If no movies are found, the process will stop with a clear error message.');
            return {
                valid: true,
                reason: 'Validation skipped - will check during generation',
            };
        }
    }

    // Function to start video generation process
    async function startVideoGeneration() {
        // Clear previous status messages
        statusMessages.innerHTML = '';

        // Reset video ready message flag for new video
        videoReadyMessageShown = false;

        // Show progress bar and reset color
        progressContainer.classList.remove('d-none');
        progressBar.style.width = '0%';
        progressBar.classList.remove('bg-success'); // Reset to default color

        // Disable generate button
        generateButton.disabled = true;
        generateButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';

        // Get selected options
        const country = countrySelect.value;
        const platform = platformSelect.value; // Send platform value as-is
        const genre = genreSelect.value;
        const template = templateSelect.value; // Get selected template ID
        const contentType = document.querySelector('input[name="contentType"]:checked').value;
        const pauseAfterExtraction = document.getElementById('pauseAfterExtraction').checked;

        // Build target URL for validation
        const country_obj = countrySelect.options[countrySelect.selectedIndex];
        const platform_obj = platformSelect.options[platformSelect.selectedIndex];
        const genre_obj = genreSelect.options[genreSelect.selectedIndex];
        const contentType_obj = document.querySelector('input[name="contentType"]:checked');

        const targetUrl = buildStreamGankUrl(country_obj.value, genre_obj.text, platform_obj.text, contentType_obj.value);

        // Validate the URL before proceeding
        addStatusMessage('info', '🚀', 'Starting video generation process...');
        const validation = await validateStreamGankUrl(targetUrl);

        if (!validation.valid) {
            // Stop the process and show error
            addStatusMessage('error', '❌', `Process stopped: ${validation.reason}`);
            addStatusMessage('info', 'ℹ️', `Target URL: ${targetUrl}`);
            addStatusMessage('info', '💡', 'Please try different parameters (genre, platform, or content type) to find available movies.');

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
            { message: '✅ Video generation complete!', time: 1000, isSuccess: true },
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
        // Re-enable generate button
        generateButton.disabled = false;
        generateButton.innerHTML = '<span class="icon">🎬</span> Generate Video';

        // Show results
        videoResults.classList.remove('d-none');

        // Set data from API response or use defaults
        moviesCount.textContent = data && data.moviesCount ? data.moviesCount : '3';
        videosCount.textContent = data && data.videosCount ? data.videosCount : '3';
        groupId.textContent = data && data.groupId ? data.groupId : generateTimestampId();

        // Only show video player if explicitly requested AND video URL is available
        if (showVideo && data && data.videoUrl) {
            // Ensure progress bar is at 100% when showing video
            progressBar.style.width = '100%';
            progressBar.classList.add('bg-success'); // Make it green when complete

            // Reset video ready message flag for new video
            videoReadyMessageShown = false;

            // Hide rendering status and show video
            renderingStatus.classList.add('d-none');
            videoPlayer.classList.remove('d-none');

            // Test if video URL is accessible
            addStatusMessage('info', '🔗', `Loading video from: ${data.videoUrl}`);
            finalVideo.src = data.videoUrl;

            // Set up video URL link and display
            videoUrlLink.href = data.videoUrl;
            videoUrlDisplay.textContent = data.videoUrl;

            // Remove any existing event listeners to prevent duplicates
            finalVideo.removeEventListener('loadstart', videoLoadStartHandler);
            finalVideo.removeEventListener('canplay', videoCanPlayHandler);
            finalVideo.removeEventListener('error', videoErrorHandler);

            // Add video load event listeners (only once per video)
            finalVideo.addEventListener('loadstart', videoLoadStartHandler);
            finalVideo.addEventListener('canplay', videoCanPlayHandler);
            finalVideo.addEventListener('error', videoErrorHandler);

            addStatusMessage('success', '🎉', 'Video rendering completed! You can now view and download your video.');
        } else if (showVideo) {
            // Video was supposed to be ready but no URL available
            renderingStatus.classList.add('d-none');
            videoUrlLink.href = '#';
            videoUrlDisplay.textContent = 'Not available';
            addStatusMessage('warning', '⚠️', 'Video generation completed but final video URL not available yet. Check status manually.');
        } else if (data && data.creatomateId) {
            // Video is being processed - show rendering status
            renderingStatus.classList.remove('d-none');
            videoPlayer.classList.add('d-none');
            videoUrlLink.href = '#';
            videoUrlDisplay.textContent = 'Processing...';
            creatomateIdDisplay.textContent = data.creatomateId;
            addStatusMessage('success', '✅', 'Video generation submitted successfully! Monitoring render progress...');
        } else {
            // No video processing
            renderingStatus.classList.add('d-none');
            videoUrlLink.href = '#';
            videoUrlDisplay.textContent = '-';
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

    // Function to call the generate API - now adds to Redis queue
    async function callGenerateAPI(country, platform, genre, contentType, template, pauseAfterExtraction) {
        try {
            // Set progress bar to 10%
            progressBar.style.width = '10%';

            // Add different message based on pause flag
            if (pauseAfterExtraction) {
                addStatusMessage('info', '📋', 'Adding movie extraction job to queue (will pause after finding movies)...');
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
                pauseAfterExtraction: pauseAfterExtraction, // Include pause flag
            };

            // Call the API endpoint to add to queue
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData),
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
                addStatusMessage('info', '📈', `Queue stats - Pending: ${data.queueStatus.pending}, Processing: ${data.queueStatus.processing}`);

                // Store job ID for monitoring
                window.currentJobId = data.jobId;

                // Set progress bar to 20% (queued)
                progressBar.style.width = '20%';

                // Start monitoring job status
                startJobMonitoring(data.jobId);
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

    // Function to monitor Redis job status
    async function startJobMonitoring(jobId) {
        let attempts = 0;
        const maxAttempts = 180; // Monitor for up to 30 minutes (10 second intervals)
        let lastStatus = null;
        let lastStep = null;
        let shownMessages = new Set(); // Track shown messages to avoid duplicates

        addStatusMessage('info', '👀', 'Starting job monitoring...');

        const monitorJob = async () => {
            try {
                attempts++;

                // Get job status from Redis
                const response = await fetch(`/api/job/${jobId}`);
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
                        addStatusMessage('info', '⏳', `Job is pending in queue (position: ${job.queuePosition || 'unknown'})`);
                        lastStatus = 'pending';
                    }
                } else if (job.status === 'processing') {
                    const progress = Math.max(30, job.progress || 30);
                    progressBar.style.width = `${progress}%`;

                    // Show current step only if it changed
                    const stepMessage = job.currentStep || `Processing (${progress}% complete)`;
                    if (lastStep !== stepMessage) {
                        addStatusMessage('info', '🔄', stepMessage);
                        lastStep = stepMessage;
                    }
                } else if (job.status === 'completed') {
                    progressBar.style.width = '90%';

                    // Only show completion message once
                    if (lastStatus !== 'completed') {
                        addStatusMessage('success', '✅', 'Python script completed successfully!');
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
                                videosCount: 3,
                            },
                            false
                        ); // Don't show video yet

                        // Start Creatomate monitoring
                        setTimeout(() => {
                            monitorCreatomateStatus(job.creatomateId, {
                                jobId: job.id,
                                groupId: job.id,
                                moviesCount: 3,
                                videosCount: 3,
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
                                videosCount: 3,
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
                        addStatusMessage('error', '❌', `Job failed: ${job.error || 'Unknown error'}`);

                        if (job.retryCount < job.maxRetries) {
                            addStatusMessage('info', '🔄', `Job will be retried (attempt ${job.retryCount + 1}/${job.maxRetries})`);
                        }

                        lastStatus = 'failed';
                    }

                    // Reset generate button
                    generateButton.disabled = false;
                    generateButton.innerHTML = '<span class="icon">🎬</span> Generate Video';
                    return; // Stop monitoring
                }

                // Continue monitoring if job is still in progress
                if (attempts < maxAttempts && (job.status === 'pending' || job.status === 'processing')) {
                    // Use shorter interval for processing jobs to get real-time updates
                    const interval = job.status === 'processing' ? 3000 : 8000; // 3s for processing, 8s for pending
                    setTimeout(monitorJob, interval);
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
                    setTimeout(monitorJob, 15000); // Retry in 15 seconds
                } else {
                    generateButton.disabled = false;
                    generateButton.innerHTML = '<span class="icon">🎬</span> Generate Video';
                }
            }
        };

        // Start monitoring after 5 seconds
        setTimeout(monitorJob, 5000);
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

                // Only show attempt message every 5 attempts to reduce spam
                if (attempts % 5 === 1 || attempts === 1) {
                    addStatusMessage('info', '🔍', `Checking Creatomate status... (attempt ${attempts}/${maxAttempts})`);
                }

                const response = await fetch(`/api/status/${creatomateId}`);
                const statusData = await response.json();

                console.log('Status check response:', statusData); // Debug log

                if (statusData.success) {
                    const status = statusData.status.toLowerCase();

                    // Only show status update if it changed
                    if (lastCreatomateStatus !== status) {
                        addStatusMessage('info', '📊', `Creatomate status: ${status}`);
                        lastCreatomateStatus = status;
                    }

                    if (status === 'completed' || status === 'succeeded') {
                        // Set progress bar to 100% and make it green
                        progressBar.style.width = '100%';
                        progressBar.classList.add('bg-success');

                        // Only show completion messages once
                        if (!creatomateMessages.has('completed')) {
                            addStatusMessage('success', '🎉', 'Video rendering completed successfully!');
                            addStatusMessage('success', '🔗', `Video URL: ${statusData.videoUrl}`);
                            addStatusMessage('success', '📊', 'Progress: 100% - Video generation complete!');
                            creatomateMessages.add('completed');
                        }

                        // Update the job in Redis with the final video URL
                        if (initialData.jobId && statusData.videoUrl) {
                            try {
                                const updateResponse = await fetch(`/api/job/${initialData.jobId}/complete`, {
                                    method: 'POST',
                                    headers: {
                                        'Content-Type': 'application/json',
                                    },
                                    body: JSON.stringify({
                                        videoUrl: statusData.videoUrl,
                                    }),
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
                            creatomateId: creatomateId,
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
                            addStatusMessage('info', '⏳', `Video status: ${statusText}... (${attempts}/${maxAttempts})`);
                        }

                        // Update progress bar based on status
                        let progressPercent = 90; // Start at 90% (Python script done)
                        if (status.includes('render') || status.includes('process')) {
                            progressPercent = 95; // Rendering in progress
                        }
                        progressBar.style.width = `${progressPercent}%`;

                        // Schedule next check
                        setTimeout(() => checkStatus(), 10000);
                    } else {
                        // Max attempts reached
                        if (!creatomateMessages.has('timeout')) {
                            addStatusMessage('warning', '⚠️', 'Video monitoring timeout. Use "Check Status" button to check manually.');
                            creatomateMessages.add('timeout');
                        }
                        // Don't call finishGeneration here - keep the check status button available
                    }
                } else {
                    const errorKey = `status-check-failed-${statusData.message}`;
                    if (!creatomateMessages.has(errorKey)) {
                        addStatusMessage('error', '❌', `Status check failed: ${statusData.message || 'Unknown error'}`);
                        creatomateMessages.add(errorKey);
                    }

                    if (attempts < maxAttempts) {
                        if (!creatomateMessages.has('retrying-status')) {
                            addStatusMessage('warning', '⚠️', 'Retrying status check in 10 seconds...');
                            creatomateMessages.add('retrying-status');
                        }
                        setTimeout(() => checkStatus(), 10000);
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
                        addStatusMessage('warning', '⚠️', 'Retrying in 15 seconds...');
                        creatomateMessages.add('retrying-network');
                    }
                    setTimeout(() => checkStatus(), 15000);
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
        addStatusMessage('info', '⏳', 'Status monitoring will begin in 5 seconds...');
        setTimeout(() => checkStatus(), 5000);
    }

    // Function to process log messages from the server
    function processLogMessages(logs) {
        let progressValue = 10; // Start at 10% (initial request)
        const progressIncrement = 90 / logs.length; // Distribute remaining 90%

        logs.forEach((log) => {
            if (log.trim()) {
                // Only process non-empty logs
                let type = 'info';
                let icon = '🔄';

                // Determine message type and icon based on content
                if (log.includes('ERROR') || log.includes('❌')) {
                    type = 'error';
                    icon = '❌';
                } else if (log.includes('SUCCESS') || log.includes('✅')) {
                    type = 'success';
                    icon = '✅';
                } else if (log.includes('WARNING')) {
                    type = 'warning';
                    icon = '⚠️';
                }

                // Extract the actual message without timestamp and level
                const messageMatch = log.match(/\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - \w+ - (.+)/);
                const message = messageMatch ? messageMatch[1] : log;

                // Add the status message
                addStatusMessage(type, icon, message);

                // Update progress bar
                progressValue += progressIncrement;
                progressBar.style.width = `${Math.min(progressValue, 95)}%`; // Cap at 95% until complete
            }
        });
    }

    // Function to add a status message
    function addStatusMessage(type, icon, message) {
        const messageElement = document.createElement('div');
        messageElement.className = `status-message ${type}`;

        // Add special styling for percentage progress messages
        const isProgressMessage = message.includes('%') && (message.includes('Processing') || message.includes('Downloading') || message.includes('Uploading') || message.includes('Rendering') || message.includes('Generating') || message.includes('Converting') || message.includes('Extracting') || message.includes('Creating') || message.includes('Capturing'));

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
                        addStatusMessage('success', '🎉', 'Video rendering completed! Loading video...');

                        // Create final data object and finish generation
                        const finalData = {
                            videoUrl: statusData.videoUrl,
                            creatomateId: creatomateId,
                        };

                        finishGeneration(finalData, true);
                    } else if (status === 'failed' || status === 'error') {
                        addStatusMessage('error', '❌', 'Video rendering failed.');
                    } else {
                        addStatusMessage('info', '⏳', `Status: ${status} - Still processing...`);
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
            videoUrl: 'https://f002.backblazeb2.com/file/creatomate-c8xg3hsxdu/4a4588bd-d92a-46a1-924d-428d27710c19.mp4',
            creatomateId: '4a4588bd-d92a-46a1-924d-428d27710c19',
            moviesCount: 3,
            videosCount: 3,
            groupId: 'workflow_20250729_113801',
        };

        addStatusMessage('success', '🎬', 'Loading your completed video...');
        finishGeneration(currentVideoData, true);
    });

    // Handle clear logs button
    clearLogsBtn.addEventListener('click', function () {
        statusMessages.innerHTML = '<div class="status-message info"><span class="status-icon">🗑️</span><span class="status-text">Logs cleared.</span></div>';
        // Reset video ready message flag when clearing logs
        videoReadyMessageShown = false;
    });

    // Add test button to force show video section (for debugging)
    const testVideoBtn = document.createElement('button');
    testVideoBtn.textContent = '🎬 Test Video Display';
    testVideoBtn.className = 'btn btn-warning btn-sm ms-2';
    testVideoBtn.addEventListener('click', function () {
        console.log('🧪 Testing video display...');

        // Force show video section with test data
        finishGeneration(
            {
                videoUrl: 'https://player.vimeo.com/external/371433846.sd.mp4?s=236da2f3c0fd273d2c6d9a064f3ae35579b2bbdf&profile_id=139&oauth2_token_id=57447761',
                creatomateId: 'test-12345',
                groupId: 'test-group',
                moviesCount: 3,
                videosCount: 3,
            },
            true
        );

        addStatusMessage('success', '🧪', 'Test video display triggered!');
    });

    // Add test button next to clear logs
    document.getElementById('clear-logs-btn').parentNode.appendChild(testVideoBtn);

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

    // Clear queue button event listener
    document.getElementById('clear-queue-btn').addEventListener('click', async function () {
        if (confirm('Are you sure you want to clear all queues? This will remove all pending, processing, completed, and failed jobs.')) {
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

    // Function to refresh queue status
    async function refreshQueueStatus() {
        try {
            const response = await fetch('/api/queue/status');
            const result = await response.json();

            if (result.success) {
                const stats = result.stats;
                document.getElementById('queue-pending').textContent = stats.pending || 0;
                document.getElementById('queue-processing').textContent = stats.processing || 0;
                document.getElementById('queue-completed').textContent = stats.completed || 0;
                document.getElementById('queue-failed').textContent = stats.failed || 0;

                console.log('📊 Queue stats updated:', stats);
            } else {
                console.error('❌ Failed to get queue status');
            }
        } catch (error) {
            console.error('❌ Error getting queue status:', error);
        }
    }
});
