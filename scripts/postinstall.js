#!/usr/bin/env node

/**
 * Post-install script for @bobmatnyc/claude-mpm npm package
 * 
 * This is a wrapper that will install the Python package on first run
 */

console.log('\n🎉 @bobmatnyc/claude-mpm installed!');
console.log('\nThis is a wrapper that will install and run the Python package.');
console.log('On first run, it will automatically install claude-mpm via pip.');
console.log('\nRequirements:');
console.log('  • Claude Code 1.0.60 or later');
console.log('  • Python 3.8 or later');
console.log('  • pip');
console.log('\nUsage: claude-mpm [options]');
console.log('\nFor more info: https://github.com/bobmatnyc/claude-mpm\n');

// Quick checks (non-blocking)
const { execSync } = require('child_process');

// Check for Python
try {
  const pythonVersion = execSync('python3 --version 2>&1', { encoding: 'utf8' });
  console.log(`✅ Found ${pythonVersion.trim()}`);
} catch (e) {
  try {
    const pythonVersion = execSync('python --version 2>&1', { encoding: 'utf8' });
    console.log(`✅ Found ${pythonVersion.trim()}`);
  } catch (e2) {
    console.warn('⚠️  Python 3.8+ is required but not found');
    console.warn('   Please install Python from https://python.org');
  }
}

// Check for Claude CLI
try {
  const claudeVersion = execSync('claude --version 2>&1', { encoding: 'utf8' });
  console.log(`✅ Found Claude Code ${claudeVersion.trim()}`);
} catch (e) {
  console.warn('⚠️  Claude Code not found');
  console.warn('   Please install Claude Code 1.0.60+ from https://claude.ai/code');
}