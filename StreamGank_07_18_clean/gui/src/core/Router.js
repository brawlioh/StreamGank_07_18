/**
 * Router Service - Professional client-side routing
 * Handles URL-based navigation, route parameters, and browser history
 */

export class Router extends EventTarget {
    constructor() {
        super();
        this.routes = new Map();
        this.currentRoute = null;
        this.currentParams = {};
        this.isInitialized = false;
        this.basePath = '';
    }

    /**
     * Initialize the router and setup event listeners
     */
    init() {
        if (this.isInitialized) return;

        // Handle browser back/forward buttons
        window.addEventListener('popstate', (event) => {
            this.handleLocationChange();
        });

        // Handle initial page load
        this.handleLocationChange();

        this.isInitialized = true;
    }

    /**
     * Register a route with its handler
     * @param {string} path - Route pattern (e.g., '/job/:id')
     * @param {Function} handler - Route handler function
     * @param {Object} options - Route options
     */
    addRoute(path, handler, options = {}) {
        const routePattern = this.pathToRegex(path);

        this.routes.set(path, {
            pattern: routePattern,
            handler: handler,
            params: this.extractParams(path),
            title: options.title || 'StreamGank',
            requiresAuth: options.requiresAuth || false,
            metadata: options.metadata || {}
        });

        console.log(`🛤️ Route registered: ${path}`);
    }

    /**
     * Navigate to a specific path
     * @param {string} path - Target path
     * @param {Object} options - Navigation options
     */
    navigate(path, options = {}) {
        const { replace = false, state = null } = options;

        if (replace) {
            window.history.replaceState(state, '', path);
        } else {
            window.history.pushState(state, '', path);
        }

        this.handleLocationChange();
    }

    /**
     * Go back in browser history
     */
    back() {
        window.history.back();
    }

    /**
     * Go forward in browser history
     */
    forward() {
        window.history.forward();
    }

    /**
     * Handle location changes (URL changes)
     */
    handleLocationChange() {
        const path = window.location.pathname;
        const matchedRoute = this.matchRoute(path);

        if (matchedRoute) {
            const { route, params, routeKey } = matchedRoute;

            // Update current state
            const previousRoute = this.currentRoute;
            this.currentRoute = routeKey;
            this.currentParams = params;

            // Update document title
            if (route.title) {
                document.title = route.title;
            }

            // Emit route change event
            this.dispatchEvent(
                new CustomEvent('routeChange', {
                    detail: {
                        path,
                        route: routeKey,
                        params,
                        previousRoute,
                        metadata: route.metadata
                    }
                })
            );

            // Call route handler
            try {
                route.handler(params, path);
                console.log(`🛤️ Navigated to: ${path} (${routeKey})`);
            } catch (error) {
                console.error('🛤️ Route handler error:', error);
                this.dispatchEvent(new CustomEvent('routeError', { detail: { path, error } }));
            }
        } else {
            // No route matched - handle 404
            this.handle404(path);
        }
    }

    /**
     * Match current path against registered routes
     * @param {string} path - Current path
     * @returns {Object|null} Matched route info or null
     */
    matchRoute(path) {
        for (const [routeKey, route] of this.routes.entries()) {
            const match = path.match(route.pattern);

            if (match) {
                const params = {};

                // Extract route parameters
                route.params.forEach((paramName, index) => {
                    params[paramName] = match[index + 1];
                });

                return {
                    route,
                    params,
                    routeKey,
                    match
                };
            }
        }

        return null;
    }

    /**
     * Convert path pattern to regex
     * @param {string} path - Path pattern (e.g., '/job/:id')
     * @returns {RegExp} Route regex
     */
    pathToRegex(path) {
        // Escape special regex characters except for parameter patterns
        const escaped = path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\\:([^/]+)/g, '([^/]+)'); // Convert :param to capture group

        return new RegExp(`^${escaped}$`);
    }

    /**
     * Extract parameter names from path pattern
     * @param {string} path - Path pattern
     * @returns {Array<string>} Parameter names
     */
    extractParams(path) {
        const params = [];
        const matches = path.matchAll(/:([^/]+)/g);

        for (const match of matches) {
            params.push(match[1]);
        }

        return params;
    }

    /**
     * Handle 404 - route not found
     * @param {string} path - Unmatched path
     */
    handle404(path) {
        console.warn(`🛤️ No route found for: ${path}`);

        // Emit 404 event
        this.dispatchEvent(new CustomEvent('notFound', { detail: { path } }));

        // Try to redirect to dashboard or show 404 page
        if (path !== '/' && path !== '/dashboard') {
            this.navigate('/dashboard', { replace: true });
        }
    }

    /**
     * Generate URL for a route with parameters
     * @param {string} routePath - Route pattern
     * @param {Object} params - Route parameters
     * @returns {string} Generated URL
     */
    generateUrl(routePath, params = {}) {
        let url = routePath;

        // Replace parameters in the path
        for (const [key, value] of Object.entries(params)) {
            url = url.replace(`:${key}`, encodeURIComponent(value));
        }

        return url;
    }

    /**
     * Get current route information
     * @returns {Object} Current route info
     */
    getCurrentRoute() {
        return {
            path: window.location.pathname,
            route: this.currentRoute,
            params: this.currentParams,
            hash: window.location.hash,
            search: window.location.search
        };
    }

    /**
     * Check if current route matches pattern
     * @param {string} pattern - Route pattern to check
     * @returns {boolean} Whether current route matches
     */
    isCurrentRoute(pattern) {
        return this.currentRoute === pattern;
    }

    /**
     * Add query parameters to current URL
     * @param {Object} params - Query parameters to add
     */
    updateQuery(params) {
        const url = new URL(window.location);

        for (const [key, value] of Object.entries(params)) {
            if (value === null || value === undefined) {
                url.searchParams.delete(key);
            } else {
                url.searchParams.set(key, value);
            }
        }

        this.navigate(url.pathname + url.search, { replace: true });
    }

    /**
     * Get query parameters from current URL
     * @returns {Object} Query parameters
     */
    getQuery() {
        const params = {};
        const searchParams = new URLSearchParams(window.location.search);

        for (const [key, value] of searchParams.entries()) {
            params[key] = value;
        }

        return params;
    }

    /**
     * Cleanup router resources
     */
    cleanup() {
        window.removeEventListener('popstate', this.handleLocationChange);
        this.routes.clear();
        this.isInitialized = false;
        console.log('🛤️ Router cleaned up');
    }

    /**
     * Emit custom events
     * @param {string} eventName - Event name
     * @param {Object} data - Event data
     */
    emit(eventName, data) {
        const event = new CustomEvent(eventName, { detail: data });
        this.dispatchEvent(event);
    }
}

// Export singleton instance
export default new Router();
