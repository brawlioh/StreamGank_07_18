# StreamGank Video Generator GUI

A modern web interface for the StreamGank Automated Video Generator, matching the styling of the StreamGank website.

## Features

- User-friendly interface for selecting video generation parameters
- Real-time status updates during video generation
- Video preview functionality
- Responsive design matching the StreamGank website
- Seamless integration with the Python backend

## Installation

1. Install Node.js dependencies:

```bash
cd gui
npm install
```

2. Make sure Python dependencies are installed:

```bash
pip install -r ../requirements.txt
```

## Usage

1. Start the Node.js server:

```bash
cd gui
npm start
```

2. Open your browser and navigate to:

```
http://localhost:3000
```

3. Select your video generation parameters:
   - Streaming Country
   - Platform
   - Genre
   - Content Type

4. Click "Generate Video" to start the process

5. Monitor the generation progress in real-time

6. View the final video when processing completes

## Development

For development with hot-reloading:

```bash
npm run dev
```

## Integration

The GUI integrates with the existing Python backend using a Node.js Express server as middleware. It calls the `automated_video_generator.py` script with the appropriate parameters selected through the interface.

## Note

For demonstration purposes, the GUI is currently set to simulation mode. To connect with the actual Python backend, set `isDemoMode` to `false` in the `script.js` file.
