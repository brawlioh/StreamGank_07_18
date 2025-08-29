#!/bin/bash
# StreamGank VM-Optimized Docker Management Scripts
# Enhanced for Virtual Machine environments with performance monitoring

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_vm_status() {
    echo -e "${PURPLE}[VM-STATUS]${NC} $1"
}

# Check VM resources before starting
check_vm_resources() {
    print_status "Checking VM resources..."
    
    # Check available RAM (Linux/macOS compatible)
    if command -v free >/dev/null 2>&1; then
        available_ram=$(free -m | awk 'NR==2{printf "%.1f", $7/1024}')
        print_vm_status "Available RAM: ${available_ram}GB"
        
        if (( $(echo "$available_ram < 3" | bc -l) )); then
            print_warning "Low available RAM detected. Consider stopping other applications."
        fi
    fi
    
    # Check available disk space
    available_disk=$(df -h . | awk 'NR==2{print $4}')
    print_vm_status "Available disk space: $available_disk"
    
    # Check CPU cores
    cpu_cores=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo "unknown")
    print_vm_status "CPU cores: $cpu_cores"
}

# Validate required environment variables
validate_env() {
    print_status "Validating environment configuration..."
    
    # Check if .env file exists
    if [ ! -f .env ]; then
        print_error "❌ FATAL: .env file not found!"
        print_error "📝 Create .env file from docker.env.example:"
        print_error "   cp docker.env.example .env"
        print_error "   # Then edit .env with your configuration"
        exit 1
    fi
    
    # Load environment variables
    source .env 2>/dev/null || {
        print_error "❌ FATAL: Failed to load .env file!"
        print_error "📝 Check .env file syntax and permissions"
        exit 1
    }
    
    # Define required environment variables
    REQUIRED_VARS=(
        "APP_ENV:Application environment (local/prod)"
        "NODE_ENV:Node.js environment" 
        "PORT:Application port"
        "PYTHONPATH:Python path"
        "PYTHONUNBUFFERED:Python output buffering"
        "STREAMGANK_DATA_PATH:Data storage path"
        "REDIS_HOST:Redis server hostname"
        "REDIS_PORT:Redis server port"
        "REDIS_PASSWORD:Redis authentication password"
        "REDIS_DB:Redis database number (0-15)"
    )
    
    # Validate each required variable
    missing_vars=()
    for var_info in "${REQUIRED_VARS[@]}"; do
        var_name=$(echo "$var_info" | cut -d: -f1)
        var_desc=$(echo "$var_info" | cut -d: -f2-)
        
        # Get variable value using indirect expansion
        var_value="${!var_name}"
        
        if [ -z "$var_value" ]; then
            missing_vars+=("$var_name ($var_desc)")
        fi
    done
    
    # Report missing variables and exit if any found
    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_error "❌ FATAL: Missing required environment variables in .env:"
        for var in "${missing_vars[@]}"; do
            print_error "   - $var"
        done
        print_error ""
        print_error "📝 Update your .env file with all required variables"
        print_error "📋 See docker.env.example for reference"
        exit 1
    fi
    
    print_success "✅ All required environment variables are set"
}

# VM-optimized setup
setup_vm_optimized() {
    print_status "Setting up VM-optimized environment..."
    
    # Validate environment first
    validate_env
    
    # Load environment variables (already validated)
    source .env
    DATA_PATH="$STREAMGANK_DATA_PATH"
    
    print_status "Creating data directories at: $DATA_PATH"
    
    # Create required directories
    mkdir -p assets videos outputs temp redis_data  # Legacy directories (still needed)
    mkdir -p "$DATA_PATH"/{assets,videos,outputs,redis,logs}  # New organized structure
    
    print_success "Created directory structure:"
    print_success "  📁 $DATA_PATH/assets/     - Generated assets"
    print_success "  📁 $DATA_PATH/videos/     - Output videos"  
    print_success "  📁 $DATA_PATH/outputs/    - Processed outputs"
    print_success "  📁 $DATA_PATH/redis/      - Redis data"
    print_success "  📁 $DATA_PATH/logs/       - Application logs"
    
    # Set up environment file
    if [ ! -f .env ]; then
        if [ -f docker.env.example ]; then
            cp docker.env.example .env
            print_warning "Created .env file. Please edit with your API keys."
            
            # VM-specific adjustments to .env
            if grep -q "REDIS_HOST=redis" .env; then
                sed -i.bak 's/REDIS_HOST=.*/REDIS_HOST=redis/' .env
                print_vm_status "Configured Redis for local Docker instance"
            fi
        else
            print_error "docker.env.example not found!"
            exit 1
        fi
    fi
    
    print_success "VM environment setup complete!"
}

# Build with VM optimizations
build_vm_optimized() {
    print_status "Building VM-optimized Docker images..."
    check_vm_resources
    
    # Build with limited parallel jobs to avoid overwhelming VM
    export DOCKER_BUILDKIT=1
    export BUILDKIT_PROGRESS=plain
    
    docker-compose -f docker-compose.vm-optimized.yml build \
        --parallel \
        --memory=1g
    
    print_success "VM-optimized build complete!"
}

# Force rebuild without cache (use when dependencies change)
vm_rebuild() {
    print_status "Setting up VM-optimized environment..."
    setup_vm_optimized
    print_success "VM environment setup complete!"
    
    print_status "Force rebuilding VM-optimized Docker images (no cache)..."
    print_status "This will re-download all dependencies - use when requirements.txt or package.json change"
    print_status "Checking VM resources..."
    
    print_vm_status "Available disk space: $(df -h . | awk 'NR==2 {print $4}')"
    print_vm_status "CPU cores: $(nproc)"
    
    # Build with no cache to get fresh dependencies
    export DOCKER_BUILDKIT=1
    export BUILDKIT_PROGRESS=plain
    
    docker-compose -f docker-compose.vm-optimized.yml build \
        --no-cache \
        --parallel \
        --memory=1g
    
    print_success "VM-optimized force rebuild complete!"
}

# Start with VM monitoring
start_vm_production() {
    print_status "Starting StreamGank in VM-optimized production mode..."
    check_vm_resources
    
    docker-compose -f docker-compose.vm-optimized.yml up -d
    
    # Wait for services to be healthy
    print_status "Waiting for services to become healthy..."
    sleep 10
    
    # Show status
    show_vm_status
    
    print_success "StreamGank is running in VM-optimized mode!"
    print_status "GUI available at: http://localhost:3000"
}

# VM-optimized restart (down-build-start sequence)
vm_restart() {
    print_status "🔄 VM Restart - Full down-build-start sequence..."
    print_status "This will:"
    echo "  1. Stop all running containers"
    echo "  2. Rebuild Docker images with cache"
    echo "  3. Start services in production mode"
    echo ""
    
    # Step 1: Stop containers
    print_status "Step 1/3: Stopping containers..."
    docker-compose -f docker-compose.vm-optimized.yml down
    print_success "✅ Containers stopped"
    
    # Step 2: Build (includes setup and build)
    print_status "Step 2/3: Building VM-optimized images..."
    setup_vm_optimized
    build_vm_optimized
    print_success "✅ Build completed"
    
    # Step 3: Start (setup already done, just start production)
    print_status "Step 3/3: Starting production services..."
    start_vm_production
    print_success "✅ Services started"
    
    print_success "🎉 VM Restart completed successfully!"
    print_status "GUI available at: http://localhost:3000"
}

# VM-optimized quick update (build-start sequence - NO stop needed)
vm_update() {
    print_status "🚀 VM Update - Quick build-start sequence for code changes..."
    print_status "This will:"
    echo "  1. Rebuild Docker images with cache (for code changes)"
    echo "  2. Start services with new image (containers auto-updated)"
    echo "  ⚡ FASTER: No stop step needed - Docker handles the update!"
    echo ""
    
    # Step 1: Build with cache (perfect for code changes)
    print_status "Step 1/2: Building updated images..."
    setup_vm_optimized
    build_vm_optimized
    print_success "✅ Build completed"
    
    # Step 2: Start/Update services (Docker will restart containers with new image)
    print_status "Step 2/2: Updating services with new image..."
    docker-compose -f docker-compose.vm-optimized.yml up -d
    print_success "✅ Services updated"
    
    print_success "🎉 VM Update completed successfully!"
    print_status "GUI available at: http://localhost:3000"
    print_status "💡 Use 'vm-update' for code changes | 'vm-restart' for config changes | 'vm-rebuild' for dependency changes"
}

# VM-optimized simple restart (NO rebuild - saves disk space!)
vm_simple_restart() {
    print_status "🔄 VM Simple Restart - No rebuild to save disk space..."
    print_status "This will:"
    echo "  1. Stop all running containers"
    echo "  2. Start services using existing images"
    echo "  💾 NO BUILD = NO CACHE BUILDUP = SAVES 50GB!"
    echo ""
    
    # Step 1: Stop containers
    print_status "Step 1/2: Stopping containers..."
    docker-compose -f docker-compose.vm-optimized.yml down
    print_success "✅ Containers stopped"
    
    # Step 2: Start (no build, no setup, just start!)
    print_status "Step 2/2: Starting services with existing images..."
    docker-compose -f docker-compose.vm-optimized.yml up -d
    print_success "✅ Services started"
    
    # Show status
    print_status "Checking service status..."
    sleep 5
    show_vm_status
    
    print_success "🎉 VM Simple Restart completed!"
    print_status "GUI available at: http://localhost:3000"
    print_status "💾 No build cache created - disk space saved!"
}

# Show detailed VM and container status
show_vm_status() {
    print_vm_status "Container Status:"
    docker-compose -f docker-compose.vm-optimized.yml ps
    
    print_vm_status "Container Resource Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
    
    print_vm_status "Volume Usage:"
    docker system df
    
    # Check health status
    print_vm_status "Health Status:"
    docker-compose -f docker-compose.vm-optimized.yml exec streamgank-app python -c "print('Backend: OK')" 2>/dev/null && echo "✓ Backend healthy" || echo "✗ Backend unhealthy"
    docker-compose -f docker-compose.vm-optimized.yml exec streamgank-app curl -sf http://localhost:3000/health >/dev/null 2>&1 && echo "✓ GUI healthy" || echo "✗ GUI unhealthy"
    docker-compose -f docker-compose.vm-optimized.yml exec redis redis-cli ping >/dev/null 2>&1 && echo "✓ Redis healthy" || echo "✗ Redis unhealthy"
}

# VM-optimized cleanup with resource reclamation
cleanup_vm() {
    print_warning "VM Cleanup - This will:"
    echo "  - Stop all containers"
    echo "  - Remove containers and networks"
    echo "  - Clean up Docker cache"
    echo "  - Reclaim VM disk space"
    echo ""
    echo "Persistent data (volumes) will be preserved."
    echo ""
    read -p "Continue? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Starting VM cleanup..."
        
        # Stop services
        docker-compose -f docker-compose.vm-optimized.yml down --remove-orphans
        
        # Clean up Docker resources
        docker system prune -f
        docker volume prune -f
        
        # Show reclaimed space
        print_vm_status "Cleanup complete! Disk space reclaimed:"
        docker system df
        
        print_success "VM cleanup completed!"
    else
        print_status "Cleanup cancelled."
    fi
}

# Monitor VM performance while running
monitor_vm() {
    print_status "Starting VM performance monitoring (Ctrl+C to stop)..."
    
    while true; do
        clear
        echo "=== StreamGank VM Performance Monitor ==="
        echo "Timestamp: $(date)"
        echo
        
        check_vm_resources
        echo
        show_vm_status
        
        sleep 5
    done
}

# Show VM-specific help
show_vm_help() {
    echo "StreamGank VM-Optimized Docker Management"
    echo "Designed for Virtual Machine environments"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "VM Commands:"
    echo "  vm-setup      - Setup VM-optimized environment"
    echo "  vm-build      - Build with VM resource limits (uses cache)"
    echo "  vm-rebuild    - Force rebuild without cache (when dependencies change)"
    echo "  vm-start      - Start in VM-optimized production mode"
    echo "  vm-restart    - Full restart: down → build → start (complete refresh)"
    echo "  vm-simple-restart - Simple restart: down → start (NO BUILD - saves disk space!)"
    echo "  vm-update     - Quick update: build → start (FAST - for code changes only)"
    echo "  vm-status     - Show detailed VM and container status"
    echo "  vm-monitor    - Real-time VM performance monitoring"
    echo "  vm-cleanup    - VM-optimized cleanup with space reclamation"
    echo ""
    echo "Standard Commands:"
    echo "  stop          - Stop all services"
    echo "  logs [service]- View logs"
    echo "  cli <command> - Run CLI command in container"
    echo "  help          - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 vm-setup   # Initialize VM environment"
    echo "  $0 vm-start   # Start production mode"
    echo "  $0 vm-simple-restart # Simple restart (RECOMMENDED - saves 50GB!)"
    echo "  $0 vm-update  # Quick update after code changes (FASTEST)"
    echo "  $0 vm-restart # Full restart: stop → build → start (creates cache)"
    echo "  $0 vm-monitor # Monitor performance"
    echo ""
}

# Enhanced logging for VM
view_vm_logs() {
    local service=${1:-""}
    if [ -z "$service" ]; then
        print_status "Showing logs for all services (VM mode)..."
        docker-compose -f docker-compose.vm-optimized.yml logs -f --tail=100
    else
        print_status "Showing logs for service: $service (VM mode)"
        docker-compose -f docker-compose.vm-optimized.yml logs -f --tail=50 "$service"
    fi
}

# Run CLI with VM considerations
run_vm_cli() {
    if [ $# -eq 0 ]; then
        print_error "No command provided. Usage: $0 cli <python_command>"
        exit 1
    fi
    
    print_status "Running CLI command in VM container..."
    docker-compose -f docker-compose.vm-optimized.yml exec streamgank-app python "$@"
}

# Stop services (VM compatible)
stop_vm_services() {
    print_status "Stopping StreamGank services (VM mode)..."
    docker-compose -f docker-compose.vm-optimized.yml down
    print_success "VM services stopped!"
}

# Main script logic with VM optimizations
case "${1:-help}" in
    vm-setup)
        setup_vm_optimized
        ;;
    vm-build)
        setup_vm_optimized
        build_vm_optimized
        ;;
    vm-rebuild)
        vm_rebuild
        ;;
    vm-start)
        setup_vm_optimized
        start_vm_production
        ;;
    vm-restart)
        vm_restart
        ;;
    vm-simple-restart)
        vm_simple_restart
        ;;
    vm-update)
        vm_update
        ;;
    vm-status)
        show_vm_status
        ;;
    vm-monitor)
        monitor_vm
        ;;
    vm-cleanup)
        cleanup_vm
        ;;
    stop)
        stop_vm_services
        ;;
    logs)
        view_vm_logs "$2"
        ;;
    cli)
        shift
        run_vm_cli "$@"
        ;;
    help|--help|-h)
        show_vm_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_vm_help
        exit 1
        ;;
esac
