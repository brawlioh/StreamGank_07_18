#!/bin/bash
# StreamGank Quick Restart - NO REBUILD
# Use this for simple restarts without creating build cache

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Quick restart without rebuilding
quick_restart() {
    print_status "🔄 Quick Restart (No Rebuild) - Saves disk space!"
    print_status "This will:"
    echo "  1. Stop containers"
    echo "  2. Start containers (using existing images)"
    echo "  ⚡ NO BUILD = NO CACHE BUILDUP!"
    echo ""
    
    # Step 1: Stop
    print_status "Step 1/2: Stopping containers..."
    docker-compose -f docker-compose.vm-optimized.yml down
    print_success "✅ Containers stopped"
    
    # Step 2: Start (no build!)
    print_status "Step 2/2: Starting containers with existing images..."
    docker-compose -f docker-compose.vm-optimized.yml up -d
    print_success "✅ Containers started"
    
    # Show status
    print_status "Checking container status..."
    docker-compose -f docker-compose.vm-optimized.yml ps
    
    print_success "🎉 Quick Restart completed!"
    print_status "GUI available at: http://localhost:3000"
    print_status "💾 No build cache created - disk space saved!"
}

# Run the quick restart
quick_restart
