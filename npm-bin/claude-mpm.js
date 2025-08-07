#!/usr/bin/env node

/**
 * NPM wrapper for claude-mpm
 * This script checks for Python/pip/pipx installation and runs the Python version
 */

const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');
const readline = require('readline');

// Helper function to ask yes/no questions
function askYesNo(question) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
  
  return new Promise((resolve) => {
    rl.question(`${question} (y/n): `, (answer) => {
      rl.close();
      resolve(answer.toLowerCase() === 'y');
    });
  });
}

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

function warn(message) {
  log('⚠ ' + message, colors.yellow);
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

// Check if claude-mpm is installed via UV
function isClaudeMpmInstalledUv() {
  try {
    execSync('uv pip show claude-mpm', { stdio: 'ignore' });
    return true;
  } catch (e) {
    return false;
  }
}

// Check if claude-mpm is installed via pip
function isClaudeMpmInstalledPip() {
  try {
    execSync('pip show claude-mpm', { stdio: 'ignore' });
    return true;
  } catch (e) {
    return false;
  }
}

// Check if claude-mpm is installed via pipx
function isClaudeMpmInstalledPipx() {
  try {
    execSync('pipx list | grep claude-mpm', { stdio: 'ignore' });
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

// Check if environment is externally managed
function isExternallyManaged() {
  const python = getPythonCommand();
  if (!python) return false;
  
  try {
    // Try to install a dummy package to check
    execSync(`${python} -m pip install --dry-run pip 2>&1`, { encoding: 'utf8' });
    return false;
  } catch (e) {
    return e.toString().includes('externally-managed-environment');
  }
}

// Install pipx if needed
async function installPipx() {
  info('Installing pipx for isolated Python app management...');
  
  try {
    if (process.platform === 'darwin' && commandExists('brew')) {
      execSync('brew install pipx', { stdio: 'inherit' });
      execSync('pipx ensurepath', { stdio: 'inherit' });
      success('pipx installed successfully!');
      return true;
    } else {
      const python = getPythonCommand();
      execSync(`${python} -m pip install --user pipx`, { stdio: 'inherit' });
      execSync(`${python} -m pipx ensurepath`, { stdio: 'inherit' });
      success('pipx installed successfully!');
      return true;
    }
  } catch (e) {
    error('Failed to install pipx automatically.');
    console.log('\nPlease install pipx manually:');
    if (process.platform === 'darwin') {
      console.log('  brew install pipx');
    } else {
      console.log('  python3 -m pip install --user pipx');
    }
    console.log('  pipx ensurepath');
    return false;
  }
}

// Install UV if needed
async function installUv() {
  info('Installing UV for fast Python package management...');
  
  try {
    if (process.platform === 'darwin' && commandExists('brew')) {
      execSync('brew install uv', { stdio: 'inherit' });
      success('UV installed successfully!');
      return true;
    } else {
      // Use the official UV installer
      execSync('curl -LsSf https://astral.sh/uv/install.sh | sh', { stdio: 'inherit', shell: true });
      success('UV installed successfully!');
      info('You may need to restart your terminal for UV to be available in PATH');
      return true;
    }
  } catch (e) {
    error('Failed to install UV automatically.');
    console.log('\nPlease install UV manually:');
    console.log('  curl -LsSf https://astral.sh/uv/install.sh | sh');
    console.log('  or');
    console.log('  brew install uv (macOS)');
    return false;
  }
}

// Install claude-mpm
async function installClaudeMpm() {
  info('Installing claude-mpm Python package...');
  
  const python = getPythonCommand();
  if (!python) {
    error('Python is not installed. Please install Python 3.8 or later.');
    process.exit(1);
  }

  // Try UV first (recommended)
  if (commandExists('uv')) {
    info('Using UV for installation (recommended)...');
    try {
      execSync('uv pip install claude-mpm', { stdio: 'inherit' });
      success('claude-mpm installed successfully via UV!');
      return;
    } catch (e) {
      warn('Failed to install via UV, trying other methods...');
    }
  } else {
    info('UV is the recommended installer for claude-mpm.');
    const answer = process.env.CI ? 'n' : await askYesNo('Would you like to install UV first? (recommended)');
    if (answer) {
      const installed = await installUv();
      if (installed && commandExists('uv')) {
        try {
          execSync('uv pip install claude-mpm', { stdio: 'inherit' });
          success('claude-mpm installed successfully via UV!');
          return;
        } catch (e) {
          warn('Failed to install via UV, trying other methods...');
        }
      }
    }
  }

  // Check if environment is externally managed
  if (isExternallyManaged()) {
    warn('Python environment is externally managed (PEP 668).');
    
    // Try pipx first
    if (commandExists('pipx')) {
      info('Using pipx for installation...');
      try {
        execSync('pipx install claude-mpm', { stdio: 'inherit' });
        success('claude-mpm installed successfully via pipx!');
        info('You may need to restart your terminal or run: source ~/.bashrc');
        return;
      } catch (e) {
        error('Failed to install via pipx.');
      }
    } else {
      info('pipx is recommended for installing Python applications on your system.');
      const installed = await installPipx();
      if (installed) {
        try {
          execSync('pipx install claude-mpm', { stdio: 'inherit' });
          success('claude-mpm installed successfully via pipx!');
          info('You may need to restart your terminal or run: source ~/.bashrc');
          return;
        } catch (e) {
          error('Failed to install via pipx.');
        }
      }
    }
  }

  // Try regular pip install
  try {
    execSync(`${python} -m pip install --upgrade claude-mpm`, { 
      stdio: 'inherit' 
    });
    success('claude-mpm installed successfully!');
  } catch (e) {
    if (e.toString().includes('externally-managed-environment')) {
      error('Cannot install system-wide due to PEP 668.');
      console.log('\nOptions:');
      console.log('1. Install pipx and run: pipx install claude-mpm');
      console.log('2. Use a virtual environment');
      console.log('3. Install with: pip install --user claude-mpm');
    } else {
      error('Failed to install claude-mpm. Please try manually:');
      console.log('  pip install claude-mpm');
      console.log('  or');
      console.log('  pipx install claude-mpm');
    }
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

// Find claude-mpm command
function findClaudeMpmCommand() {
  // Check pipx bin directory FIRST
  const pipxBin = path.join(os.homedir(), '.local', 'bin', 'claude-mpm');
  if (fs.existsSync(pipxBin)) {
    return pipxBin;
  }

  // Check if in Python scripts directory
  const python = getPythonCommand();
  if (python) {
    try {
      const scriptsPath = execSync(`${python} -m site --user-base`, { encoding: 'utf8' }).trim();
      const claudeMpmPath = path.join(scriptsPath, 'bin', 'claude-mpm');
      if (fs.existsSync(claudeMpmPath)) {
        return claudeMpmPath;
      }
    } catch (e) {
      // Ignore
    }
  }

  // Don't use generic 'which' that might find ourselves
  return null;
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

  // Check if claude-mpm is installed
  let claudeMpmCommand = findClaudeMpmCommand();
  
  if (!claudeMpmCommand && !isClaudeMpmInstalledUv() && !isClaudeMpmInstalledPip() && !isClaudeMpmInstalledPipx()) {
    await installClaudeMpm();
    claudeMpmCommand = findClaudeMpmCommand();
    
    if (!claudeMpmCommand) {
      error('claude-mpm was installed but cannot be found in PATH.');
      console.log('\nPlease ensure your PATH includes:');
      console.log('  ~/.local/bin (for pipx or pip --user installations)');
      console.log('\nYou can add it by running:');
      console.log('  echo \'export PATH="$HOME/.local/bin:$PATH"\' >> ~/.bashrc');
      console.log('  source ~/.bashrc');
      process.exit(1);
    }
  }

  // If still not found, try one more time
  if (!claudeMpmCommand) {
    claudeMpmCommand = 'claude-mpm';  // Hope it's in PATH
  }

  // Run claude-mpm with all arguments
  const args = process.argv.slice(2);
  const child = spawn(claudeMpmCommand, args, { 
    stdio: 'inherit',
    shell: true 
  });

  child.on('error', (err) => {
    if (err.code === 'ENOENT') {
      error('claude-mpm command not found after installation.');
      console.log('\nPlease check that claude-mpm is in your PATH.');
      console.log('You may need to restart your terminal or run:');
      console.log('  source ~/.bashrc');
    } else {
      error(`Failed to run claude-mpm: ${err.message}`);
    }
    process.exit(1);
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