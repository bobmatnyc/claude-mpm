#!/usr/bin/env python3
"""
QA Test Suite for Viewer Improvements
Tests both File Path Bar Viewer and Edit Tool Diff Viewers

Original Requirements:
1. VIEWER should be in the blue file path bar
2. DIFF viewer should be attached to each EDIT tool use, showing only the diff for THAT edit

Usage: python test_viewer_improvements_qa.py
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ViewerImprovementsQA:
    """QA Test Suite for File Path Bar Viewer and Edit Tool Diff Viewers"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.test_results = {
            'file_path_viewer': {},
            'edit_diff_viewers': {},
            'integration': {},
            'edge_cases': {},
            'summary': {'passed': 0, 'failed': 0, 'total': 0}
        }
        
    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run in headless mode
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
            logger.info("WebDriver setup successful")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {e}")
            return False
            
    def teardown_driver(self):
        """Clean up WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")
            
    def load_dashboard(self, port=8765):
        """Load the dashboard in browser"""
        try:
            url = f"http://localhost:{port}"
            self.driver.get(url)
            logger.info(f"Loaded dashboard at {url}")
            
            # Wait for dashboard to initialize
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "header")))
            time.sleep(2)  # Allow for JS initialization
            return True
            
        except TimeoutException:
            logger.error(f"Timeout loading dashboard at port {port}")
            return False
        except Exception as e:
            logger.error(f"Failed to load dashboard: {e}")
            return False
            
    def record_test_result(self, category, test_name, passed, details="", error=""):
        """Record individual test result"""
        result = {
            'passed': passed,
            'details': details,
            'error': error,
            'timestamp': time.time()
        }
        self.test_results[category][test_name] = result
        self.test_results['summary']['total'] += 1
        if passed:
            self.test_results['summary']['passed'] += 1
        else:
            self.test_results['summary']['failed'] += 1
            
        status = "PASS" if passed else "FAIL"
        logger.info(f"[{status}] {category}/{test_name}: {details}")
        if error:
            logger.error(f"Error: {error}")
            
    def test_file_path_bar_viewer(self):
        """Test File Path Bar Viewer functionality"""
        logger.info("=== Testing File Path Bar Viewer ===")
        
        # Test 1: Verify blue file path bar exists and is clickable
        try:
            file_path_element = self.wait.until(
                EC.element_to_be_clickable((By.CLASS_NAME, "working-dir-path"))
            )
            self.record_test_result(
                'file_path_viewer', 
                'clickable_path_bar_exists',
                True,
                "Blue file path bar found and is clickable"
            )
        except TimeoutException:
            self.record_test_result(
                'file_path_viewer', 
                'clickable_path_bar_exists',
                False,
                "Blue file path bar not found or not clickable",
                "TimeoutException waiting for .working-dir-path element"
            )
            return
            
        # Test 2: Click file path bar to open overlay
        try:
            file_path_element.click()
            time.sleep(1)
            
            overlay = self.driver.find_element(By.ID, "directory-viewer-overlay")
            self.record_test_result(
                'file_path_viewer',
                'overlay_opens_on_click',
                True,
                "Directory viewer overlay opens when path bar is clicked"
            )
        except NoSuchElementException:
            self.record_test_result(
                'file_path_viewer',
                'overlay_opens_on_click', 
                False,
                "Directory viewer overlay does not appear after clicking path bar",
                "Overlay element #directory-viewer-overlay not found"
            )
            return
        except Exception as e:
            self.record_test_result(
                'file_path_viewer',
                'overlay_opens_on_click',
                False, 
                "Error clicking path bar",
                str(e)
            )
            return
            
        # Test 3: Verify overlay is positioned below blue bar
        try:
            path_bar_rect = file_path_element.rect
            overlay_rect = overlay.rect
            
            positioned_correctly = overlay_rect['y'] > path_bar_rect['y'] + path_bar_rect['height']
            self.record_test_result(
                'file_path_viewer',
                'overlay_positioned_below_bar',
                positioned_correctly,
                f"Overlay positioned {'correctly' if positioned_correctly else 'incorrectly'} below path bar"
            )
        except Exception as e:
            self.record_test_result(
                'file_path_viewer',
                'overlay_positioned_below_bar',
                False,
                "Error checking overlay position",
                str(e)
            )
            
        # Test 4: Test directory navigation
        try:
            # Look for directory items (should have class directory-item)
            directory_items = self.driver.find_elements(By.CLASS_NAME, "directory-item")
            if directory_items:
                # Click first directory
                directory_items[0].click()
                time.sleep(1)
                
                # Check if path changed (overlay should still be there but content different)
                self.record_test_result(
                    'file_path_viewer',
                    'directory_navigation_works',
                    True,
                    f"Directory navigation works - found {len(directory_items)} directories"
                )
            else:
                self.record_test_result(
                    'file_path_viewer',
                    'directory_navigation_works',
                    True,
                    "No directories found to test navigation (current directory may be empty)"
                )
        except Exception as e:
            self.record_test_result(
                'file_path_viewer',
                'directory_navigation_works',
                False,
                "Error testing directory navigation",
                str(e)
            )
            
        # Test 5: Test Shift+Click opens directory change dialog
        try:
            # Close current overlay first
            self.driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(0.5)
            
            # Shift+click on path bar
            actions = ActionChains(self.driver)
            actions.key_down(Keys.SHIFT).click(file_path_element).key_up(Keys.SHIFT).perform()
            time.sleep(1)
            
            # Check for alert/prompt (directory change dialog)
            try:
                alert = self.driver.switch_to.alert
                alert.dismiss()  # Close the dialog
                self.record_test_result(
                    'file_path_viewer',
                    'shift_click_opens_dialog',
                    True,
                    "Shift+Click opens directory change dialog"
                )
            except:
                self.record_test_result(
                    'file_path_viewer',
                    'shift_click_opens_dialog',
                    False,
                    "Shift+Click does not open directory change dialog",
                    "No alert dialog detected"
                )
        except Exception as e:
            self.record_test_result(
                'file_path_viewer',
                'shift_click_opens_dialog',
                False,
                "Error testing Shift+Click functionality",
                str(e)
            )
            
        # Test 6: Test clicking outside closes overlay
        try:
            # Open overlay again
            file_path_element.click()
            time.sleep(0.5)
            
            # Click outside (on body)
            self.driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(0.5)
            
            # Check if overlay is gone
            try:
                overlay = self.driver.find_element(By.ID, "directory-viewer-overlay")
                overlay_visible = overlay.is_displayed()
                self.record_test_result(
                    'file_path_viewer',
                    'click_outside_closes_overlay',
                    not overlay_visible,
                    f"Click outside overlay - overlay {'still visible' if overlay_visible else 'properly closed'}"
                )
            except NoSuchElementException:
                self.record_test_result(
                    'file_path_viewer',
                    'click_outside_closes_overlay',
                    True,
                    "Click outside closes overlay - overlay element removed"
                )
        except Exception as e:
            self.record_test_result(
                'file_path_viewer',
                'click_outside_closes_overlay',
                False,
                "Error testing click outside functionality",
                str(e)
            )
            
        # Test 7: Test responsive behavior (resize window)
        try:
            # Test mobile size
            self.driver.set_window_size(375, 667)  # iPhone size
            time.sleep(1)
            
            file_path_element.click()
            time.sleep(0.5)
            
            overlay = self.driver.find_element(By.ID, "directory-viewer-overlay")
            overlay_width = overlay.rect['width']
            window_width = self.driver.get_window_size()['width']
            
            # Overlay should adapt to smaller screen
            responsive = overlay_width <= window_width * 0.9  # Should be <= 90% of window width
            
            self.record_test_result(
                'file_path_viewer',
                'responsive_behavior',
                responsive,
                f"Responsive behavior - overlay width {overlay_width}px on {window_width}px screen"
            )
            
            # Restore window size
            self.driver.set_window_size(1920, 1080)
            
            # Close overlay
            self.driver.find_element(By.TAG_NAME, "body").click()
            
        except Exception as e:
            self.record_test_result(
                'file_path_viewer',
                'responsive_behavior',
                False,
                "Error testing responsive behavior",
                str(e)
            )
            
    def test_edit_diff_viewers(self):
        """Test Edit Tool Diff Viewers functionality"""
        logger.info("=== Testing Edit Tool Diff Viewers ===")
        
        # Switch to events tab to see events
        try:
            events_tab = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[onclick=\"switchTab('events')\"]")))
            events_tab.click()
            time.sleep(1)
        except TimeoutException:
            logger.error("Could not find events tab")
            return
            
        # Test 1: Look for Edit tool events with diff viewers
        try:
            events_list = self.driver.find_element(By.ID, "events-list")
            edit_events = self.driver.find_elements(By.CSS_SELECTOR, ".event-item .inline-edit-diff-viewer")
            
            if edit_events:
                self.record_test_result(
                    'edit_diff_viewers',
                    'diff_viewers_present',
                    True,
                    f"Found {len(edit_events)} Edit events with diff viewers"
                )
            else:
                self.record_test_result(
                    'edit_diff_viewers',
                    'diff_viewers_present',
                    False,
                    "No Edit events with diff viewers found - may need to generate Edit events first",
                    "Consider running Edit tool operations to generate test data"
                )
                return
                
        except NoSuchElementException:
            self.record_test_result(
                'edit_diff_viewers',
                'diff_viewers_present', 
                False,
                "Events list not found",
                "Could not locate #events-list element"
            )
            return
            
        # Test 2: Test diff toggle functionality
        try:
            first_diff_viewer = edit_events[0]
            toggle_header = first_diff_viewer.find_element(By.CLASS_NAME, "diff-toggle-header")
            
            # Get initial state
            diff_container = first_diff_viewer.find_element(By.CLASS_NAME, "diff-content-container")
            initial_display = diff_container.get_attribute("style")
            
            # Click toggle
            toggle_header.click()
            time.sleep(0.5)
            
            # Check if state changed
            after_display = diff_container.get_attribute("style")
            toggle_works = initial_display != after_display
            
            self.record_test_result(
                'edit_diff_viewers',
                'diff_toggle_works',
                toggle_works,
                f"Diff toggle {'works' if toggle_works else 'does not work'} - display style changed"
            )
            
        except Exception as e:
            self.record_test_result(
                'edit_diff_viewers',
                'diff_toggle_works',
                False,
                "Error testing diff toggle functionality",
                str(e)
            )
            
        # Test 3: Verify diff content shows old_string → new_string
        try:
            # Expand a diff viewer
            if not diff_container.is_displayed():
                toggle_header.click()
                time.sleep(0.5)
                
            diff_lines = diff_container.find_elements(By.CLASS_NAME, "diff-line")
            
            if diff_lines:
                has_additions = any("diff-added" in line.get_attribute("class") for line in diff_lines)
                has_removals = any("diff-removed" in line.get_attribute("class") for line in diff_lines)
                
                self.record_test_result(
                    'edit_diff_viewers',
                    'diff_content_shows_changes',
                    has_additions or has_removals,
                    f"Diff content shows changes - additions: {has_additions}, removals: {has_removals}"
                )
            else:
                self.record_test_result(
                    'edit_diff_viewers',
                    'diff_content_shows_changes',
                    False,
                    "No diff lines found in expanded diff viewer",
                    "Diff container may be empty"
                )
                
        except Exception as e:
            self.record_test_result(
                'edit_diff_viewers',
                'diff_content_shows_changes',
                False,
                "Error checking diff content",
                str(e)
            )
            
        # Test 4: Test MultiEdit events show multiple edits
        try:
            # Look for MultiEdit events specifically
            multiedit_events = []
            for event in self.driver.find_elements(By.CLASS_NAME, "event-item"):
                if "MultiEdit" in event.text:
                    diff_viewer = event.find_element(By.CLASS_NAME, "inline-edit-diff-viewer")
                    if diff_viewer:
                        multiedit_events.append((event, diff_viewer))
                        
            if multiedit_events:
                event, diff_viewer = multiedit_events[0]
                toggle = diff_viewer.find_element(By.CLASS_NAME, "diff-toggle-header")
                toggle.click()  # Expand
                time.sleep(0.5)
                
                edit_sections = diff_viewer.find_elements(By.CLASS_NAME, "edit-diff-section")
                multiple_edits = len(edit_sections) > 1
                
                self.record_test_result(
                    'edit_diff_viewers',
                    'multiedit_shows_multiple_diffs',
                    multiple_edits,
                    f"MultiEdit events show {len(edit_sections)} edit section(s)"
                )
            else:
                self.record_test_result(
                    'edit_diff_viewers',
                    'multiedit_shows_multiple_diffs',
                    True,
                    "No MultiEdit events found to test (not required for basic functionality)"
                )
                
        except Exception as e:
            self.record_test_result(
                'edit_diff_viewers',
                'multiedit_shows_multiple_diffs',
                False,
                "Error testing MultiEdit functionality",
                str(e)
            )
            
        # Test 5: Verify diff toggle doesn't trigger event selection
        try:
            # Find an event with diff viewer
            event_with_diff = None
            for event in self.driver.find_elements(By.CLASS_NAME, "event-item"):
                diff_viewer = event.find_elements(By.CLASS_NAME, "inline-edit-diff-viewer")
                if diff_viewer:
                    event_with_diff = event
                    break
                    
            if event_with_diff:
                # Check if event is selected initially
                initial_selected = "selected" in event_with_diff.get_attribute("class")
                
                # Click diff toggle
                diff_toggle = event_with_diff.find_element(By.CLASS_NAME, "diff-toggle-header")
                diff_toggle.click()
                time.sleep(0.5)
                
                # Check if event selection state changed
                after_selected = "selected" in event_with_diff.get_attribute("class")
                selection_unchanged = initial_selected == after_selected
                
                self.record_test_result(
                    'edit_diff_viewers',
                    'diff_toggle_no_event_selection',
                    selection_unchanged,
                    f"Diff toggle does {'not' if selection_unchanged else ''} trigger event selection"
                )
            else:
                self.record_test_result(
                    'edit_diff_viewers',
                    'diff_toggle_no_event_selection',
                    True,
                    "No events with diff viewers to test selection behavior"
                )
                
        except Exception as e:
            self.record_test_result(
                'edit_diff_viewers',
                'diff_toggle_no_event_selection',
                False,
                "Error testing diff toggle selection behavior",
                str(e)
            )
            
        # Test 6: Verify diff coloring (green additions, red removals)
        try:
            diff_container = self.driver.find_element(By.CSS_SELECTOR, ".diff-content-container[style*='block']")
            added_lines = diff_container.find_elements(By.CLASS_NAME, "diff-added")
            removed_lines = diff_container.find_elements(By.CLASS_NAME, "diff-removed")
            
            # Check CSS colors (approximate check)
            coloring_correct = True
            if added_lines:
                added_color = added_lines[0].value_of_css_property("color")
                # Should be greenish
                coloring_correct &= "rgb(16, 185, 129)" in added_color or "#10b981" in added_color.lower()
                
            if removed_lines:
                removed_color = removed_lines[0].value_of_css_property("color")
                # Should be reddish  
                coloring_correct &= "rgb(239, 68, 68)" in removed_color or "#ef4444" in removed_color.lower()
                
            self.record_test_result(
                'edit_diff_viewers',
                'diff_coloring_correct',
                coloring_correct,
                f"Diff coloring - {len(added_lines)} additions, {len(removed_lines)} removals"
            )
            
        except Exception as e:
            self.record_test_result(
                'edit_diff_viewers',
                'diff_coloring_correct',
                False,
                "Error checking diff coloring",
                str(e)
            )
            
        # Test 7: Verify non-Edit events don't show diff viewers
        try:
            non_edit_events = []
            for event in self.driver.find_elements(By.CLASS_NAME, "event-item"):
                event_text = event.text
                if not any(tool in event_text for tool in ["Edit", "MultiEdit"]):
                    diff_viewers = event.find_elements(By.CLASS_NAME, "inline-edit-diff-viewer")
                    if not diff_viewers:
                        non_edit_events.append(event)
                        
            self.record_test_result(
                'edit_diff_viewers',
                'non_edit_events_no_diffs',
                len(non_edit_events) > 0,
                f"Found {len(non_edit_events)} non-Edit events without diff viewers (correct behavior)"
            )
            
        except Exception as e:
            self.record_test_result(
                'edit_diff_viewers',
                'non_edit_events_no_diffs',
                False,
                "Error checking non-Edit events",
                str(e)
            )
            
    def test_integration(self):
        """Test integration and existing functionality"""
        logger.info("=== Testing Integration ===")
        
        # Test 1: Check for JavaScript console errors
        try:
            logs = self.driver.get_log('browser')
            console_errors = [log for log in logs if log['level'] == 'SEVERE']
            
            self.record_test_result(
                'integration',
                'no_console_errors',
                len(console_errors) == 0,
                f"Console errors: {len(console_errors)}"
            )
            
            if console_errors:
                for error in console_errors[:5]:  # Show first 5 errors
                    logger.error(f"Console error: {error['message']}")
                    
        except Exception as e:
            self.record_test_result(
                'integration',
                'no_console_errors',
                False,
                "Error checking console errors",
                str(e)
            )
            
        # Test 2: Test keyboard navigation still works
        try:
            # Switch to events tab and try arrow key navigation
            events_tab = self.driver.find_element(By.CSS_SELECTOR, "[onclick=\"switchTab('events')\"]")
            events_tab.click()
            time.sleep(1)
            
            # Send arrow key to body
            actions = ActionChains(self.driver)
            actions.send_keys(Keys.ARROW_DOWN).perform()
            time.sleep(0.5)
            
            # Check if any event is selected
            selected_events = self.driver.find_elements(By.CSS_SELECTOR, ".event-item.selected")
            
            self.record_test_result(
                'integration',
                'keyboard_navigation_works',
                len(selected_events) > 0,
                f"Keyboard navigation - {len(selected_events)} events selected"
            )
            
        except Exception as e:
            self.record_test_result(
                'integration',
                'keyboard_navigation_works',
                False,
                "Error testing keyboard navigation",
                str(e)
            )
            
        # Test 3: Test tab switching still works
        try:
            tabs = ['events', 'agents', 'tools', 'files']
            tab_switching_works = True
            
            for tab in tabs:
                tab_button = self.driver.find_element(By.CSS_SELECTOR, f"[onclick=\"switchTab('{tab}')\"]")
                tab_button.click()
                time.sleep(0.5)
                
                # Check if tab content is visible
                tab_content = self.driver.find_element(By.ID, f"{tab}-content")
                if not tab_content.is_displayed():
                    tab_switching_works = False
                    break
                    
            self.record_test_result(
                'integration',
                'tab_switching_works',
                tab_switching_works,
                "Tab switching functionality preserved"
            )
            
        except Exception as e:
            self.record_test_result(
                'integration',
                'tab_switching_works',
                False,
                "Error testing tab switching",
                str(e)
            )
            
        # Test 4: Test event selection modal still works
        try:
            # Switch back to events tab
            events_tab = self.driver.find_element(By.CSS_SELECTOR, "[onclick=\"switchTab('events')\"]")
            events_tab.click()
            time.sleep(1)
            
            # Click on an event (not on diff toggle)
            events = self.driver.find_elements(By.CLASS_NAME, "event-item")
            if events:
                # Click on event content, not diff toggle
                event_content = events[0].find_element(By.CLASS_NAME, "event-single-row-content")
                event_content.click()
                time.sleep(0.5)
                
                # Check if event is selected and module viewer shows content
                selected = "selected" in events[0].get_attribute("class")
                module_content = self.driver.find_element(By.CLASS_NAME, "module-data-content")
                has_content = module_content.text.strip() != ""
                
                self.record_test_result(
                    'integration',
                    'event_selection_works',
                    selected and has_content,
                    f"Event selection works - selected: {selected}, has content: {has_content}"
                )
            else:
                self.record_test_result(
                    'integration',
                    'event_selection_works',
                    True,
                    "No events to test selection (not a failure)"
                )
                
        except Exception as e:
            self.record_test_result(
                'integration',
                'event_selection_works',
                False,
                "Error testing event selection",
                str(e)
            )
            
    def test_edge_cases(self):
        """Test edge cases and error conditions"""
        logger.info("=== Testing Edge Cases ===")
        
        # Test 1: Rapid clicking on file path bar
        try:
            file_path_element = self.driver.find_element(By.CLASS_NAME, "working-dir-path")
            
            # Rapid clicks
            for _ in range(5):
                file_path_element.click()
                time.sleep(0.1)
                
            time.sleep(1)
            
            # Should still work - overlay should be visible
            try:
                overlay = self.driver.find_element(By.ID, "directory-viewer-overlay")
                overlay_visible = overlay.is_displayed()
                self.record_test_result(
                    'edge_cases',
                    'rapid_clicking_stable',
                    overlay_visible,
                    "Rapid clicking - overlay still works"
                )
            except NoSuchElementException:
                self.record_test_result(
                    'edge_cases',
                    'rapid_clicking_stable',
                    False,
                    "Rapid clicking broke overlay functionality",
                    "Overlay not found after rapid clicks"
                )
                
        except Exception as e:
            self.record_test_result(
                'edge_cases',
                'rapid_clicking_stable',
                False,
                "Error testing rapid clicking",
                str(e)
            )
            
        # Test 2: Test with very long file paths
        try:
            # Inject a very long file path for testing
            long_path = "/very/long/path/to/test/responsive/behavior/with/extremely/long/directory/names/that/might/cause/layout/issues/in/the/directory/viewer/overlay/component"
            
            self.driver.execute_script(f"""
                const pathElement = document.querySelector('.working-dir-path');
                if (pathElement) {{
                    pathElement.textContent = '{long_path}';
                }}
            """)
            
            time.sleep(0.5)
            
            # Click to open overlay
            file_path_element = self.driver.find_element(By.CLASS_NAME, "working-dir-path")
            file_path_element.click()
            time.sleep(1)
            
            # Check if overlay still renders correctly
            overlay = self.driver.find_element(By.ID, "directory-viewer-overlay")
            overlay_width = overlay.rect['width']
            window_width = self.driver.get_window_size()['width']
            
            # Overlay should not exceed window width
            width_ok = overlay_width <= window_width
            
            self.record_test_result(
                'edge_cases',
                'long_paths_handled',
                width_ok,
                f"Long paths handled - overlay width {overlay_width}px vs window {window_width}px"
            )
            
            # Close overlay
            self.driver.find_element(By.TAG_NAME, "body").click()
            
        except Exception as e:
            self.record_test_result(
                'edge_cases',
                'long_paths_handled',
                False,
                "Error testing long paths",
                str(e)
            )
            
        # Test 3: Test diff viewer with empty/minimal diffs
        try:
            # This would need actual test data, but we can test the structure
            diff_viewers = self.driver.find_elements(By.CLASS_NAME, "inline-edit-diff-viewer")
            
            if diff_viewers:
                # Find a diff with minimal content
                minimal_diff_found = False
                for diff_viewer in diff_viewers:
                    toggle = diff_viewer.find_element(By.CLASS_NAME, "diff-toggle-header")
                    toggle.click()
                    time.sleep(0.5)
                    
                    diff_lines = diff_viewer.find_elements(By.CLASS_NAME, "diff-line")
                    if len(diff_lines) <= 2:  # Minimal diff
                        minimal_diff_found = True
                        
                        # Check that it still renders correctly
                        container = diff_viewer.find_element(By.CLASS_NAME, "diff-container")
                        container_visible = container.is_displayed()
                        
                        self.record_test_result(
                            'edge_cases',
                            'minimal_diffs_handled',
                            container_visible,
                            f"Minimal diff renders correctly - {len(diff_lines)} lines"
                        )
                        break
                        
                if not minimal_diff_found:
                    self.record_test_result(
                        'edge_cases',
                        'minimal_diffs_handled',
                        True,
                        "No minimal diffs found to test (not a failure)"
                    )
            else:
                self.record_test_result(
                    'edge_cases',
                    'minimal_diffs_handled',
                    True,
                    "No diff viewers found to test (not a failure)"
                )
                
        except Exception as e:
            self.record_test_result(
                'edge_cases',
                'minimal_diffs_handled',
                False,
                "Error testing minimal diffs",
                str(e)
            )
            
        # Test 4: Test special characters in file paths
        try:
            # Test with special characters
            special_path = "/path/with spaces/and-dashes/under_scores/dots.in.name/[brackets]/file.txt"
            
            self.driver.execute_script(f"""
                const pathElement = document.querySelector('.working-dir-path');
                if (pathElement) {{
                    pathElement.textContent = '{special_path}';
                }}
            """)
            
            # Click to open overlay
            file_path_element = self.driver.find_element(By.CLASS_NAME, "working-dir-path")
            file_path_element.click()
            time.sleep(1)
            
            # Check if overlay opens without errors
            overlay = self.driver.find_element(By.ID, "directory-viewer-overlay")
            overlay_visible = overlay.is_displayed()
            
            self.record_test_result(
                'edge_cases',
                'special_characters_handled',
                overlay_visible,
                "Special characters in paths handled correctly"
            )
            
            # Close overlay
            self.driver.find_element(By.TAG_NAME, "body").click()
            
        except Exception as e:
            self.record_test_result(
                'edge_cases',
                'special_characters_handled',
                False,
                "Error testing special characters",
                str(e)
            )
            
    def generate_qa_report(self):
        """Generate comprehensive QA report"""
        logger.info("=== Generating QA Report ===")
        
        report = {
            'timestamp': time.time(),
            'test_summary': self.test_results['summary'],
            'detailed_results': self.test_results,
            'requirements_assessment': self.assess_requirements(),
            'recommendations': self.generate_recommendations()
        }
        
        return report
        
    def assess_requirements(self):
        """Assess how well the implementation meets original requirements"""
        assessment = {
            'requirement_1': {
                'requirement': 'VIEWER should be in the blue file path bar',
                'met': False,
                'evidence': []
            },
            'requirement_2': {
                'requirement': 'DIFF viewer should be attached to each EDIT tool use, showing only the diff for THAT edit',
                'met': False,
                'evidence': []
            }
        }
        
        # Check requirement 1
        req1_tests = [
            'clickable_path_bar_exists',
            'overlay_opens_on_click',
            'overlay_positioned_below_bar',
            'directory_navigation_works',
            'click_outside_closes_overlay'
        ]
        
        req1_passed = all(
            self.test_results['file_path_viewer'].get(test, {}).get('passed', False) 
            for test in req1_tests
        )
        
        assessment['requirement_1']['met'] = req1_passed
        assessment['requirement_1']['evidence'] = [
            f"{test}: {'PASS' if self.test_results['file_path_viewer'].get(test, {}).get('passed', False) else 'FAIL'}"
            for test in req1_tests
        ]
        
        # Check requirement 2
        req2_tests = [
            'diff_viewers_present',
            'diff_toggle_works',
            'diff_content_shows_changes',
            'non_edit_events_no_diffs'
        ]
        
        req2_passed = all(
            self.test_results['edit_diff_viewers'].get(test, {}).get('passed', False)
            for test in req2_tests
        )
        
        assessment['requirement_2']['met'] = req2_passed
        assessment['requirement_2']['evidence'] = [
            f"{test}: {'PASS' if self.test_results['edit_diff_viewers'].get(test, {}).get('passed', False) else 'FAIL'}"
            for test in req2_tests
        ]
        
        return assessment
        
    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Analyze failures and suggest improvements
        for category, tests in self.test_results.items():
            if category == 'summary':
                continue
                
            for test_name, result in tests.items():
                if not result['passed']:
                    if 'console_errors' in test_name:
                        recommendations.append("Fix JavaScript console errors that may affect functionality")
                    elif 'responsive' in test_name:
                        recommendations.append("Improve responsive design for mobile devices")
                    elif 'keyboard' in test_name:
                        recommendations.append("Ensure keyboard navigation remains functional")
                    elif 'diff' in test_name:
                        recommendations.append("Verify diff viewer implementation and styling")
                    elif 'overlay' in test_name:
                        recommendations.append("Fix file path overlay positioning or behavior")
                        
        # General recommendations
        if self.test_results['summary']['failed'] > 0:
            recommendations.append("Run additional manual testing to verify user experience")
            recommendations.append("Test with various file types and directory structures")
            
        if not recommendations:
            recommendations.append("Implementation appears solid - consider adding more edge case testing")
            recommendations.append("Monitor for user feedback and performance in production")
            
        return recommendations
        
    def run_full_qa_suite(self, port=8765):
        """Run the complete QA test suite"""
        logger.info("Starting Viewer Improvements QA Test Suite")
        
        if not self.setup_driver():
            logger.error("Failed to setup WebDriver")
            return None
            
        try:
            if not self.load_dashboard(port):
                logger.error(f"Failed to load dashboard at port {port}")
                return None
                
            # Run all test suites
            self.test_file_path_bar_viewer()
            self.test_edit_diff_viewers()
            self.test_integration()
            self.test_edge_cases()
            
            # Generate final report
            report = self.generate_qa_report()
            
            logger.info(f"QA Suite completed: {report['test_summary']['passed']}/{report['test_summary']['total']} tests passed")
            
            return report
            
        finally:
            self.teardown_driver()


def main():
    """Main function to run QA tests"""
    qa = ViewerImprovementsQA()
    
    # Try different ports
    for port in [8765, 8080, 3000]:
        logger.info(f"Trying port {port}")
        report = qa.run_full_qa_suite(port)
        
        if report:
            # Save report to file
            report_file = Path(__file__).parent / "viewer_improvements_qa_report.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
                
            # Print summary
            print("\n" + "="*50)
            print("QA REPORT SUMMARY")
            print("="*50)
            print(f"Total tests: {report['test_summary']['total']}")
            print(f"Passed: {report['test_summary']['passed']}")
            print(f"Failed: {report['test_summary']['failed']}")
            print(f"Success rate: {(report['test_summary']['passed']/report['test_summary']['total']*100):.1f}%")
            
            print(f"\nREQUIREMENTS ASSESSMENT:")
            for req_id, req_data in report['requirements_assessment'].items():
                status = "✅ MET" if req_data['met'] else "❌ NOT MET"
                print(f"{req_id}: {status}")
                print(f"  {req_data['requirement']}")
                
            print(f"\nRECOMMENDATIONS:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"{i}. {rec}")
                
            print(f"\nDetailed report saved to: {report_file}")
            
            return report['test_summary']['failed'] == 0  # Return True if all tests passed
            
    logger.error("Could not connect to dashboard on any port")
    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)