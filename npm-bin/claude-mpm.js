#!/usr/bin/env node

/**
 * NPM wrapper for claude-mpm
 * This script checks for Python/pip installation and runs the Python version
 */

const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

// Colors for output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

function log(message, color = '') {
  console.log(color + message + colors.reset);
}

function error(message) {
  console.error(colors.red + '✗ ' + message + colors.reset);
}

function success(message) {
  log('✓ ' + message, colors.green);
}

function info(message) {
  log('ℹ ' + message, colors.cyan);
}

// Check if a command exists
function commandExists(cmd) {
  try {
    execSync(`which ${cmd}`, { stdio: 'ignore' });
    return true;
  } catch (e) {
    return false;
  }
}

// Check if claude-mpm is installed via pip
function isClaudeMpmInstalled() {
  try {
    execSync('pip show claude-mpm', { stdio: 'ignore' });
    return true;
  } catch (e) {
    return false;
  }
}

// Get Python command
function getPythonCommand() {
  if (commandExists('python3')) return 'python3';
  if (commandExists('python')) return 'python';
  return null;
}

// Install claude-mpm via pip
async function installClaudeMpm() {
  info('Installing claude-mpm Python package...');
  
  const python = getPythonCommand();
  if (!python) {
    error('Python is not installed. Please install Python 3.8 or later.');
    process.exit(1);
  }

  try {
    execSync(`${python} -m pip install --upgrade claude-mpm`, { 
      stdio: 'inherit' 
    });
    success('claude-mpm installed successfully!');
  } catch (e) {
    error('Failed to install claude-mpm. Please try: pip install claude-mpm');
    process.exit(1);
  }
}

// Check Claude CLI is installed
function checkClaude() {
  if (!commandExists('claude')) {
    error('Claude CLI not found. Please install Claude Code 1.0.60 or later.');
    error('Visit: https://claude.ai/code');
    process.exit(1);
  }
  
  // Check version
  try {
    const version = execSync('claude --version', { encoding: 'utf8' }).trim();
    const match = version.match(/(\d+)\.(\d+)\.(\d+)/);
    if (match) {
      const [, major, minor, patch] = match;
      const versionNum = parseInt(major) * 10000 + parseInt(minor) * 100 + parseInt(patch);
      if (versionNum < 10060) {
        error(`Claude Code ${major}.${minor}.${patch} found, but 1.0.60 or later is required.`);
        error('Please update Claude Code: claude update');
        process.exit(1);
      }
    }
  } catch (e) {
    // Continue if version check fails
  }
}

// Main function
async function main() {
  // Check prerequisites
  checkClaude();
  
  const python = getPythonCommand();
  if (!python) {
    error('Python is not installed. Please install Python 3.8 or later.');
    process.exit(1);
  }

  // Check if pip exists
  if (!commandExists('pip') && !commandExists('pip3')) {
    error('pip is not installed. Please install pip.');
    process.exit(1);
  }

  // Install claude-mpm if not present
  if (!isClaudeMpmInstalled()) {
    await installClaudeMpm();
  }

  // Run claude-mpm with all arguments
  const args = process.argv.slice(2);
  const child = spawn('claude-mpm', args, { 
    stdio: 'inherit',
    shell: true 
  });

  child.on('error', (err) => {
    if (err.code === 'ENOENT') {
      error('claude-mpm command not found. Installing...');
      installClaudeMpm().then(() => {
        // Retry after installation
        spawn('claude-mpm', args, { stdio: 'inherit', shell: true });
      });
    } else {
      error(`Failed to run claude-mpm: ${err.message}`);
      process.exit(1);
    }
  });

  child.on('exit', (code) => {
    process.exit(code || 0);
  });
}

// Run main
main().catch(err => {
  error(`Unexpected error: ${err.message}`);
  process.exit(1);
});