# StreamGank - Optimized Unified Container
# Single container with Python + Node.js optimized for size and performance
FROM mcr.microsoft.com/playwright/python:v1.54.0-jammy

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV NODE_ENV=production
ENV PORT=3000

# Set working directory
WORKDIR /app

# Install system dependencies and Node.js in one layer (optimized)
RUN apt-get update && apt-get install -y \
    # Essential tools
    curl wget \
    # FFmpeg for video processing
    ffmpeg \
    # Add Node.js 20 LTS
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    # Clean up to reduce image size
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

# Copy and install Python dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip cache purge

# Install Playwright browsers (cached layer)
RUN playwright install chromium \
    && playwright install-deps

# Copy and install Node.js dependencies including dev deps for building (cached layer)  
COPY gui/package*.json ./gui/
RUN cd gui && npm install --production=false \
    && npm cache clean --force

# Copy GUI source code for building (before main copy to leverage caching)
COPY gui/ ./gui/

# Build Vite project to generate updated dist/ folder
RUN cd gui && npm run build \
    && echo "✅ Vite build completed - dist/ folder updated"

# Install only production dependencies after build (optimize image size)
RUN cd gui && npm prune --production \
    && npm cache clean --force

# Create necessary directories
RUN mkdir -p assets videos screenshots clips covers \
    cloudinary creatomate heygen scroll_frames trailers \
    temp_videos responses test_output scripts gui/logs

# Copy remaining application code (this layer changes most frequently)
# First backup the built GUI dist folder
RUN cp -r gui/dist /tmp/gui-dist-backup 2>/dev/null || true

# Copy all application code
COPY . .

# Restore the built GUI dist folder (overwrite any source version)
RUN if [ -d /tmp/gui-dist-backup ]; then \
        rm -rf gui/dist && \
        cp -r /tmp/gui-dist-backup gui/dist && \
        rm -rf /tmp/gui-dist-backup; \
    fi

# Health check for unified container
HEALTHCHECK --interval=45s --timeout=15s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" && curl -f http://localhost:3000/health || exit 1

# Expose GUI port
EXPOSE 3000

# Start both services (GUI server which can spawn Python processes)
CMD ["node", "gui/server.js"]
