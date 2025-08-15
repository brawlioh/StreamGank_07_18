# 🐳 StreamGank Docker Setup

This guide will help you run StreamGank using Docker containers for a consistent, isolated environment.

## 📋 Prerequisites

-   Docker (version 20.10+)
-   Docker Compose (version 2.0+)
-   At least 4GB RAM available for containers
-   10GB free disk space

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Make the script executable (Linux/macOS)
chmod +x docker-scripts.sh

# Setup dependencies and environment
./docker-scripts.sh setup
```

### 2. Configure Environment Variables

Edit the `.env` file with your actual API keys and configurations:

```bash
# Copy the example and edit
cp docker.env.example .env
nano .env  # or use your preferred editor
```

Required configurations:

-   `SUPABASE_URL` and `SUPABASE_KEY`
-   `OPENAI_API_KEY` or `GEMINI_API_KEY`
-   `HEYGEN_API_KEY`
-   `CREATOMATE_API_KEY` and `CREATOMATE_PROJECT_ID`
-   `CLOUDINARY_*` credentials

### 3. Build and Start Services

```bash
# Build all services
./docker-scripts.sh build

# Start in production mode
./docker-scripts.sh start
```

### 4. Access the Application

-   **GUI Interface**: http://localhost:3000
-   **Redis**: localhost:6379

## 🛠️ Development Mode

For development with live code reloading:

```bash
# Start in development mode
./docker-scripts.sh dev

# View logs
./docker-scripts.sh logs

# View logs for specific service
./docker-scripts.sh logs streamgank-gui
```

## 📋 Available Commands

### Management Scripts

```bash
./docker-scripts.sh setup     # Check dependencies and setup environment
./docker-scripts.sh build     # Build all Docker services
./docker-scripts.sh start     # Start in production mode
./docker-scripts.sh dev       # Start in development mode
./docker-scripts.sh stop      # Stop all services
./docker-scripts.sh logs      # View all logs
./docker-scripts.sh cleanup   # Remove all containers and volumes
```

### CLI Commands in Container

```bash
# Run Python CLI commands directly in the container
./docker-scripts.sh cli main.py --help
./docker-scripts.sh cli main.py --country US --platform Netflix --genre Horror --content-type Film
./docker-scripts.sh cli main.py --get-platforms US
```

### Direct Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Execute commands in backend container
docker-compose exec streamgank-backend python main.py --help

# Access backend container shell
docker-compose exec streamgank-backend bash

# Access GUI container shell
docker-compose exec streamgank-gui sh
```

## 🏗️ Architecture

### Services

1. **streamgank-backend**: Python application with all dependencies
2. **streamgank-gui**: Node.js web server for the GUI
3. **redis**: Job queue and caching

### Volumes

-   **Persistent data**: Assets, videos, screenshots are mounted as volumes
-   **Redis data**: Persistent Redis data storage
-   **Source code**: Mounted in development mode for live reloading

### Networks

-   **streamgank-network**: Internal bridge network for service communication

## 🔧 Configuration

### Environment Variables

Key environment variables for Docker deployment:

```bash
# Application
APP_ENV=docker

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Python
PYTHONPATH=/app
PYTHONUNBUFFERED=1

# Node.js
NODE_ENV=production
PORT=3000
```

### Volume Mounts

The following directories are mounted as volumes:

-   `./assets` → `/app/assets`
-   `./videos` → `/app/videos`
-   `./screenshots` → `/app/screenshots`
-   `./clips` → `/app/clips`
-   `./covers` → `/app/covers`
-   `./test_output` → `/app/test_output`

## 🐛 Troubleshooting

### Common Issues

**Port 3000 already in use:**

```bash
# Stop existing services
./docker-scripts.sh stop

# Or kill the process using port 3000
lsof -ti:3000 | xargs kill -9  # macOS/Linux
netstat -ano | findstr :3000   # Windows
```

**Permission issues with volumes:**

```bash
# Fix permissions (Linux/macOS)
sudo chown -R $USER:$USER ./assets ./videos ./screenshots
```

**Container build fails:**

```bash
# Clean build cache
docker system prune -a
./docker-scripts.sh build
```

**Python dependencies issues:**

```bash
# Rebuild backend container
docker-compose build --no-cache streamgank-backend
```

### Debugging

**View container logs:**

```bash
./docker-scripts.sh logs streamgank-backend
./docker-scripts.sh logs streamgank-gui
./docker-scripts.sh logs redis
```

**Access container shell:**

```bash
# Backend container
docker-compose exec streamgank-backend bash

# GUI container
docker-compose exec streamgank-gui sh
```

**Check container status:**

```bash
docker-compose ps
```

## 📊 Monitoring

### Health Checks

All services include health checks:

-   **Backend**: Python import test
-   **GUI**: HTTP health endpoint
-   **Redis**: Redis ping command

### Resource Usage

Monitor resource usage:

```bash
# Container stats
docker stats

# Disk usage
docker system df
```

## 🔄 Updates

### Updating the Application

```bash
# Pull latest changes
git pull

# Rebuild and restart
./docker-scripts.sh stop
./docker-scripts.sh build
./docker-scripts.sh start
```

### Updating Dependencies

```bash
# Rebuild containers with updated dependencies
docker-compose build --no-cache
```

## 🧹 Cleanup

### Remove All Data

```bash
# This will remove all containers, networks, and volumes
./docker-scripts.sh cleanup
```

### Selective Cleanup

```bash
# Remove only containers
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Remove unused Docker resources
docker system prune -f
```

## 📝 Production Deployment

For production deployment:

1. Use `docker-compose.yml` (not the dev override)
2. Set `NODE_ENV=production`
3. Use proper secrets management for API keys
4. Set up reverse proxy (nginx) for SSL termination
5. Configure log rotation
6. Set up monitoring and alerting

Example production command:

```bash
docker-compose -f docker-compose.yml up -d
```

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. View container logs for error details
3. Ensure all required environment variables are set
4. Verify Docker and Docker Compose versions
5. Check available system resources (RAM, disk space)
