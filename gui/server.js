const express = require('express');
const { exec } = require('child_process');
const path = require('path');
const app = express();
const port = 3000;

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

// API endpoint to start video generation
app.post('/api/generate', (req, res) => {
    const { country, platform, genre, contentType } = req.body;
    
    if (!country || !platform || !genre || !contentType) {
        return res.status(400).json({ success: false, message: 'Missing required parameters' });
    }
    
    // Construct command to run the Python script with parameters
    const command = `python3 ${path.join(__dirname, '../automated_video_generator.py')} --country ${country} --platform ${platform} --genre ${genre} --type ${contentType} --non-interactive`;
    
    // Execute the command
    exec(command, (error, stdout, stderr) => {
        if (error) {
            console.error(`Error: ${error.message}`);
            return res.status(500).json({ success: false, message: error.message });
        }
        
        if (stderr) {
            console.error(`Stderr: ${stderr}`);
        }
        
        console.log(`Stdout: ${stdout}`);
        
        // Parse the output to extract the group ID and other information
        let groupId = '';
        let moviesCount = 0;
        let videosCount = 0;
        let videoUrl = '';
        
        // Extract group ID using regex
        const groupIdMatch = stdout.match(/group ID: ([0-9_]+)/);
        if (groupIdMatch && groupIdMatch[1]) {
            groupId = groupIdMatch[1];
        }
        
        // Extract movies count
        const moviesMatch = stdout.match(/Movies processed: (\d+)/);
        if (moviesMatch && moviesMatch[1]) {
            moviesCount = parseInt(moviesMatch[1], 10);
        }
        
        // Extract videos count
        const videosMatch = stdout.match(/HeyGen videos created: (\d+)/);
        if (videosMatch && videosMatch[1]) {
            videosCount = parseInt(videosMatch[1], 10);
        }
        
        // Extract final video URL (if available)
        const videoUrlMatch = stdout.match(/Final video URL: (https:\/\/[^\s]+)/);
        if (videoUrlMatch && videoUrlMatch[1]) {
            videoUrl = videoUrlMatch[1];
        }
        
        // Return the results
        res.json({
            success: true,
            groupId,
            moviesCount,
            videosCount,
            videoUrl,
            logs: stdout.split('\n')
        });
    });
});

// Start the server
app.listen(port, () => {
    console.log(`StreamGank Video Generator GUI server running at http://localhost:${port}`);
});
