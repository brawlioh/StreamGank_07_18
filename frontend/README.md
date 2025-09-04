# StreamGank Frontend - Vite + React + Tailwind v4

This is the Vite + React + Tailwind v4 migration of the StreamGank Video Generator GUI, maintaining exact functionality and appearance.

## 🚀 Quick Start

### Prerequisites

-   Node.js 18+
-   npm 9+
-   StreamGank backend server running on port 3000

### Installation

1. **Install dependencies:**

    ```bash
    cd frontend
    npm install
    ```

2. **Set up environment variables:**

    ```bash
    # Create environment file
    echo "VITE_BACKEND_URL=http://localhost:3000" > .env.local
    ```

3. **Start development server:**

    ```bash
    npm run dev
    ```

    The frontend will be available at: http://localhost:3000

4. **Build for production:**
    ```bash
    npm run build
    npm run preview
    ```

## 📋 Features Migrated

### ✅ Complete Feature Parity

-   **Dashboard Page** - Video generation form with real-time preview
-   **Queue Management** - Job monitoring and queue controls
-   **Job Detail Pages** - Individual job progress with real-time updates
-   **Real-time Updates** - Server-Sent Events with polling fallback
-   **Professional Navigation** - Responsive navigation with status indicators
-   **API Integration** - All 40+ endpoints from original GUI
-   **Webhook Support** - Complete webhook system integration

### 🎨 Visual Design

-   **Exact UI Match** - Pixel-perfect recreation of original design
-   **Dark Theme** - Professional dark interface with StreamGank branding
-   **Responsive Design** - Mobile-friendly responsive layout
-   **Animations** - Smooth transitions and loading states
-   **Status Indicators** - Real-time connection and queue status

### 🔧 Technical Architecture

-   **Vite** - Ultra-fast build tool with HMR
-   **React 18** - Modern React with hooks and TypeScript
-   **Tailwind v4** - Latest utility-first CSS framework
-   **React Router** - Client-side routing
-   **TypeScript** - Type-safe development with full API typing
-   **Professional Services** - APIService, RealtimeService with caching
-   **Error Handling** - Comprehensive error handling and retry logic

## 🌐 API Integration

The frontend connects to all backend endpoints documented in `StreamGank_API_and_Webhooks_Documentation.md`:

### Core Endpoints Used:

-   **Video Generation:** `/api/generate`
-   **Job Management:** `/api/job/:jobId/*`
-   **Queue Operations:** `/api/queue/*`
-   **Real-time Updates:** `/api/queue/status/stream`
-   **Movie Preview:** `/api/movies/preview`
-   **Platform/Genre Data:** `/api/platforms/:country`, `/api/genres/:country`
-   **Webhook System:** `/api/webhooks/*`

### Real-time Features:

-   **Server-Sent Events** for instant updates
-   **Job-specific SSE streams** for detailed monitoring
-   **Adaptive polling fallback** when SSE unavailable
-   **Professional connection management** with auto-reconnection

## 📁 Project Structure

```
frontend/
├── src/
│   ├── pages/                  # React Router pages
│   │   ├── Dashboard.tsx      # Dashboard page
│   │   ├── Queue.tsx          # Queue management page
│   │   └── JobDetail.tsx      # Dynamic job detail pages
│   ├── components/            # Reusable React components
│   │   ├── Navigation.tsx     # Main navigation header
│   │   ├── FormManager.tsx    # Video generation form
│   │   ├── StatusMessages.tsx # Real-time status messages
│   │   └── MoviePreview.tsx   # Movie preview cards
│   ├── services/              # API and real-time services
│   │   ├── APIService.ts      # HTTP client with caching
│   │   └── RealtimeService.ts # SSE and polling service
│   ├── App.tsx                # Main app component with routing
│   ├── main.tsx               # Vite entry point
│   └── index.css              # Global styles with Tailwind
├── package.json               # Dependencies and scripts
├── vite.config.ts             # Vite configuration with Tailwind
├── tailwind.config.js         # Tailwind v4 configuration
├── tsconfig.json              # TypeScript configuration
└── README.md                  # This file
```

## 🔄 Migration Advantages

### Why Vite + React + Tailwind v4:

1. **Performance** - Vite's ultra-fast HMR and build times
2. **Modern Stack** - Latest React 18 with concurrent features
3. **Tailwind v4** - Latest CSS framework with improved performance
4. **Developer Experience** - Instant updates, better debugging
5. **Build Optimization** - Smaller bundles, better caching
6. **Type Safety** - Full TypeScript integration

### Technical Improvements:

-   **Lightning Fast Development** - Vite HMR vs traditional bundlers
-   **Modern React Patterns** - Hooks, Context, Suspense ready
-   **CSS Performance** - Tailwind v4 with improved purging
-   **Bundle Optimization** - Automatic code splitting
-   **Hot Module Replacement** - Instant updates without page refresh

## 🚦 Development

### Available Scripts:

-   `npm run dev` - Start development server (port 3000)
-   `npm run build` - Build for production
-   `npm run preview` - Preview production build
-   `npm run lint` - Run ESLint

### Environment Configuration:

-   **Backend URL:** Configure via `VITE_BACKEND_URL` environment variable
-   **API Proxy:** Automatic proxy to backend server on port 3000
-   **Hot Reload:** Instant updates during development

### Development Features:

-   **Fast Refresh** - Preserve component state during edits
-   **Error Overlay** - Clear error messages in development
-   **Source Maps** - Debug original TypeScript code
-   **Tree Shaking** - Eliminate dead code automatically

## 🔗 Backend Integration

The frontend requires the StreamGank backend server to be running on port 3000. All API calls are automatically proxied through Vite configuration.

**Backend Dependencies:**

-   StreamGank backend server (port 3000)
-   Redis queue system
-   Python video generation scripts
-   Webhook endpoints configured

## 📊 Real-time Features

### Connection Management:

-   **Primary:** Server-Sent Events (SSE)
-   **Fallback:** Adaptive polling with smart intervals
-   **Recovery:** Automatic reconnection on network changes
-   **Performance:** Page visibility API for reduced load

### Update Types:

-   **Queue Statistics** - Live job counts and worker status
-   **Job Progress** - Step-by-step workflow updates
-   **Video Status** - Creatomate rendering progress
-   **Error Notifications** - Instant failure alerts

## 🎯 Exact Feature Match

This Vite migration provides:

-   **100% Visual Parity** - Identical appearance to original GUI
-   **100% Functional Parity** - All features work exactly the same
-   **Improved Performance** - Faster loading and updates
-   **Better Developer Experience** - Modern tooling and debugging
-   **Future-Proof Architecture** - Ready for React 19 and beyond

The migration maintains every detail of the original interface while providing a modern, maintainable, and high-performance foundation.
