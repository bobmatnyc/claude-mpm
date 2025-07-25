#!/usr/bin/env node

/**
 * Post-install script for claude-mpm npm package
 * 
 * Sets up necessary directories and validates dependencies
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');
const mkdirp = require('mkdirp');

console.log('🚀 Setting up claude-mpm...');

// Create user directories
const userDir = path.join(os.homedir(), '.claude-mpm');
const directories = [
  path.join(userDir, 'agents', 'user-defined'),
  path.join(userDir, 'config'),
  path.join(userDir, 'logs'),
  path.join(userDir, 'templates')
];

directories.forEach(dir => {
  mkdirp.sync(dir);
  console.log(`✅ Created directory: ${dir}`);
});

// Create default config if not exists
const configFile = path.join(userDir, 'config', 'settings.json');
if (!fs.existsSync(configFile)) {
  const defaultConfig = {
    version: '1.0',
    hooks: {
      enabled: true,
      port_range: [8080, 8099]
    },
    logging: {
      level: 'INFO',
      max_size_mb: 100,
      retention_days: 30
    },
    agents: {
      auto_discover: true,
      precedence: ['project', 'user', 'system']
    },
    orchestration: {
      default_mode: 'subprocess',
      enable_todo_hijacking: false
    }
  };
  
  fs.writeFileSync(configFile, JSON.stringify(defaultConfig, null, 2));
  console.log('✅ Created default configuration');
}

// Check for Python
try {
  const pythonVersion = execSync('python3 --version', { encoding: 'utf8' });
  console.log(`✅ Found ${pythonVersion.trim()}`);
} catch (e) {
  console.warn('⚠️  Python 3.8+ is required but not found in PATH');
  console.warn('   Please install Python from https://python.org');
}

// Check for Claude CLI
try {
  execSync('which claude', { encoding: 'utf8' });
  console.log('✅ Found Claude CLI');
} catch (e) {
  console.warn('⚠️  Claude CLI not found in PATH');
  console.warn('   Please install Claude CLI to use claude-mpm');
}

console.log('\n✨ claude-mpm setup complete!');
console.log('\nUsage:');
console.log('  claude-mpm          # Interactive mode');
console.log('  claude-mpm -i "prompt"  # Non-interactive mode');
console.log('  ticket create "Fix bug"  # Create a ticket');
console.log('\nFor more information, visit: https://github.com/claude-mpm/claude-mpm');