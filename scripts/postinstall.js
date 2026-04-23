#!/usr/bin/env node

/**
 * Post-install script for @bobmatnyc/claude-mpm npm package
 *
 * This is a wrapper that will install the Python package on first run
 */

console.log('\n🎉 @bobmatnyc/claude-mpm npm wrapper installed!');
console.log('\n⚠️  IMPORTANT: This is an npm wrapper for a Python package');
console.log('   The actual claude-mpm implementation requires Python 3.8+\n');

console.log('📋 Requirements:');
console.log('  • Python 3.8 or later');
console.log('  • Claude Code 1.0.60 or later');
console.log('  • UV, pip, or pipx for Python package management\n');

console.log('🚀 Installation Options:');
console.log('  1. UV (recommended): uv pip install claude-mpm');
console.log('  2. pip: pip install claude-mpm');
console.log('  3. pipx: pipx install claude-mpm\n');

console.log('📦 What happens on first run:');
console.log('  • If claude-mpm Python package is not found, this wrapper will:');
console.log('    - Attempt to install it automatically using pip or pipx');
console.log('    - Guide you through any installation issues\n');

console.log('📖 For complete installation guide: https://github.com/bobmatnyc/claude-mpm#installation\n');

// Quick checks (non-blocking)
const { execSync } = require('child_process');

let pythonFound = false;
let pythonPath = null;
let pythonVersion = null;

// Check for Python
try {
  pythonVersion = execSync('python3 --version 2>&1', { encoding: 'utf8' }).trim();
  pythonPath = 'python3';
  pythonFound = true;
} catch (e) {
  try {
    pythonVersion = execSync('python --version 2>&1', { encoding: 'utf8' }).trim();
    pythonPath = 'python';
    pythonFound = true;
  } catch (e2) {
    // Python not found
  }
}

if (pythonFound) {
  // Extract version number
  const versionMatch = pythonVersion.match(/Python (\d+\.\d+\.\d+)/);
  if (versionMatch) {
    const [major, minor] = versionMatch[1].split('.').map(Number);
    if (major >= 3 && minor >= 8) {
      console.log(`✅ Found ${pythonVersion}`);
    } else {
      console.warn(`⚠️  Found ${pythonVersion} but Python 3.8+ is required`);
      console.warn('   Please upgrade Python from https://python.org');
    }
  }
} else {
  console.error('❌ Python not found!');
  console.error('   Python 3.8+ is REQUIRED for claude-mpm to function');
  console.error('   Please install Python from:');
  console.error('   • https://python.org (official)');
  console.error('   • brew install python3 (macOS)');
  console.error('   • apt install python3 (Ubuntu/Debian)');
}

// Check for Claude CLI
try {
  const claudeVersion = execSync('claude --version 2>&1', { encoding: 'utf8' });
  console.log(`✅ Found Claude Code ${claudeVersion.trim()}`);
} catch (e) {
  console.warn('⚠️  Claude Code not found');
  console.warn('   Please install Claude Code 1.0.60+ from https://claude.ai/code');
}

// Check for Python package managers
const packageManagers = [];
try {
  execSync('uv --version 2>&1', { encoding: 'utf8' });
  packageManagers.push('UV');
} catch (e) {}

try {
  execSync('pipx --version 2>&1', { encoding: 'utf8' });
  packageManagers.push('pipx');
} catch (e) {}

try {
  execSync('pip --version 2>&1', { encoding: 'utf8' });
  packageManagers.push('pip');
} catch (e) {}

if (packageManagers.length > 0) {
  console.log(`✅ Found Python package managers: ${packageManagers.join(', ')}`);
} else if (pythonFound) {
  console.warn('⚠️  No Python package managers found (UV, pip, or pipx)');
  console.warn('   The wrapper will attempt to install pip on first run');
}

console.log('\n💡 Next step: Run "claude-mpm" to start using the tool');
