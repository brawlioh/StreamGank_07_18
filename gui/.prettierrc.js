/**
 * Prettier Configuration for StreamGank Video Generator
 * Professional code formatting standards
 */
module.exports = {
    // Basic formatting - more flexible
    printWidth: 120,
    tabWidth: 4,
    useTabs: false,
    semi: true,
    singleQuote: true,
    quoteProps: 'as-needed',

    // JavaScript specific
    jsxSingleQuote: true,
    trailingComma: 'none',
    bracketSpacing: true,
    bracketSameLine: false,
    arrowParens: 'always',

    // Line endings - auto detect
    endOfLine: 'auto',

    // Prose formatting
    proseWrap: 'preserve',

    // HTML/XML formatting
    htmlWhitespaceSensitivity: 'css',

    // Overrides for specific file types
    overrides: [
        // JavaScript/TypeScript files - more flexible
        {
            files: ['*.js', '*.mjs'],
            options: {
                parser: 'babel',
                printWidth: 120,
                tabWidth: 4,
                arrowParens: 'always',
                trailingComma: 'none'
            }
        },

        // JSON files
        {
            files: ['*.json', '.eslintrc', '.prettierrc'],
            options: {
                parser: 'json',
                printWidth: 80,
                tabWidth: 2
            }
        },

        // CSS files
        {
            files: ['*.css', '*.scss', '*.less'],
            options: {
                parser: 'css',
                printWidth: 120,
                singleQuote: false
            }
        },

        // HTML files
        {
            files: ['*.html'],
            options: {
                parser: 'html',
                printWidth: 120,
                tabWidth: 2,
                htmlWhitespaceSensitivity: 'ignore'
            }
        },

        // Markdown files
        {
            files: ['*.md'],
            options: {
                parser: 'markdown',
                printWidth: 80,
                proseWrap: 'always',
                tabWidth: 2
            }
        },

        // Configuration files
        {
            files: ['webpack.config.js', '.eslintrc.js', '.prettierrc.js', 'babel.config.js'],
            options: {
                parser: 'babel',
                printWidth: 100,
                tabWidth: 4
            }
        }
    ]
};
