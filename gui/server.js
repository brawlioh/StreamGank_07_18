const express = require('express');
const { spawn } = require('child_process');
const path = require('path');
const VideoQueueManager = require('./queue-manager');

const app = express();
const port = 3000;

// Initialize Redis queue manager
const queueManager = new VideoQueueManager();

// Middleware for parsing JSON and serving static files
app.use(express.json());
app.use(express.static(path.join(__dirname)));

// Enable CORS
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
    next();
});

// Route to serve the main HTML file
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Platform mapping to match Python script expectations
const platformMapping = {
    prime: 'Prime',
    apple_tvplus: 'Apple TV+',
    disney_plus: 'Disney+',
    hulu: 'Hulu',
    max: 'Max',
    netflix: 'Netflix',
};

// Content type mapping
const contentTypeMapping = {
    Film: 'Film',
    Serie: 'Série',
    all: 'Film', // Default to Film for 'all' option
};

// Helper function to execute Python script with async/await
async function executePythonScript(args, cwd = path.join(__dirname, '..'), timeoutMs = 30 * 60 * 1000) {
    return new Promise((resolve, reject) => {
        console.log('Executing command:', 'python', args.join(' '));

        const pythonProcess = spawn('python', args, {
            cwd: cwd,
            env: {
                ...process.env,
                PYTHONIOENCODING: 'utf-8',
                PYTHONUNBUFFERED: '1',
            },
        });

        let stdout = '';
        let stderr = '';
        let isResolved = false;

        // Set up timeout (30 minutes default)
        const timeout = setTimeout(() => {
            if (!isResolved) {
                isResolved = true;
                pythonProcess.kill('SIGTERM');
                reject({
                    code: -2,
                    error: 'Python script execution timeout',
                    stdout,
                    stderr,
                });
            }
        }, timeoutMs);

        // Handle stdout data
        pythonProcess.stdout.on('data', (data) => {
            try {
                const output = data.toString('utf8');
                stdout += output;
                console.log('Python stdout:', output);
            } catch (encodingError) {
                console.warn('Encoding error in stdout:', encodingError.message);
                const output = data.toString('latin1'); // Fallback encoding
                stdout += output;
            }
        });

        // Handle stderr data
        pythonProcess.stderr.on('data', (data) => {
            try {
                const output = data.toString('utf8');
                stderr += output;
                console.error('Python stderr:', output);
            } catch (encodingError) {
                console.warn('Encoding error in stderr:', encodingError.message);
                const output = data.toString('latin1'); // Fallback encoding
                stderr += output;
            }
        });

        // Handle process completion
        pythonProcess.on('close', (code) => {
            if (!isResolved) {
                isResolved = true;
                clearTimeout(timeout);
                console.log(`Python process exited with code ${code}`);

                if (code !== 0) {
                    reject({
                        code,
                        error: stderr || 'Python script failed with no error message',
                        stdout,
                    });
                } else {
                    resolve({
                        code,
                        stdout,
                        stderr,
                    });
                }
            }
        });

        // Handle process errors
        pythonProcess.on('error', (error) => {
            if (!isResolved) {
                isResolved = true;
                clearTimeout(timeout);
                console.error('Failed to start Python process:', error);
                reject({
                    code: -1,
                    error: error.message,
                    stdout: '',
                    stderr: '',
                });
            }
        });
    });
}

// API endpoint to add video to Redis queue
app.post('/api/generate', async (req, res) => {
    try {
        const { country, platform, genre, contentType } = req.body;

        console.log('📨 Received queue request:', { country, platform, genre, contentType });

        if (!country || !platform || !genre || !contentType) {
            return res.status(400).json({
                success: false,
                message: 'Missing required parameters',
                received: { country, platform, genre, contentType },
            });
        }

        // Map platform and content type to match Python script expectations
        const mappedPlatform = platformMapping[platform] || platform;
        const mappedContentType = contentTypeMapping[contentType] || contentType;

        console.log('🔄 Mapped values:', {
            country,
            platform: mappedPlatform,
            genre,
            contentType: mappedContentType,
        });

        // Add job to Redis queue
        const job = await queueManager.addJob({
            country,
            platform: mappedPlatform,
            genre,
            contentType: mappedContentType,
        });

        // Get current queue status
        const queueStatus = await queueManager.getQueueStatus();

        // Return job info and queue status
        res.json({
            success: true,
            jobId: job.id,
            message: 'Video added to queue successfully',
            queuePosition: queueStatus.pending + queueStatus.processing,
            queueStatus: queueStatus,
            job: job,
        });
    } catch (error) {
        console.error('❌ Failed to add job to queue:', error);

        res.status(500).json({
            success: false,
            message: 'Failed to add video to queue',
            error: error.message,
        });
    }
});

// API endpoint to check Creatomate status
app.get('/api/status/:creatomateId', async (req, res) => {
    try {
        const { creatomateId } = req.params;

        const scriptPath = path.join(__dirname, '../automated_video_generator.py');
        const args = [scriptPath, '--check-creatomate', creatomateId];

        // Execute Python script with async/await
        const result = await executePythonScript(args);
        const { stdout } = result;

        // Parse status from output
        let status = 'unknown';
        let videoUrl = '';

        const statusMatch = stdout.match(/Render Status[:\s]+(\w+)/i);
        if (statusMatch && statusMatch[1]) {
            status = statusMatch[1];
        }

        const urlMatch = stdout.match(/Video URL[:\s]+(https:\/\/[^\s\n]+)/i);
        if (urlMatch && urlMatch[1]) {
            videoUrl = urlMatch[1];
        }

        res.json({
            success: true,
            status: status,
            videoUrl: videoUrl,
            creatomateId: creatomateId,
        });
    } catch (error) {
        console.error('Status check failed:', error);

        res.status(500).json({
            success: false,
            message: 'Failed to check status',
            error: error.error || error.message,
        });
    }
});

// API endpoint to test Python script and database connection
app.get('/api/test', async (req, res) => {
    try {
        console.log('Testing Python script and database connection...');

        const scriptPath = path.join(__dirname, '../automated_video_generator.py');
        const args = [scriptPath, '--country', 'FR', '--platform', 'Netflix', '--genre', 'Horror', '--content-type', 'Film', '--num-movies', '1', '--skip-scroll-video', '--all'];

        // Execute with shorter timeout for testing
        const result = await executePythonScript(args, path.join(__dirname, '..'), 5 * 60 * 1000);

        res.json({
            success: true,
            message: 'Python script test completed',
            hasOutput: result.stdout.length > 0,
            outputLength: result.stdout.length,
            preview: result.stdout.substring(0, 500) + (result.stdout.length > 500 ? '...' : ''),
        });
    } catch (error) {
        console.error('Python script test failed:', error);

        res.json({
            success: false,
            message: 'Python script test failed',
            error: error.error || error.message,
            code: error.code,
            stdout: error.stdout ? error.stdout.substring(0, 500) : '',
            stderr: error.stderr ? error.stderr.substring(0, 500) : '',
        });
    }
});

// API endpoint to get job status by ID
app.get('/api/job/:jobId', async (req, res) => {
    try {
        const { jobId } = req.params;
        const job = await queueManager.getJob(jobId);

        if (!job) {
            return res.status(404).json({
                success: false,
                message: 'Job not found',
            });
        }

        res.json({
            success: true,
            job: job,
        });
    } catch (error) {
        console.error('❌ Failed to get job:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to get job status',
            error: error.message,
        });
    }
});

// API endpoint to get queue status
app.get('/api/queue/status', async (req, res) => {
    try {
        // Clean up any orphaned processing jobs first
        await queueManager.cleanupProcessingQueue();

        const stats = await queueManager.getQueueStats();
        res.json({
            success: true,
            stats: stats,
        });
    } catch (error) {
        console.error('❌ Failed to get queue status:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to get queue status',
            error: error.message,
        });
    }
});

// API endpoint to get all jobs
app.get('/api/queue/jobs', async (req, res) => {
    try {
        const jobs = await queueManager.getAllJobs();
        res.json({
            success: true,
            jobs: jobs,
        });
    } catch (error) {
        console.error('❌ Failed to get all jobs:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to get jobs',
            error: error.message,
        });
    }
});

// API endpoint to clear queue (admin only)
app.post('/api/queue/clear', async (req, res) => {
    try {
        await queueManager.clearAllQueues();
        res.json({
            success: true,
            message: 'All queues cleared successfully',
        });
    } catch (error) {
        console.error('❌ Failed to clear queues:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to clear queues',
            error: error.message,
        });
    }
});

// API endpoint to update job with video URL after Creatomate completion
app.post('/api/job/:jobId/complete', async (req, res) => {
    try {
        const { jobId } = req.params;
        const { videoUrl } = req.body;

        if (!videoUrl) {
            return res.status(400).json({
                success: false,
                message: 'Video URL is required',
            });
        }

        const job = await queueManager.getJob(jobId);
        if (!job) {
            return res.status(404).json({
                success: false,
                message: 'Job not found',
            });
        }

        // Update job with final video URL
        job.videoUrl = videoUrl;
        job.progress = 100;
        job.completedAt = new Date().toISOString();
        job.currentStep = 'Video rendering completed!';

        await queueManager.updateJob(job);

        res.json({
            success: true,
            message: 'Job updated with video URL',
            job: job,
        });
    } catch (error) {
        console.error('❌ Failed to update job:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to update job',
            error: error.message,
        });
    }
});

// API endpoint to get available platforms by region from database
app.get('/api/platforms/:country', async (req, res) => {
    try {
        const { country } = req.params;
        console.log(`🌍 Fetching platforms for country: ${country}`);

        // Use the exact platform data provided by the user
        const availablePlatforms = {
            FR: ['Prime', 'Apple TV+', 'Disney+', 'Max', 'Netflix', 'Free'],
            US: ['Prime', 'Apple TV+', 'Disney+', 'Hulu', 'Max', 'Netflix'],
        };

        const platforms = availablePlatforms[country] || availablePlatforms['US']; // Default to US if country not found

        console.log(`✅ Found ${platforms.length} platforms for ${country}:`, platforms);

        res.json({
            success: true,
            country: country,
            platforms: platforms,
            source: 'user_defined',
            count: platforms.length,
        });
    } catch (error) {
        console.error('❌ Error fetching platforms:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to fetch platforms',
            error: error.message,
        });
    }
});

// API endpoint to validate StreamGank URL
app.post('/api/validate-url', async (req, res) => {
    try {
        const { url } = req.body;

        if (!url) {
            return res.status(400).json({
                success: false,
                message: 'URL is required',
            });
        }

        console.log(`🔍 Validating URL: ${url}`);

        // Use node's built-in fetch or a library like axios to check the URL
        const https = require('https');
        const http = require('http');
        const urlParsed = new URL(url);

        const client = urlParsed.protocol === 'https:' ? https : http;

        const validation = await new Promise((resolve, reject) => {
            const request = client.get(
                url,
                {
                    headers: {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    },
                    timeout: 10000,
                },
                (response) => {
                    let data = '';

                    response.on('data', (chunk) => {
                        data += chunk;
                    });

                    response.on('end', () => {
                        // Check for indicators that no movies are available
                        const htmlLower = data.toLowerCase();

                        // More comprehensive empty result indicators
                        const noMoviesIndicators = ['no movies found', 'no results', 'aucun film trouvé', 'aucun résultat', 'no content available', 'pas de contenu disponible', 'empty results', 'résultats vides', 'no movies available', 'aucun film disponible', 'no items found', 'nothing found', 'rien trouvé', 'empty page', 'page vide', '0 results', '0 résultats', 'no matches found', 'aucune correspondance', 'no content matches', 'pas de contenu correspondant', 'no movies match your criteria', 'try modifying your filters', 'modifying your filters', 'no movies match', 'match your criteria'];

                        const hasNoMovies = noMoviesIndicators.some((indicator) => htmlLower.includes(indicator));

                        // Additional specific check for the exact StreamGank message
                        const streamgankNoMoviesMessage = htmlLower.includes('no movies match your criteria') || htmlLower.includes('try modifying your filters') || htmlLower.includes('modifying your filters');

                        // Check if the page has very little content (might indicate empty results)
                        const textContent = data
                            .replace(/<[^>]*>/g, '')
                            .replace(/\s+/g, ' ')
                            .trim();
                        const hasMinimalContent = textContent.length < 1200; // Increased threshold

                        // More specific movie content detection - look for actual movie listings
                        const movieContentIndicators = ['class="movie', 'class="film', 'movie-card', 'film-card', 'poster-image', 'movie-title', 'film-title', 'streaming-item', 'content-item', 'movie-poster', 'film-poster', 'content-card', 'media-card'];

                        const hasMovieElements = movieContentIndicators.some((indicator) => htmlLower.includes(indicator));

                        // Look for actual movie/show titles or IMDb ratings (strong indicators of content)
                        const hasRatings = htmlLower.includes('imdb') || htmlLower.includes('rating') || htmlLower.includes('note');
                        const hasWatchLinks = htmlLower.includes('watch') || htmlLower.includes('regarder') || htmlLower.includes('stream');

                        // Basic content check
                        const hasBasicMovieContent = htmlLower.includes('movie') || htmlLower.includes('film') || htmlLower.includes('série') || htmlLower.includes('show') || htmlLower.includes('title') || htmlLower.includes('poster');

                        // Check for pagination or result count indicators
                        const hasPagination = htmlLower.includes('page') || htmlLower.includes('next') || htmlLower.includes('previous');
                        const hasResultCount = /\d+\s*(results|résultats|movies|films|shows|séries)/.test(htmlLower);

                        // Check for zero results specifically
                        const hasZeroResults = /0\s*(results|résultats|movies|films|shows|séries)/.test(htmlLower);

                        console.log(`🔍 Validation analysis for: ${url}
                        - Has no-movies indicators: ${hasNoMovies}
                        - StreamGank no-movies message: ${streamgankNoMoviesMessage}
                        - Content length: ${textContent.length}
                        - Has minimal content: ${hasMinimalContent}
                        - Has movie elements: ${hasMovieElements}
                        - Has basic movie content: ${hasBasicMovieContent}
                        - Has ratings: ${hasRatings}
                        - Has watch links: ${hasWatchLinks}
                        - Has pagination: ${hasPagination}
                        - Has result count: ${hasResultCount}
                        - Has zero results: ${hasZeroResults}`);

                        // Log first 500 characters of content for debugging
                        console.log(`📄 First 500 chars of page content: ${data.substring(0, 500)}`);

                        // More strict validation logic
                        if (hasNoMovies || hasZeroResults || streamgankNoMoviesMessage) {
                            resolve({
                                valid: false,
                                reason: 'No movies available for the selected parameters',
                                details: 'The StreamGank page explicitly indicates no content was found',
                            });
                        } else if (hasMinimalContent && !hasMovieElements && !hasRatings && !hasWatchLinks) {
                            resolve({
                                valid: false,
                                reason: 'No movie content detected on the page',
                                details: `The page has minimal content (${textContent.length} chars) and no movie indicators`,
                            });
                        } else if (!hasMovieElements && !hasResultCount && !hasPagination && !hasRatings && hasMinimalContent) {
                            resolve({
                                valid: false,
                                reason: 'Page appears to have no movie listings',
                                details: 'No movie elements, ratings, result counts, or pagination found',
                            });
                        } else if (hasBasicMovieContent && (hasMovieElements || hasRatings || hasWatchLinks || hasResultCount)) {
                            resolve({
                                valid: true,
                                reason: 'Movies appear to be available for selected parameters',
                                details: `Page analysis: content=${textContent.length} chars, elements=${hasMovieElements}, ratings=${hasRatings}`,
                            });
                        } else {
                            // When in doubt, assume no movies to be safe
                            resolve({
                                valid: false,
                                reason: 'Cannot confirm movie availability - page structure unclear',
                                details: 'Page analysis inconclusive, assuming no content to avoid wasted processing',
                            });
                        }
                    });
                }
            );

            request.on('error', (error) => {
                console.error('Validation request error:', error);
                reject(error);
            });

            request.on('timeout', () => {
                request.destroy();
                reject(new Error('Request timeout'));
            });
        });

        console.log(`✅ Validation result: ${validation.valid ? 'Valid' : 'Invalid'} - ${validation.reason}`);

        res.json({
            success: true,
            ...validation,
        });
    } catch (error) {
        console.error('❌ Error validating URL:', error);

        // If validation fails, return valid=true to continue (fail-safe approach)
        res.json({
            success: true,
            valid: true,
            reason: 'Validation failed, proceeding anyway',
            details: `Validation error: ${error.message}`,
        });
    }
});

// Initialize Redis connection and start server
async function startServer() {
    try {
        // Connect to Redis
        await queueManager.connect();
        console.log('🔗 Redis queue manager connected');

        // Start the server
        app.listen(port, () => {
            console.log(`🚀 StreamGank Video Generator GUI server running at http://localhost:${port}`);
            console.log(`📋 Redis queue system active`);
            console.log(`🗂️ Platform mappings loaded: ${Object.keys(platformMapping).length} platforms`);
            console.log(`📝 Content type mappings: ${Object.keys(contentTypeMapping).join(', ')}`);
        });
    } catch (error) {
        console.error('❌ Failed to start server:', error);
        process.exit(1);
    }
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n🛑 Shutting down server...');
    await queueManager.close();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('\n🛑 Shutting down server...');
    await queueManager.close();
    process.exit(0);
});

// Start the server
startServer();
