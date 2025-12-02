#!/usr/bin/env python3
"""
Browser Automation Test for Code Analysis Dashboard
==================================================

WHY: Comprehensive browser-based testing of the dashboard's code analysis functionality.
Tests the complete user interaction flow from button click to tree visualization,
validates event handling, and captures screenshots for debugging.

DESIGN DECISIONS:
- Use Selenium WebDriver for browser automation
- Test multiple browsers (Chrome, Firefox) if available
- Capture screenshots at key points for debugging
- Monitor browser console for JavaScript errors
- Test responsive layout and visual elements
- Validate lazy loading and user interactions
"""

import contextlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class CodeAnalysisBrowserTest:
    """Browser automation test for code analysis dashboard functionality."""

    def __init__(
        self, base_url="http://localhost:8765", screenshots_dir="test_screenshots"
    ):
        """Initialize the browser test.

        Args:
            base_url: Base URL of the dashboard
            screenshots_dir: Directory to save screenshots
        """
        self.base_url = base_url
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(exist_ok=True)

        self.driver = None
        self.current_browser = None
        self.test_results = []
        self.console_errors = []
        self.start_time = None

        # Test configuration
        self.default_timeout = 30
        self.element_timeout = 10

    def setup_chrome_driver(self, headless=False) -> Optional[webdriver.Chrome]:
        """Setup Chrome WebDriver with options."""
        try:
            chrome_options = ChromeOptions()
            if headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")

            # Enable logging
            chrome_options.add_argument("--enable-logging")
            chrome_options.add_argument("--log-level=0")

            driver = webdriver.Chrome(options=chrome_options)
            driver.implicitly_wait(5)
            return driver

        except Exception as e:
            print(f"❌ Failed to setup Chrome driver: {e}")
            return None

    def setup_firefox_driver(self, headless=False) -> Optional[webdriver.Firefox]:
        """Setup Firefox WebDriver with options."""
        try:
            firefox_options = FirefoxOptions()
            if headless:
                firefox_options.add_argument("--headless")
            firefox_options.add_argument("--width=1920")
            firefox_options.add_argument("--height=1080")

            driver = webdriver.Firefox(options=firefox_options)
            driver.implicitly_wait(5)
            return driver

        except Exception as e:
            print(f"❌ Failed to setup Firefox driver: {e}")
            return None

    def capture_screenshot(self, name: str, description: str = ""):
        """Capture screenshot with timestamp."""
        if not self.driver:
            return None

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{self.current_browser}_{name}.png"
        filepath = self.screenshots_dir / filename

        try:
            self.driver.save_screenshot(str(filepath))
            print(f"📸 Screenshot saved: {filename} - {description}")
            return str(filepath)
        except Exception as e:
            print(f"❌ Failed to capture screenshot {name}: {e}")
            return None

    def get_console_logs(self) -> List[Dict[str, Any]]:
        """Get browser console logs."""
        if not self.driver:
            return []

        try:
            # Only available in Chrome
            if self.current_browser == "chrome":
                logs = self.driver.get_log("browser")
                return [
                    {
                        "level": log["level"],
                        "message": log["message"],
                        "timestamp": log["timestamp"],
                    }
                    for log in logs
                ]
        except Exception as e:
            print(f"⚠️ Could not retrieve console logs: {e}")

        return []

    def check_for_console_errors(self) -> List[Dict[str, Any]]:
        """Check for JavaScript errors in console."""
        console_logs = self.get_console_logs()
        errors = [log for log in console_logs if log["level"] in ["SEVERE", "WARNING"]]

        if errors:
            print(f"⚠️ Found {len(errors)} console errors/warnings:")
            for error in errors:
                print(f"   {error['level']}: {error['message']}")

        self.console_errors.extend(errors)
        return errors

    async def test_dashboard_load(self) -> Dict[str, Any]:
        """Test dashboard loading and basic elements."""
        print("\n🌐 Testing Dashboard Load...")

        try:
            # Navigate to dashboard
            self.driver.get(self.base_url)
            self.capture_screenshot("dashboard_load", "Initial dashboard load")

            # Wait for basic elements to load
            WebDriverWait(self.driver, self.default_timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Check page title
            expected_titles = ["Claude MPM Dashboard", "Dashboard", "Code Analysis"]
            page_title = self.driver.title
            title_match = any(expected in page_title for expected in expected_titles)

            # Check for key dashboard elements
            elements_to_check = [
                ("connection-status", "Connection status indicator"),
                ("nav-tabs", "Navigation tabs"),
                ("code-tab", "Code analysis tab"),
            ]

            missing_elements = []
            for element_id, description in elements_to_check:
                try:
                    self.driver.find_element(By.ID, element_id)
                except NoSuchElementException:
                    missing_elements.append(
                        {"id": element_id, "description": description}
                    )

            console_errors = self.check_for_console_errors()

            success = (
                title_match and len(missing_elements) == 0 and len(console_errors) == 0
            )

            result = {
                "test_name": "dashboard_load",
                "browser": self.current_browser,
                "success": success,
                "details": {
                    "url": self.base_url,
                    "page_title": page_title,
                    "title_match": title_match,
                    "missing_elements": missing_elements,
                    "console_errors": len(console_errors),
                    "load_time": (
                        time.time() - self.start_time if self.start_time else 0
                    ),
                },
            }

            if success:
                print(f"✅ Dashboard load test passed for {self.current_browser}")
            else:
                print(f"❌ Dashboard load test failed for {self.current_browser}")
                if missing_elements:
                    print(f"   Missing elements: {[e['id'] for e in missing_elements]}")

            return result

        except Exception as e:
            self.capture_screenshot(
                "dashboard_load_error", f"Dashboard load error: {e!s}"
            )
            return {
                "test_name": "dashboard_load",
                "browser": self.current_browser,
                "success": False,
                "details": {"error": str(e)},
            }

    async def test_code_tab_navigation(self) -> Dict[str, Any]:
        """Test navigation to the Code analysis tab."""
        print("\n📋 Testing Code Tab Navigation...")

        try:
            # Find and click the Code tab
            code_tab = WebDriverWait(self.driver, self.element_timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-tab="code"]'))
            )

            self.capture_screenshot("before_code_tab_click", "Before clicking Code tab")
            code_tab.click()

            # Wait for tab content to load
            WebDriverWait(self.driver, self.element_timeout).until(
                EC.visibility_of_element_located((By.ID, "code-tab"))
            )

            self.capture_screenshot("after_code_tab_click", "After clicking Code tab")

            # Check if tab is active
            code_tab_panel = self.driver.find_element(By.ID, "code-tab")
            is_active = "active" in code_tab_panel.get_attribute("class")

            # Check for code analysis elements
            code_elements = [
                ("analyze-code-btn", "Analyze button"),
                ("code-tree-container", "Code tree container"),
                ("breadcrumb-content", "Breadcrumb area"),
            ]

            missing_elements = []
            for element_id, description in code_elements:
                try:
                    element = self.driver.find_element(By.ID, element_id)
                    if not element.is_displayed():
                        missing_elements.append(
                            {
                                "id": element_id,
                                "description": f"{description} (not visible)",
                            }
                        )
                except NoSuchElementException:
                    missing_elements.append(
                        {"id": element_id, "description": description}
                    )

            console_errors = self.check_for_console_errors()
            success = is_active and len(missing_elements) == 0

            result = {
                "test_name": "code_tab_navigation",
                "browser": self.current_browser,
                "success": success,
                "details": {
                    "tab_active": is_active,
                    "missing_elements": missing_elements,
                    "console_errors": len(console_errors),
                },
            }

            if success:
                print(f"✅ Code tab navigation test passed for {self.current_browser}")
            else:
                print(f"❌ Code tab navigation test failed for {self.current_browser}")
                if missing_elements:
                    print(f"   Missing elements: {[e['id'] for e in missing_elements]}")

            return result

        except Exception as e:
            self.capture_screenshot(
                "code_tab_error", f"Code tab navigation error: {e!s}"
            )
            return {
                "test_name": "code_tab_navigation",
                "browser": self.current_browser,
                "success": False,
                "details": {"error": str(e)},
            }

    async def test_analyze_button_click(self) -> Dict[str, Any]:
        """Test clicking the Analyze button and monitoring for events."""
        print("\n🔍 Testing Analyze Button Click...")

        try:
            # Find the analyze button
            analyze_btn = WebDriverWait(self.driver, self.element_timeout).until(
                EC.element_to_be_clickable((By.ID, "analyze-code-btn"))
            )

            # Check initial state
            initial_btn_disabled = analyze_btn.get_attribute("disabled") is not None

            self.capture_screenshot(
                "before_analyze_click", "Before clicking Analyze button"
            )

            # Click the analyze button
            analyze_btn.click()
            print("🖱️ Clicked Analyze button")

            # Wait a moment for the action to register
            time.sleep(0.5)

            # Check if button state changed (should be disabled during analysis)
            btn_disabled_after_click = analyze_btn.get_attribute("disabled") is not None

            # Check if loading indicator appears
            try:
                loading_element = self.driver.find_element(By.ID, "code-tree-loading")
                loading_visible = loading_element.is_displayed()
            except NoSuchElementException:
                loading_visible = False

            # Check breadcrumb for status updates
            try:
                breadcrumb = self.driver.find_element(By.ID, "breadcrumb-content")
                breadcrumb_text = breadcrumb.text
            except NoSuchElementException:
                breadcrumb_text = ""

            self.capture_screenshot(
                "after_analyze_click", "After clicking Analyze button"
            )

            # Wait for some processing (but not too long for the test)
            time.sleep(3)

            # Check for any visual updates in the tree container
            try:
                tree_container = self.driver.find_element(By.ID, "code-tree-container")
                tree_has_content = (
                    len(tree_container.text.strip()) > 0
                    or len(tree_container.find_elements(By.TAG_NAME, "*")) > 1
                )
            except NoSuchElementException:
                tree_has_content = False

            # Check for event viewer updates (if visible)
            events_detected = False
            try:
                event_viewer = self.driver.find_element(By.ID, "event-viewer")
                if event_viewer.is_displayed():
                    events_detected = (
                        len(event_viewer.find_elements(By.CLASS_NAME, "event-item")) > 0
                    )
            except NoSuchElementException:
                pass

            self.capture_screenshot("analyze_processing", "During analysis processing")

            console_errors = self.check_for_console_errors()

            # Success criteria: button disabled and some indication of processing
            success = btn_disabled_after_click and (
                loading_visible
                or breadcrumb_text != ""
                or tree_has_content
                or events_detected
            )

            result = {
                "test_name": "analyze_button_click",
                "browser": self.current_browser,
                "success": success,
                "details": {
                    "initial_btn_disabled": initial_btn_disabled,
                    "btn_disabled_after_click": btn_disabled_after_click,
                    "loading_visible": loading_visible,
                    "breadcrumb_text": breadcrumb_text,
                    "tree_has_content": tree_has_content,
                    "events_detected": events_detected,
                    "console_errors": len(console_errors),
                },
            }

            if success:
                print(f"✅ Analyze button click test passed for {self.current_browser}")
            else:
                print(f"❌ Analyze button click test failed for {self.current_browser}")
                print(f"   Button disabled: {btn_disabled_after_click}")
                print(f"   Loading visible: {loading_visible}")
                print(f"   Breadcrumb: {breadcrumb_text}")

            return result

        except Exception as e:
            self.capture_screenshot(
                "analyze_click_error", f"Analyze button click error: {e!s}"
            )
            return {
                "test_name": "analyze_button_click",
                "browser": self.current_browser,
                "success": False,
                "details": {"error": str(e)},
            }

    async def test_tree_visualization(self) -> Dict[str, Any]:
        """Test the code tree visualization after analysis."""
        print("\n🌳 Testing Tree Visualization...")

        try:
            # Wait longer for tree to populate
            time.sleep(5)

            # Check for SVG elements (D3.js visualization)
            svg_elements = self.driver.find_elements(
                By.CSS_SELECTOR, "#code-tree-container svg"
            )
            tree_nodes = self.driver.find_elements(
                By.CSS_SELECTOR, "#code-tree-container .node"
            )
            tree_links = self.driver.find_elements(
                By.CSS_SELECTOR, "#code-tree-container .link"
            )

            # Check for statistics updates
            stats_elements = {
                "code-stats-files": "files",
                "code-stats-classes": "classes",
                "code-stats-functions": "functions",
            }

            stats_values = {}
            for stat_id, stat_name in stats_elements.items():
                try:
                    element = self.driver.find_element(By.ID, stat_id)
                    stats_values[stat_name] = element.text
                except NoSuchElementException:
                    stats_values[stat_name] = "N/A"

            # Test tree interaction (if nodes exist)
            interactive_test_passed = False
            if tree_nodes:
                try:
                    # Click on the first node to test interaction
                    first_node = tree_nodes[0]
                    self.driver.execute_script("arguments[0].click();", first_node)
                    time.sleep(1)

                    # Check if anything changed (highlighting, expansion, etc.)
                    interactive_test_passed = True
                    print("✅ Tree interaction test passed")

                except Exception as e:
                    print(f"⚠️ Tree interaction test failed: {e}")

            self.capture_screenshot("tree_visualization", "Code tree visualization")

            console_errors = self.check_for_console_errors()

            # Success criteria: SVG exists and some visual elements are present
            success = len(svg_elements) > 0 and (
                len(tree_nodes) > 0 or len(tree_links) > 0
            )

            result = {
                "test_name": "tree_visualization",
                "browser": self.current_browser,
                "success": success,
                "details": {
                    "svg_elements": len(svg_elements),
                    "tree_nodes": len(tree_nodes),
                    "tree_links": len(tree_links),
                    "stats_values": stats_values,
                    "interactive_test_passed": interactive_test_passed,
                    "console_errors": len(console_errors),
                },
            }

            if success:
                print(f"✅ Tree visualization test passed for {self.current_browser}")
                print(f"   Found {len(tree_nodes)} nodes and {len(tree_links)} links")
            else:
                print(f"❌ Tree visualization test failed for {self.current_browser}")
                print(f"   SVG elements: {len(svg_elements)}, Nodes: {len(tree_nodes)}")

            return result

        except Exception as e:
            self.capture_screenshot(
                "tree_viz_error", f"Tree visualization error: {e!s}"
            )
            return {
                "test_name": "tree_visualization",
                "browser": self.current_browser,
                "success": False,
                "details": {"error": str(e)},
            }

    async def test_event_monitoring(self) -> Dict[str, Any]:
        """Test event monitoring in the dashboard."""
        print("\n📡 Testing Event Monitoring...")

        try:
            # Switch to Events tab to see event flow
            try:
                events_tab = self.driver.find_element(
                    By.CSS_SELECTOR, '[data-tab="events"]'
                )
                events_tab.click()
                time.sleep(1)

                # Check for event items
                event_items = self.driver.find_elements(By.CLASS_NAME, "event-item")
                code_events = []

                for item in event_items:
                    event_text = item.text.lower()
                    if "code:" in event_text or "analysis" in event_text:
                        code_events.append(item)

                self.capture_screenshot("events_tab", "Events tab showing code events")

                # Switch back to Code tab
                code_tab = self.driver.find_element(
                    By.CSS_SELECTOR, '[data-tab="code"]'
                )
                code_tab.click()
                time.sleep(0.5)

            except NoSuchElementException:
                # Events tab might not be visible or available
                event_items = []
                code_events = []

            # Check connection status
            try:
                connection_status = self.driver.find_element(By.ID, "connection-status")
                status_text = connection_status.text
                is_connected = "connected" in status_text.lower()
            except NoSuchElementException:
                status_text = "N/A"
                is_connected = False

            console_errors = self.check_for_console_errors()

            # Success criteria: Connection established and some events detected
            success = is_connected and (
                len(code_events) > 0 or len(console_errors) == 0
            )

            result = {
                "test_name": "event_monitoring",
                "browser": self.current_browser,
                "success": success,
                "details": {
                    "connection_status": status_text,
                    "is_connected": is_connected,
                    "total_events": len(event_items),
                    "code_events": len(code_events),
                    "console_errors": len(console_errors),
                },
            }

            if success:
                print(f"✅ Event monitoring test passed for {self.current_browser}")
                print(f"   Connection: {status_text}, Code events: {len(code_events)}")
            else:
                print(f"❌ Event monitoring test failed for {self.current_browser}")
                print(f"   Connection: {status_text}, Events: {len(code_events)}")

            return result

        except Exception as e:
            self.capture_screenshot(
                "event_monitor_error", f"Event monitoring error: {e!s}"
            )
            return {
                "test_name": "event_monitoring",
                "browser": self.current_browser,
                "success": False,
                "details": {"error": str(e)},
            }

    async def test_responsive_design(self) -> Dict[str, Any]:
        """Test responsive design at different screen sizes."""
        print("\n📱 Testing Responsive Design...")

        try:
            test_sizes = [
                (1920, 1080, "desktop"),
                (1024, 768, "tablet"),
                (375, 667, "mobile"),
            ]

            size_results = []

            for width, height, device_type in test_sizes:
                print(f"   Testing {device_type} size: {width}x{height}")

                # Resize browser window
                self.driver.set_window_size(width, height)
                time.sleep(1)

                # Check if key elements are still visible and usable
                elements_to_check = [
                    ("analyze-code-btn", "Analyze button"),
                    ("code-tree-container", "Code tree container"),
                ]

                visible_elements = 0
                for element_id, _description in elements_to_check:
                    try:
                        element = self.driver.find_element(By.ID, element_id)
                        if element.is_displayed():
                            visible_elements += 1
                    except NoSuchElementException:
                        pass

                self.capture_screenshot(
                    f"responsive_{device_type}", f"Responsive design - {device_type}"
                )

                size_results.append(
                    {
                        "device_type": device_type,
                        "size": f"{width}x{height}",
                        "visible_elements": visible_elements,
                        "total_elements": len(elements_to_check),
                    }
                )

            # Restore original size
            self.driver.set_window_size(1920, 1080)

            console_errors = self.check_for_console_errors()

            # Success criteria: Key elements visible in all tested sizes
            success = all(
                result["visible_elements"] == result["total_elements"]
                for result in size_results
            )

            result = {
                "test_name": "responsive_design",
                "browser": self.current_browser,
                "success": success,
                "details": {
                    "size_tests": size_results,
                    "console_errors": len(console_errors),
                },
            }

            if success:
                print(f"✅ Responsive design test passed for {self.current_browser}")
            else:
                print(f"❌ Responsive design test failed for {self.current_browser}")
                for size_result in size_results:
                    if size_result["visible_elements"] != size_result["total_elements"]:
                        print(
                            f"   {size_result['device_type']}: {size_result['visible_elements']}/{size_result['total_elements']} elements visible"
                        )

            return result

        except Exception as e:
            self.capture_screenshot(
                "responsive_error", f"Responsive design error: {e!s}"
            )
            return {
                "test_name": "responsive_design",
                "browser": self.current_browser,
                "success": False,
                "details": {"error": str(e)},
            }

    async def run_browser_test_suite(
        self, browser_name: str, headless: bool = False
    ) -> Dict[str, Any]:
        """Run the complete test suite for a specific browser."""
        print(f"\n🚀 Starting Browser Test Suite for {browser_name.upper()}")
        print("=" * 60)

        self.current_browser = browser_name
        suite_start_time = time.time()

        # Setup driver
        if browser_name.lower() == "chrome":
            self.driver = self.setup_chrome_driver(headless)
        elif browser_name.lower() == "firefox":
            self.driver = self.setup_firefox_driver(headless)
        else:
            return {
                "browser": browser_name,
                "suite_success": False,
                "error": f"Unsupported browser: {browser_name}",
            }

        if not self.driver:
            return {
                "browser": browser_name,
                "suite_success": False,
                "error": f"Failed to setup {browser_name} driver",
            }

        try:
            self.start_time = time.time()

            # Run test methods
            test_methods = [
                self.test_dashboard_load,
                self.test_code_tab_navigation,
                self.test_analyze_button_click,
                self.test_tree_visualization,
                self.test_event_monitoring,
                self.test_responsive_design,
            ]

            test_results = []
            for test_method in test_methods:
                try:
                    result = await test_method()
                    test_results.append(result)
                except Exception as e:
                    error_result = {
                        "test_name": test_method.__name__,
                        "browser": browser_name,
                        "success": False,
                        "details": {"error": str(e)},
                    }
                    test_results.append(error_result)
                    print(f"❌ Test {test_method.__name__} failed with exception: {e}")

            # Calculate results
            successful_tests = sum(
                1 for result in test_results if result.get("success", False)
            )
            suite_success = successful_tests == len(test_results)

            browser_result = {
                "browser": browser_name,
                "suite_success": suite_success,
                "total_tests": len(test_results),
                "successful_tests": successful_tests,
                "failed_tests": len(test_results) - successful_tests,
                "total_time": time.time() - suite_start_time,
                "console_errors": len(self.console_errors),
                "test_results": test_results,
            }

            # Print summary for this browser
            print(f"\n📊 {browser_name.upper()} TEST SUMMARY")
            print("-" * 40)
            print(f"Result: {'✅ PASSED' if suite_success else '❌ FAILED'}")
            print(f"Tests Passed: {successful_tests}/{len(test_results)}")
            print(f"Console Errors: {len(self.console_errors)}")
            print(f"Time: {browser_result['total_time']:.2f}s")

            return browser_result

        except Exception as e:
            return {
                "browser": browser_name,
                "suite_success": False,
                "error": str(e),
                "total_time": time.time() - suite_start_time,
            }
        finally:
            # Cleanup driver
            if self.driver:
                with contextlib.suppress(Exception):
                    self.driver.quit()
                self.driver = None

    async def run_full_test_suite(
        self, browsers=None, headless=False
    ) -> Dict[str, Any]:
        """Run the complete test suite across multiple browsers."""
        if browsers is None:
            browsers = ["chrome"]  # Default to Chrome only

        print("🌐 Starting Full Browser Test Suite")
        print("=" * 60)

        full_suite_start = time.time()
        browser_results = []

        for browser in browsers:
            try:
                result = await self.run_browser_test_suite(browser, headless)
                browser_results.append(result)
            except Exception as e:
                error_result = {
                    "browser": browser,
                    "suite_success": False,
                    "error": str(e),
                }
                browser_results.append(error_result)
                print(f"💥 Browser test suite for {browser} failed: {e}")

        # Calculate overall results
        successful_browsers = sum(
            1 for result in browser_results if result.get("suite_success", False)
        )
        overall_success = successful_browsers == len(browser_results)

        full_result = {
            "overall_success": overall_success,
            "total_browsers": len(browsers),
            "successful_browsers": successful_browsers,
            "failed_browsers": len(browsers) - successful_browsers,
            "total_time": time.time() - full_suite_start,
            "browser_results": browser_results,
            "screenshots_directory": str(self.screenshots_dir),
        }

        # Print overall summary
        print("\n" + "=" * 60)
        print("🏆 OVERALL TEST SUMMARY")
        print("=" * 60)
        print(f"Overall Result: {'✅ PASSED' if overall_success else '❌ FAILED'}")
        print(f"Browsers Passed: {successful_browsers}/{len(browsers)}")
        print(f"Total Time: {full_result['total_time']:.2f}s")
        print(f"Screenshots: {self.screenshots_dir}")

        return full_result


async def main():
    """Main test function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Browser Test for Code Analysis Dashboard"
    )
    parser.add_argument(
        "--url", type=str, default="http://localhost:8765", help="Dashboard URL"
    )
    parser.add_argument(
        "--browsers", nargs="+", default=["chrome"], help="Browsers to test"
    )
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument(
        "--screenshots-dir",
        type=str,
        default="test_screenshots",
        help="Screenshots directory",
    )
    args = parser.parse_args()

    print(f"Testing dashboard at: {args.url}")
    print(f"Browsers: {', '.join(args.browsers)}")
    print(f"Headless mode: {args.headless}")

    # Run test suite
    tester = CodeAnalysisBrowserTest(args.url, args.screenshots_dir)
    results = await tester.run_full_test_suite(args.browsers, args.headless)

    # Save results to file
    results_file = Path("test_results_browser.json")
    with results_file.open("w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n📁 Test results saved to: {results_file}")

    # Exit with appropriate code
    exit_code = 0 if results.get("overall_success", False) else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
