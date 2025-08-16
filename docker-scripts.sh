#!/bin/bash
# StreamGank Docker Management Scripts

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Check if Docker and Docker Compose are installed
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Dependencies check passed!"
}

# Setup environment file
setup_env() {
    print_status "Setting up environment file..."
    
    if [ ! -f .env ]; then
        if [ -f docker.env.example ]; then
            cp docker.env.example .env
            print_warning "Created .env file from docker.env.example. Please edit it with your actual values."
        else
            print_error "docker.env.example not found. Cannot create .env file."
            exit 1
        fi
    else
        print_success ".env file already exists."
    fi
}

# Build all services
build_services() {
    print_status "Building Docker services..."
    docker-compose build --no-cache
    print_success "Services built successfully!"
}

# Start services in production mode
start_production() {
    print_status "Starting StreamGank in production mode..."
    docker-compose up -d
    print_success "StreamGank is running in production mode!"
    print_status "GUI available at: http://localhost:3000"
}

# Start services in development mode
start_development() {
    print_status "Starting StreamGank in development mode..."
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
    print_success "StreamGank is running in development mode!"
    print_status "GUI available at: http://localhost:3000"
}

# Stop all services
stop_services() {
    print_status "Stopping StreamGank services..."
    docker-compose down
    print_success "Services stopped successfully!"
}

# View logs
view_logs() {
    local service=${1:-""}
    if [ -z "$service" ]; then
        print_status "Showing logs for all services..."
        docker-compose logs -f
    else
        print_status "Showing logs for service: $service"
        docker-compose logs -f "$service"
    fi
}

# Clean up (remove containers, networks, volumes)
cleanup() {
    print_warning "This will remove all containers, networks, and volumes. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_status "Cleaning up Docker resources..."
        docker-compose down -v --remove-orphans
        docker system prune -f
        print_success "Cleanup completed!"
    else
        print_status "Cleanup cancelled."
    fi
}

# Run Python CLI command in container
run_cli() {
    if [ $# -eq 0 ]; then
        print_error "No command provided. Usage: $0 cli <python_command>"
        exit 1
    fi
    
    print_status "Running CLI command in container..."
    docker-compose exec streamgank-backend python "$@"
}

# Show help
show_help() {
    echo "StreamGank Docker Management Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  setup         - Check dependencies and setup environment"
    echo "  build         - Build all Docker services"
    echo "  start         - Start services in production mode"
    echo "  dev           - Start services in development mode"
    echo "  stop          - Stop all services"
    echo "  logs [service]- View logs (optionally for specific service)"
    echo "  cli <command> - Run Python CLI command in container"
    echo "  cleanup       - Remove all containers, networks, and volumes"
    echo "  help          - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup"
    echo "  $0 start"
    echo "  $0 logs streamgank-gui"
    echo "  $0 cli main.py --country US --platform Netflix --genre Horror --content-type Film"
    echo ""
}

# Main script logic
case "${1:-help}" in
    setup)
        check_dependencies
        setup_env
        ;;
    build)
        check_dependencies
        build_services
        ;;
    start)
        check_dependencies
        setup_env
        start_production
        ;;
    dev)
        check_dependencies
        setup_env
        start_development
        ;;
    stop)
        stop_services
        ;;
    logs)
        view_logs "$2"
        ;;
    cli)
        shift
        run_cli "$@"
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
