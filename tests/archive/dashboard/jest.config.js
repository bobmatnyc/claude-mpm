/**
 * Jest configuration for Claude MPM dashboard tests
 */

module.exports = {
  // Test environment
  testEnvironment: 'jsdom',

  // Setup files
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],

  // Module paths
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/../../src/claude_mpm/dashboard/static/js/$1'
  },

  // Coverage configuration
  collectCoverage: true,
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  collectCoverageFrom: [
    '**/*.js',
    '!**/node_modules/**',
    '!**/coverage/**',
    '!jest.*.js'
  ],

  // Test patterns
  testMatch: [
    '**/test_*.js',
    '**/*.test.js',
    '**/*.spec.js'
  ],

  // Transform settings for ES6 modules
  transform: {
    '^.+\\.js$': ['babel-jest', {
      presets: [
        ['@babel/preset-env', {
          targets: {
            node: 'current'
          }
        }]
      ]
    }]
  },

  // Globals
  globals: {
    'window': {},
    'document': {}
  },

  // Verbose output for debugging
  verbose: true,

  // Test timeout
  testTimeout: 10000
};
