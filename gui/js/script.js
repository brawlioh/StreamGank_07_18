document.addEventListener('DOMContentLoaded', function() {
    // Get all form elements
    const countrySelect = document.getElementById('country');
    const platformSelect = document.getElementById('platform');
    const genreSelect = document.getElementById('genre');
    const contentTypeRadios = document.querySelectorAll('input[name="contentType"]');
    const generateButton = document.getElementById('generate-video');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.querySelector('.progress-bar');
    
    // Preview elements
    const previewCountry = document.getElementById('preview-country');
    const previewPlatform = document.getElementById('preview-platform');
    const previewGenre = document.getElementById('preview-genre');
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
    
    // Update preview when form elements change
    countrySelect.addEventListener('change', updatePreview);
    platformSelect.addEventListener('change', updatePreview);
    genreSelect.addEventListener('change', updatePreview);
    contentTypeRadios.forEach(radio => {
        radio.addEventListener('change', updatePreview);
    });
    
    // Initial preview update
    updatePreview();
    
    // Handle form submission
    generateButton.addEventListener('click', startVideoGeneration);
    
    // Function to update preview
    function updatePreview() {
        // Get selected values
        const country = countrySelect.options[countrySelect.selectedIndex];
        const platform = platformSelect.options[platformSelect.selectedIndex];
        const genre = genreSelect.options[genreSelect.selectedIndex];
        const contentType = document.querySelector('input[name="contentType"]:checked');
        
        // Update preview text
        previewCountry.textContent = country.text;
        previewPlatform.textContent = platform.text;
        previewGenre.textContent = genre.text;
        previewType.textContent = contentType.id === 'all' ? 'All' : 
                                (contentType.id === 'movie' ? 'Movies' : 'TV Shows');
        
        // Build and update URL
        const url = buildStreamGankUrl(
            country.value,
            genre.value,
            platform.value,
            contentType.value
        );
        previewUrl.textContent = url;
    }
    
    // Function to build StreamGank URL
    function buildStreamGankUrl(country, genre, platform, type) {
        let url = `https://streamgank.com/?country=${country}`;
        
        if (genre) {
            url += `&genres=${genre}`;
        }
        
        if (platform) {
            // Convert platform format to match website's URL parameter
            const platformParam = platform.toLowerCase().replace('_', '');
            url += `&platforms=${platformParam}`;
        }
        
        if (type && type !== 'all') {
            url += `&type=${type}`;
        }
        
        return url;
    }
    
    // Function to start video generation process
    function startVideoGeneration() {
        // Clear previous status messages
        statusMessages.innerHTML = '';
        
        // Show progress bar
        progressContainer.classList.remove('d-none');
        progressBar.style.width = '0%';
        
        // Disable generate button
        generateButton.disabled = true;
        generateButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
        
        // Get selected options
        const country = countrySelect.value;
        const platform = platformSelect.value.replace('_', ''); // Format for API
        const genre = genreSelect.value;
        const contentType = document.querySelector('input[name="contentType"]:checked').value;
        
        // Add initial status message
        addStatusMessage('info', '🚀', 'Starting video generation process...');
        
        // In development/demo mode, simulate the process
        const isDemoMode = false; // Toggle this for development/production
        
        if (isDemoMode) {
            // Simulate the automated video generation process
            simulateVideoGeneration(country, platform, genre, contentType);
        } else {
            // Call the actual API endpoint
            callGenerateAPI(country, platform, genre, contentType);
        }
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
                const messageType = step.isSuccess ? 'success' : (step.isError ? 'error' : 'info');
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
    function finishGeneration(data) {
        // Re-enable generate button
        generateButton.disabled = false;
        generateButton.innerHTML = '<span class="icon">🎬</span> Generate Video';
        
        // Show results
        videoResults.classList.remove('d-none');
        
        // Set data from API response or use defaults
        moviesCount.textContent = data && data.moviesCount ? data.moviesCount : '3';
        videosCount.textContent = data && data.videosCount ? data.videosCount : '3';
        groupId.textContent = data && data.groupId ? data.groupId : generateTimestampId();
        
        // Show video player with the actual video URL if available
        if (data && data.videoUrl) {
            videoPlayer.classList.remove('d-none');
            finalVideo.src = data.videoUrl;
        } else {
            // For demo, use a placeholder video
            videoPlayer.classList.remove('d-none');
            finalVideo.src = "https://res.cloudinary.com/dodod8s0v/video/upload/v1752902942/Video_for_intro_movie1_q2wb38.mp4";
        }
        
        // Add final success message
        addStatusMessage('success', '🎉', 'Video generation completed successfully! You can now view and download your video.');
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
    
    // Function to call the generate API
    function callGenerateAPI(country, platform, genre, contentType) {
        // Set progress bar to 10%
        progressBar.style.width = '10%';
        
        addStatusMessage('info', '🌐', 'Sending request to server...');
        
        // Prepare the request data
        const requestData = {
            country: country,
            platform: platform,
            genre: genre,
            contentType: contentType
        };
        
        // Call the API endpoint
        fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Server responded with an error');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Process logs to update status
                if (data.logs) {
                    processLogMessages(data.logs);
                }
                
                // Set progress bar to 100%
                progressBar.style.width = '100%';
                
                // Finish the generation process
                finishGeneration(data);
            } else {
                throw new Error(data.message || 'Unknown error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            addStatusMessage('error', '❌', `Error: ${error.message}`);
            
            // Reset the generate button
            generateButton.disabled = false;
            generateButton.innerHTML = '<span class="icon">🎬</span> Generate Video';
        });
    }
    
    // Function to process log messages from the server
    function processLogMessages(logs) {
        let progressValue = 10; // Start at 10% (initial request)
        const progressIncrement = 90 / logs.length; // Distribute remaining 90%
        
        logs.forEach(log => {
            if (log.trim()) { // Only process non-empty logs
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
        messageElement.innerHTML = `
            <span class="status-icon">${icon}</span>
            <span class="status-text">${message}</span>
        `;
        statusMessages.appendChild(messageElement);
        
        // Scroll to the bottom of the status messages
        statusMessages.scrollTop = statusMessages.scrollHeight;
    }
});
