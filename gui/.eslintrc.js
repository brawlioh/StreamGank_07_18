/**
 * @fileoverview ESLint configuration for StreamGank Video Generator.
 * Ensures professional code quality and consistency.
 */
module.exports = {
    env: {
        browser: true,
        es2021: true,
        node: true,
        jest: true
    },
    extends: ['eslint:recommended', 'prettier'],
    plugins: ['prettier'],
    parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module'
    },
    rules: {
        // Code quality rules
        'no-console': 'off', // Allow console for this project
        'no-debugger': 'warn',
        'no-unused-vars': 'off', // Disabled - no warnings for unused variables
        'no-var': 'error',
        'prefer-const': 'error',
        'prefer-arrow-callback': 'error',

        // ES6+ rules - made less strict
        'arrow-spacing': 'warn',
        'object-shorthand': 'warn',

        // Best practices
        eqeqeq: ['warn', 'always'],
        curly: 'off', // Allow single-line if statements without braces
        'no-implicit-globals': 'warn',
        'no-loop-func': 'warn',
        'no-param-reassign': 'warn',
        'no-return-assign': 'warn',
        'no-throw-literal': 'warn',
        'no-unmodified-loop-condition': 'warn',
        'no-useless-call': 'warn',
        'no-useless-concat': 'warn',
        'prefer-promise-reject-errors': 'warn',
        'require-await': 'warn',

        // Style rules (handled by Prettier) - make less strict
        'prettier/prettier': [
            'warn',
            {},
            {
                usePrettierrc: true,
                fileInfoOptions: {
                    withNodeModules: false
                }
            }
        ],

        // Import/Export rules
        'no-duplicate-imports': 'error',

        // Class rules
        'class-methods-use-this': 'off', // Allow methods that don't use 'this'
        'no-useless-constructor': 'warn',

        // Function rules
        'func-names': 'off',
        'prefer-rest-params': 'warn',
        'prefer-spread': 'warn'

        // Error handling
        // 'no-empty-catch': 'error'  // Temporarily disabled due to rule definition issues
    },

    overrides: [
        // Browser-specific files
        {
            files: ['src/**/*.js'],
            env: {
                browser: true,
                node: false
            },
            globals: {
                // Browser globals
                EventSource: 'readonly',
                AbortController: 'readonly',
                fetch: 'readonly'
            }
        },

        // Node.js server files
        {
            files: ['server.js', 'queue-manager.js', 'webhook-manager.js'],
            env: {
                node: true,
                browser: false
            }
        },

        // Configuration files
        {
            files: ['webpack.config.js', '.eslintrc.js'],
            env: {
                node: true,
                browser: false
            },
            rules: {
                'no-console': 'off'
            }
        }
    ],

    // Global variables
    globals: {
        process: 'readonly',
        global: 'readonly',
        __dirname: 'readonly',
        __filename: 'readonly',
        module: 'readonly',
        require: 'readonly',
        exports: 'readonly',
        Buffer: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly'
    },

    // Ignore patterns
    ignorePatterns: ['dist/', 'node_modules/', 'coverage/', '*.min.js', 'legacy/', 'temp/', '.git/']
};
