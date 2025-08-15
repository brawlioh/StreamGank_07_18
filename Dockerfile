# StreamGank Video Generator - Unified Container
FROM mcr.microsoft.com/playwright/python:v1.54.0-jammy

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Set working directory
WORKDIR /app

# Install system dependencies (cached layer - rarely changes)
RUN apt-get update && apt-get install -y \
    # FFmpeg for video processing
    ffmpeg \
    # Basic utilities
    curl \
    wget \
    # Node.js for GUI service
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies (cached layer - changes less frequently)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (cached layer - rarely changes)
RUN playwright install chromium

# Copy and install Node.js dependencies (cached layer - changes less frequently)
COPY gui/package*.json ./gui/
RUN cd gui && npm install --only=production

# Create necessary directories (cached layer - rarely changes)
RUN mkdir -p assets videos screenshots clips covers cloudinary creatomate heygen scroll_frames trailers temp_videos responses test_output scripts gui/logs

# Copy application code (this layer changes most frequently, so it's last)
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command - can be overridden in docker-compose
CMD ["tail", "-f", "/dev/null"]