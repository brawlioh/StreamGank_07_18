/**
 * Simple Reliable Router - No Dependencies, Just Works
 * Handles SPA routing, browser history, page reloads, back/forward
 */

class SimpleRouter {
    constructor() {
        this.routes = new Map();
        this.currentRoute = null;
        this.isStarted = false;

        console.log('🔧 SimpleRouter created');
    }

    /**
     * Add a route
     */
    addRoute(path, handler) {
        console.log(`📝 Adding route: ${path}`);

        // Convert :param to regex
        const paramNames = [];
        const regexPath = path.replace(/:([^/]+)/g, (match, paramName) => {
            paramNames.push(paramName);
            return '([^/]+)';
        });

        const regex = new RegExp(`^${regexPath}$`);

        this.routes.set(path, {
            handler,
            regex,
            paramNames,
            originalPath: path
        });

        console.log(`✅ Route added: ${path}`);
    }

    /**
     * Navigate to a path
     */
    navigate(path) {
        console.log(`🚀 Navigate to: ${path}`);

        // Update browser URL
        window.history.pushState({}, '', path);

        // Handle the route
        this.handleRoute(path);
    }

    /**
     * Handle current route
     */
    handleRoute(path = window.location.pathname) {
        console.log(`🔍 Handling route: ${path}`);

        // Try to match route
        for (const [routePath, routeData] of this.routes) {
            const match = path.match(routeData.regex);

            if (match) {
                console.log(`✅ Route matched: ${routePath}`);

                // Extract parameters
                const params = {};
                routeData.paramNames.forEach((name, index) => {
                    params[name] = match[index + 1];
                });

                console.log(`📋 Route params:`, params);

                // Call handler
                try {
                    routeData.handler(params);
                    this.currentRoute = routePath;
                    return true;
                } catch (error) {
                    console.error(`❌ Route handler error:`, error);
                }
            }
        }

        // No route matched
        console.warn(`❌ No route matched for: ${path}`);
        this.handle404(path);
        return false;
    }

    /**
     * Handle 404
     */
    handle404(path) {
        console.log(`🔍 404 for path: ${path}`);

        // Redirect to dashboard for unknown routes (avoid infinite loops)
        if (path !== '/dashboard' && path !== '/' && !path.startsWith('/dashboard')) {
            console.log(`🏠 Redirecting to dashboard from: ${path}`);
            this.navigate('/dashboard');
        } else {
            console.warn(`❌ Route not found and cannot redirect: ${path}`);
        }
    }

    /**
     * Start the router
     */
    start() {
        if (this.isStarted) {
            console.warn('⚠️ Router already started');
            return;
        }

        console.log('🎬 Starting router...');

        // Handle browser back/forward
        window.addEventListener('popstate', () => {
            console.log('🔄 Popstate event');
            this.handleRoute();
        });

        // Handle current route
        this.handleRoute();

        this.isStarted = true;
        console.log('✅ Router started');
    }
}

// Export singleton
export default new SimpleRouter();
