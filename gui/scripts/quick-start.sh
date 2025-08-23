#!/bin/bash

# StreamGank GUI - Quick Start Script
# Sets up development environment and starts both backend and frontend

echo "🚀 StreamGank GUI - Quick Start"
echo "================================"

# Check if we're in the gui directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Please run this script from the gui/ directory"
    echo "   cd gui && bash scripts/quick-start.sh"
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node --version 2>/dev/null | cut -d 'v' -f 2)
if [ $? -ne 0 ]; then
    echo "❌ Error: Node.js is not installed"
    echo "   Please install Node.js 16+ from https://nodejs.org"
    exit 1
fi

NODE_MAJOR=$(echo $NODE_VERSION | cut -d '.' -f 1)
if [ $NODE_MAJOR -lt 16 ]; then
    echo "❌ Error: Node.js version $NODE_VERSION is too old"
    echo "   Please upgrade to Node.js 16+ from https://nodejs.org"
    exit 1
fi

echo "✅ Node.js version: v$NODE_VERSION"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies already installed"
fi

# Create dist directory if it doesn't exist
if [ ! -d "dist" ]; then
    echo "📁 Creating dist directory..."
    mkdir dist
fi

# Build development version
echo "🔨 Building development version..."
npm run build:dev
if [ $? -ne 0 ]; then
    echo "❌ Failed to build development version"
    exit 1
fi
echo "✅ Development build complete"

echo ""
echo "🎉 Setup complete! Now starting development servers..."
echo ""
echo "📚 Available development modes:"
echo ""
echo "1. 🔧 Full development (recommended):"
echo "   Terminal 1: npm run dev          # Backend server (port 3000)"  
echo "   Terminal 2: npm run dev:client   # Frontend dev server (port 3001)"
echo ""
echo "2. 📦 Production build testing:"
echo "   npm run production               # Build + start production server"
echo ""
echo "3. 🔍 Development tools:"
echo "   npm run watch                    # Watch for changes"
echo "   npm run lint                     # Check code quality"
echo "   npm run analyze                  # Analyze bundle sizes"
echo ""

# Ask user which mode to start
read -p "Which mode would you like to start? (1/2/3 or 'skip'): " choice

case $choice in
    1)
        echo "🚀 Starting full development mode..."
        echo "   Backend will start on port 3000"
        echo "   Frontend will start on port 3001"
        echo ""
        echo "💡 Tip: Open http://localhost:3001 in your browser"
        echo ""
        
        # Start backend in background
        echo "🔧 Starting backend server..."
        npm run dev &
        BACKEND_PID=$!
        
        # Wait a moment for backend to start
        sleep 3
        
        # Start frontend dev server
        echo "🎨 Starting frontend development server..."
        npm run dev:client
        ;;
    2)
        echo "🏭 Starting production mode..."
        npm run production
        ;;
    3)
        echo "🔍 Starting watch mode..."
        npm run watch
        ;;
    *)
        echo "⏭️ Skipping automatic startup"
        echo ""
        echo "🎯 Manual commands:"
        echo "   npm run dev                 # Backend server"
        echo "   npm run dev:client          # Frontend dev server"
        echo "   npm run production          # Production mode"
        ;;
esac

echo ""
echo "✨ StreamGank GUI is ready for development!"
echo "📖 See PRODUCTION_JAVASCRIPT_ARCHITECTURE.md for detailed documentation"
