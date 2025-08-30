# StreamGank - Size Optimized Container (4.7GB → 2.4GB)
# Removes unnecessary Firefox/WebKit, keeps only headless Chromium
FROM ubuntu:22.04

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV NODE_ENV=production
ENV PORT=3000
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies in single layer (optimized for size)
RUN apt-get update && apt-get install -y \
    # Essential tools
    curl wget ca-certificates gnupg lsb-release \
    # Python 3.11
    python3 python3-pip python3-dev \
    # FFmpeg for video processing (CRITICAL)
    ffmpeg \
    # FONTS for poster generation (CRITICAL - DO NOT REMOVE)
    fonts-dejavu-core fonts-dejavu fonts-liberation \
    fontconfig \
    # Dependencies for Chromium
    libnss3 libatk-bridge2.0-0 libdrm2 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libxss1 libgconf-2-4 \
    libasound2 libatspi2.0-0 libgtk-3-0 \
    # Add Node.js 20 LTS
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    # Install only Chromium (not full Playwright suite)
    && apt-get install -y chromium-browser \
    # Refresh font cache (CRITICAL for poster fonts)
    && fc-cache -f -v \
    # Clean up to reduce image size
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y \
    && apt-get autoclean

# Create Python alias and install pip dependencies
RUN ln -s /usr/bin/python3 /usr/bin/python

# Copy Python requirements first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies (keep existing versions)
RUN pip3 install --no-cache-dir -r requirements.txt \
    # Install playwright-python package only (not full browsers)
    && pip3 install --no-cache-dir playwright==1.54.0 \
    # Configure Chromium path for Playwright
    && mkdir -p /ms-playwright \
    && echo "PLAYWRIGHT_BROWSERS_PATH=/usr/bin" >> /etc/environment

# Copy GUI source files for building
COPY gui/ gui/

# Navigate to GUI and install dependencies
WORKDIR /app/gui
RUN npm install --production=false

# Build the GUI (CRITICAL - DO NOT REMOVE)
RUN npm run build

# Return to app root
WORKDIR /app

# Create necessary directories
RUN mkdir -p assets videos screenshots clips covers \
    cloudinary creatomate heygen scroll_frames trailers \
    temp_videos responses test_output scripts gui/logs

# Copy remaining application code (this layer changes most frequently)
# First backup the built GUI dist folder (CRITICAL)
RUN cp -r gui/dist /tmp/gui-dist-backup 2>/dev/null || true

# Copy all application code
COPY . .

# Restore the built GUI dist folder (CRITICAL - overwrite any source version)
RUN if [ -d /tmp/gui-dist-backup ]; then \
        rm -rf gui/dist && \
        cp -r /tmp/gui-dist-backup gui/dist && \
        rm -rf /tmp/gui-dist-backup; \
    fi

# Configure Chromium for Playwright (point to system Chromium)
ENV PLAYWRIGHT_BROWSERS_PATH=/usr/bin
ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium-browser

# Health check for unified container
HEALTHCHECK --interval=45s --timeout=15s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" && curl -f http://localhost:3000/health || exit 1

# Expose GUI port
EXPOSE 3000

# Start both services (GUI server which can spawn Python processes)
CMD ["node", "gui/server.js"]