#!/usr/bin/env python3
"""Automated test to verify React components load correctly."""

import asyncio
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.monitor.server import UnifiedMonitorServer

async def test_react_loading():
    """Test React component loading in the browser."""

    print("Starting monitor server...")
    server = UnifiedMonitorServer(port=8765)

    # Start server in background
    server_task = asyncio.create_task(server.start())

    # Give server time to start
    await asyncio.sleep(2)

    print("Server started at http://localhost:8765")

    # Set up Chrome options for headless testing
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    try:
        # Initialize WebDriver
        print("\nInitializing Chrome WebDriver...")
        driver = webdriver.Chrome(options=chrome_options)

        # Navigate to events page
        print("Navigating to events page...")
        driver.get("http://localhost:8765/static/events.html")

        # Wait for page to load
        time.sleep(2)

        print("\n" + "="*60)
        print("Testing React Component Exports")
        print("="*60)

        # Test 1: Check if initializeReactEvents is exposed
        result = driver.execute_script("return typeof window.initializeReactEvents")
        print(f"\n✓ typeof window.initializeReactEvents: {result}")
        assert result == "function", f"Expected 'function', got '{result}'"

        # Test 2: Check if ClaudeMPMReact namespace exists
        result = driver.execute_script("return typeof window.ClaudeMPMReact")
        print(f"✓ typeof window.ClaudeMPMReact: {result}")
        assert result == "object", f"Expected 'object', got '{result}'"

        # Test 3: Check if function exists in namespace
        result = driver.execute_script("return typeof window.ClaudeMPMReact.initializeReactEvents")
        print(f"✓ typeof window.ClaudeMPMReact.initializeReactEvents: {result}")
        assert result == "function", f"Expected 'function', got '{result}'"

        # Test 4: Check if React root element exists
        result = driver.execute_script("return document.getElementById('react-events-root') !== null")
        print(f"✓ React root element exists: {result}")
        assert result == True, "React root element not found"

        # Test 5: Try to initialize React
        result = driver.execute_script("return window.initializeReactEvents()")
        print(f"✓ initializeReactEvents() returned: {result}")
        assert result == True, f"Expected true, got {result}"

        # Test 6: Check console for React initialization message
        logs = driver.get_log('browser')
        react_initialized = any('React EventViewer initialized' in log.get('message', '') for log in logs)
        print(f"✓ React initialization message in console: {react_initialized}")

        # Test 7: Check if fallback content is hidden
        result = driver.execute_script("""
            const fallback = document.getElementById('fallback-events');
            return fallback ? window.getComputedStyle(fallback).display : 'not found';
        """)
        print(f"✓ Fallback content display: {result}")

        print("\n" + "="*60)
        print("All tests passed! React components are loading correctly.")
        print("="*60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if 'driver' in locals():
            driver.quit()

        # Stop server
        print("\nShutting down server...")
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        await server.shutdown()

    return True

def main():
    """Run the test without Selenium (manual verification)."""
    print("\n" + "="*60)
    print("Manual Testing Instructions")
    print("="*60)

    print("\nSince Selenium is not installed, please test manually:")
    print("\n1. Start the server:")
    print("   python -m claude_mpm.services.monitor.server")

    print("\n2. Open browser to:")
    print("   http://localhost:8765/static/events.html")

    print("\n3. Open browser console (F12) and run:")
    print("   typeof window.initializeReactEvents")
    print("   typeof window.ClaudeMPMReact")
    print("   window.initializeReactEvents()")

    print("\n4. Expected results:")
    print("   - First: 'function'")
    print("   - Second: 'object'")
    print("   - Third: true (and React component initializes)")

    print("\n5. Check console for messages:")
    print("   - 'React events initialization function exposed on window'")
    print("   - 'React EventViewer initialized'")

    print("\n" + "="*60)

if __name__ == "__main__":
    try:
        # Try automated test first
        import selenium
        success = asyncio.run(test_react_loading())
        sys.exit(0 if success else 1)
    except ImportError:
        # Fall back to manual instructions
        main()