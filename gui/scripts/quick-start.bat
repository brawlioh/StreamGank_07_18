@echo off
REM StreamGank GUI - Quick Start Script for Windows
REM Sets up development environment and starts both backend and frontend

echo 🚀 StreamGank GUI - Quick Start
echo ================================

REM Check if we're in the gui directory
if not exist "package.json" (
    echo ❌ Error: Please run this script from the gui\ directory
    echo    cd gui && scripts\quick-start.bat
    pause
    exit /b 1
)

REM Check Node.js installation
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Node.js is not installed
    echo    Please install Node.js 16+ from https://nodejs.org
    pause
    exit /b 1
)

for /f "tokens=1 delims=." %%a in ('node --version') do set NODE_MAJOR=%%a
set NODE_MAJOR=%NODE_MAJOR:v=%
if %NODE_MAJOR% lss 16 (
    echo ❌ Error: Node.js version is too old
    echo    Please upgrade to Node.js 16+ from https://nodejs.org
    pause
    exit /b 1
)

echo ✅ Node.js version check passed

REM Install dependencies if needed
if not exist "node_modules" (
    echo 📦 Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo ❌ Failed to install dependencies
        pause
        exit /b 1
    )
    echo ✅ Dependencies installed
) else (
    echo ✅ Dependencies already installed
)

REM Create dist directory if it doesn't exist
if not exist "dist" (
    echo 📁 Creating dist directory...
    mkdir dist
)

REM Build development version
echo 🔨 Building development version...
call npm run build:dev
if errorlevel 1 (
    echo ❌ Failed to build development version
    pause
    exit /b 1
)
echo ✅ Development build complete

echo.
echo 🎉 Setup complete! Now choose development mode...
echo.
echo 📚 Available development modes:
echo.
echo 1. 🔧 Full development (recommended):
echo    Terminal 1: npm run dev          # Backend server (port 3000)
echo    Terminal 2: npm run dev:client   # Frontend dev server (port 3001)
echo.
echo 2. 📦 Production build testing:
echo    npm run production               # Build + start production server
echo.
echo 3. 🔍 Development tools:
echo    npm run watch                    # Watch for changes
echo    npm run lint                     # Check code quality
echo    npm run analyze                  # Analyze bundle sizes
echo.

set /p choice="Which mode would you like to start? (1/2/3 or 'skip'): "

if "%choice%"=="1" (
    echo 🚀 Starting full development mode...
    echo    Backend will start on port 3000
    echo    Frontend will start on port 3001
    echo.
    echo 💡 Tip: Open http://localhost:3001 in your browser
    echo.
    echo 🔧 Starting backend server in new window...
    start "StreamGank Backend" cmd /k "npm run dev"
    
    timeout /t 3 /nobreak >nul
    
    echo 🎨 Starting frontend development server...
    call npm run dev:client
) else if "%choice%"=="2" (
    echo 🏭 Starting production mode...
    call npm run production
) else if "%choice%"=="3" (
    echo 🔍 Starting watch mode...
    call npm run watch
) else (
    echo ⏭️ Skipping automatic startup
    echo.
    echo 🎯 Manual commands:
    echo    npm run dev                 # Backend server
    echo    npm run dev:client          # Frontend dev server  
    echo    npm run production          # Production mode
)

echo.
echo ✨ StreamGank GUI is ready for development!
echo 📖 See PRODUCTION_JAVASCRIPT_ARCHITECTURE.md for detailed documentation
echo.
pause
