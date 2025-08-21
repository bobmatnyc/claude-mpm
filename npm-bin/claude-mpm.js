#!/usr/bin/env node

/**
 * Claude MPM npm wrapper
 * This wrapper ensures Python 3.8+ is available and launches the claude-mpm Python package
 */

const { execSync, spawn } = require('child_process');
const { existsSync } = require('fs');
const path = require('path');

const REQUIRED_PYTHON_VERSION = [3, 8];

function checkPythonVersion(pythonCmd) {
    try {
        const versionOutput = execSync(`${pythonCmd} --version`, { encoding: 'utf8', stdio: 'pipe' });
        const versionMatch = versionOutput.match(/Python (\d+)\.(\d+)\.(\d+)/);
        
        if (!versionMatch) return false;
        
        const [, major, minor] = versionMatch.map(Number);
        return major > REQUIRED_PYTHON_VERSION[0] || 
               (major === REQUIRED_PYTHON_VERSION[0] && minor >= REQUIRED_PYTHON_VERSION[1]);
    } catch (error) {
        return false;
    }
}

function findPython() {
    const pythonCommands = ['python3', 'python', 'python3.11', 'python3.10', 'python3.9', 'python3.8'];
    
    for (const cmd of pythonCommands) {
        if (checkPythonVersion(cmd)) {
            return cmd;
        }
    }
    return null;
}

function main() {
    const pythonCmd = findPython();
    
    if (!pythonCmd) {
        console.error(`
❌ Error: Python ${REQUIRED_PYTHON_VERSION.join('.')}+ is required but not found.

Please install Python ${REQUIRED_PYTHON_VERSION.join('.')} or later and try again.
You can download Python from: https://www.python.org/downloads/

Alternatively, install claude-mpm directly with pip:
  pip install claude-mpm
`);
        process.exit(1);
    }

    // Check if claude-mpm is already installed
    try {
        execSync(`${pythonCmd} -c "import claude_mpm"`, { stdio: 'pipe' });
    } catch (error) {
        console.log('📦 Installing claude-mpm Python package...');
        try {
            execSync(`${pythonCmd} -m pip install claude-mpm`, { stdio: 'inherit' });
            console.log('✅ claude-mpm installed successfully!');
        } catch (installError) {
            console.error(`
❌ Failed to install claude-mpm Python package.

Please install it manually:
  ${pythonCmd} -m pip install claude-mpm

Or using pip directly:
  pip install claude-mpm
`);
            process.exit(1);
        }
    }

    // Launch claude-mpm with all arguments
    const args = process.argv.slice(2);
    const child = spawn(pythonCmd, ['-m', 'claude_mpm'].concat(args), { 
        stdio: 'inherit',
        env: process.env 
    });

    child.on('exit', (code) => {
        process.exit(code || 0);
    });

    child.on('error', (error) => {
        console.error(`❌ Error launching claude-mpm: ${error.message}`);
        process.exit(1);
    });
}

if (require.main === module) {
    main();
}

module.exports = { main, findPython, checkPythonVersion };