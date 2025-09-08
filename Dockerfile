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

# Install system dependencies in optimized layers (Railway-friendly)
# Layer 1: Essential tools (most stable)
RUN apt-get update && apt-get install -y \
    curl wget ca-certificates gnupg lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Layer 2: Node.js 20 LTS (separate for better caching)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Layer 3: Python and core dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Layer 4: Media processing tools
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Layer 5: Fonts (CRITICAL - DO NOT REMOVE)
RUN apt-get update && apt-get install -y \
    fonts-dejavu-core fonts-dejavu fonts-liberation fontconfig \
    && fc-cache -f -v \
    && rm -rf /var/lib/apt/lists/*

# Layer 6: Chromium and dependencies
RUN apt-get update && apt-get install -y \
    libnss3 libatk-bridge2.0-0 libdrm2 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libxss1 libgconf-2-4 \
    libasound2 libatspi2.0-0 libgtk-3-0 chromium-browser \
    && rm -rf /var/lib/apt/lists/*

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

# Copy package files first for better Docker layer caching (from project root context)
COPY frontend/package.json frontend/package-lock.json /app/frontend/

# Navigate to frontend directory
WORKDIR /app/frontend

# Install dependencies (cached layer - only rebuilds if package.json changes)
RUN npm ci --include=dev

# Verify critical build dependencies are available
RUN npm list vite || echo "Vite not found in list"
RUN npm list @tailwindcss/postcss || echo "Tailwind PostCSS not found in list"

# Pass build-time variables with Railway-friendly defaults
ARG VITE_BACKEND_URL
ARG NODE_ENV=production
ARG APP_ENV=production
ARG WEBHOOK_BASE_URL
ARG WEBHOOK_CREATOMATE_URL
ARG CACHEBUST=1

# Set environment variables for build process
ENV VITE_BACKEND_URL=${VITE_BACKEND_URL}
ENV NODE_ENV=${NODE_ENV}
ENV APP_ENV=${APP_ENV}
ENV WEBHOOK_BASE_URL=${WEBHOOK_BASE_URL}
ENV WEBHOOK_CREATOMATE_URL=${WEBHOOK_CREATOMATE_URL}

# Copy frontend source files (this layer changes frequently)
COPY frontend/ .

# Build the React frontend with Tailwind v4 (CRITICAL - DO NOT REMOVE)
RUN npm run build

# Return to app root
WORKDIR /app

# Create necessary directories
RUN mkdir -p assets videos screenshots clips covers \
    cloudinary creatomate heygen scroll_frames trailers \
    temp_videos responses test_output scripts frontend/logs

# Copy remaining application code (this layer changes most frequently)
# First backup the built frontend dist folder (CRITICAL)
RUN cp -r frontend/dist /tmp/frontend-dist-backup 2>/dev/null || true

# Force cache invalidation for code changes (vm-update/vm-restart)
COPY .docker-build-timestamp* ./

# Copy all application code
COPY . .

# Restore the built frontend dist folder (CRITICAL - overwrite any source version)
RUN if [ -d /tmp/frontend-dist-backup ]; then \
        rm -rf frontend/dist && \
        cp -r /tmp/frontend-dist-backup frontend/dist && \
        rm -rf /tmp/frontend-dist-backup; \
    fi

# Configure Chromium for Playwright (point to system Chromium)
ENV PLAYWRIGHT_BROWSERS_PATH=/usr/bin
ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium-browser

# Health check for unified container
HEALTHCHECK --interval=45s --timeout=15s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" && curl -f http://localhost:3000/health || exit 1

# Expose frontend port
EXPOSE 3000

# Start the frontend server (which can spawn Python processes)
CMD ["node", "frontend/server.js"]