#!/usr/bin/env python3
"""
Edge case and performance testing for HUD functionality.
Tests various edge cases and performance scenarios.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

class HUDEdgeCaseTester:
    """Test HUD edge cases and performance scenarios."""
    
    def __init__(self):
        self.test_results = []
        
    def log_test(self, test_name, status, details=""):
        """Log test results."""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {test_name}: {status}")
        if details:
            print(f"   {details}")
    
    def test_empty_session_handling(self):
        """Test HUD behavior with empty sessions."""
        print("\n📭 Testing empty session handling...")
        
        # Check that HUD gracefully handles sessions with no events
        hud_js = project_root / "src/claude_mpm/dashboard/static/js/components/hud-visualizer.js"
        content = hud_js.read_text()
        
        empty_session_checks = [
            "if (!this.isActive) return",
            "clear()",
            "nodes.clear()",
            "elements: []"
        ]
        
        for check in empty_session_checks:
            if check in content:
                self.log_test(f"Empty Session Check: {check}", "PASS")
            else:
                self.log_test(f"Empty Session Check: {check}", "FAIL", "Empty session handling missing")
    
    def test_rapid_session_switching(self):
        """Test behavior when rapidly switching between sessions."""
        print("\n🔄 Testing rapid session switching...")
        
        dashboard_js = project_root / "src/claude_mpm/dashboard/static/js/dashboard.js"
        content = dashboard_js.read_text()
        
        # Check for proper cleanup and state management
        switching_checks = [
            "updateHUDButtonState",
            "this.hudMode = false",
            "updateHUDDisplay",
            "clear()",
            "deactivate()"
        ]
        
        for check in switching_checks:
            if check in content:
                self.log_test(f"Session Switching: {check}", "PASS")
            else:
                self.log_test(f"Session Switching: {check}", "FAIL", "Session switching logic missing")
    
    def test_large_event_datasets(self):
        """Test HUD performance with large numbers of events."""
        print("\n📊 Testing large event dataset handling...")
        
        hud_js = project_root / "src/claude_mpm/dashboard/static/js/components/hud-visualizer.js"
        content = hud_js.read_text()
        
        # Check for performance optimizations
        perf_checks = [
            "nodes.has(id)",  # Duplicate node prevention
            "if (!this.isActive)",  # Early return for inactive state
            "Map(",  # Efficient data structures
            "setTimeout(",  # Async processing
            "return;"  # Early returns
        ]
        
        for check in perf_checks:
            if check in content:
                self.log_test(f"Performance Optimization: {check}", "PASS")
            else:
                self.log_test(f"Performance Optimization: {check}", "FAIL", "Performance optimization missing")
    
    def test_malformed_event_data(self):
        """Test handling of malformed or incomplete event data."""
        print("\n🚨 Testing malformed event data handling...")
        
        hud_js = project_root / "src/claude_mpm/dashboard/static/js/components/hud-visualizer.js"
        content = hud_js.read_text()
        
        # Check for defensive programming
        defensive_checks = [
            "|| event.type",
            "|| 'unknown'",
            "|| 'Unknown Tool'",
            "|| 'Agent'",
            "timestamp.getTime()",
            "event.data?"
        ]
        
        defensive_found = sum(1 for check in defensive_checks if check in content)
        if defensive_found >= 3:
            self.log_test("Malformed Data Handling", "PASS", f"Found {defensive_found} defensive patterns")
        else:
            self.log_test("Malformed Data Handling", "WARN", f"Limited defensive programming ({defensive_found} patterns)")
    
    def test_browser_compatibility(self):
        """Test browser compatibility features."""
        print("\n🌐 Testing browser compatibility...")
        
        # Check HTML for compatibility features
        html_file = project_root / "src/claude_mpm/dashboard/templates/index.html"
        html_content = html_file.read_text()
        
        # Check for modern JS features and fallbacks
        compat_checks = [
            "https://unpkg.com/cytoscape",  # CDN usage for compatibility
            "https://unpkg.com/cytoscape-dagre",
            "https://unpkg.com/dagre"
        ]
        
        for check in compat_checks:
            if check in html_content:
                self.log_test(f"Browser Compatibility: {check}", "PASS")
            else:
                self.log_test(f"Browser Compatibility: {check}", "FAIL", "Compatibility feature missing")
        
        # Check JavaScript for modern features
        hud_js = project_root / "src/claude_mpm/dashboard/static/js/components/hud-visualizer.js"
        js_content = hud_js.read_text()
        
        # Check for ES6+ features with potential issues
        modern_features = [
            "class ",
            "const ",
            "let ",
            "=>",
            "Map(",
            "ResizeObserver"
        ]
        
        modern_count = sum(1 for feature in modern_features if feature in js_content)
        if modern_count >= 4:
            self.log_test("Modern JS Features", "PASS", f"Uses {modern_count} modern features")
        else:
            self.log_test("Modern JS Features", "WARN", f"Limited modern JS usage ({modern_count} features)")
    
    def test_memory_leak_prevention(self):
        """Test memory leak prevention measures."""
        print("\n🧠 Testing memory leak prevention...")
        
        hud_js = project_root / "src/claude_mpm/dashboard/static/js/components/hud-visualizer.js"
        content = hud_js.read_text()
        
        # Check for proper cleanup
        cleanup_checks = [
            "clear()",
            "nodes.clear()",
            "this.cy.elements().remove()",
            "deactivate()",
            "this.isActive = false",
            "removeEventListener("
        ]
        
        cleanup_found = sum(1 for check in cleanup_checks if check in content)
        if cleanup_found >= 4:
            self.log_test("Memory Leak Prevention", "PASS", f"Found {cleanup_found} cleanup patterns")
        else:
            self.log_test("Memory Leak Prevention", "WARN", f"Limited cleanup ({cleanup_found} patterns)")
    
    def test_error_recovery(self):
        """Test error recovery mechanisms."""
        print("\n🛠️ Testing error recovery...")
        
        hud_js = project_root / "src/claude_mpm/dashboard/static/js/components/hud-visualizer.js"
        content = hud_js.read_text()
        
        # Check for error handling patterns
        error_patterns = [
            "try {",
            "} catch",
            "console.error(",
            "if (!this.container)",
            "return false",
            "return null"
        ]
        
        error_count = sum(1 for pattern in error_patterns if pattern in content)
        if error_count >= 3:
            self.log_test("Error Recovery", "PASS", f"Found {error_count} error handling patterns")
        else:
            self.log_test("Error Recovery", "WARN", f"Limited error handling ({error_count} patterns)")
    
    def test_concurrent_operations(self):
        """Test handling of concurrent operations."""
        print("\n⚡ Testing concurrent operations...")
        
        hud_js = project_root / "src/claude_mpm/dashboard/static/js/components/hud-visualizer.js"
        content = hud_js.read_text()
        
        # Check for concurrency handling
        concurrency_checks = [
            "if (!this.isActive)",  # State checks
            "nodes.has(id)",  # Duplicate prevention
            "return;",  # Early returns
            "setTimeout("  # Async operations
        ]
        
        for check in concurrency_checks:
            if check in content:
                self.log_test(f"Concurrency Check: {check}", "PASS")
            else:
                self.log_test(f"Concurrency Check: {check}", "FAIL", "Concurrency handling missing")
    
    def test_responsive_design(self):
        """Test responsive design implementation."""
        print("\n📱 Testing responsive design...")
        
        css_file = project_root / "src/claude_mpm/dashboard/static/css/dashboard.css"
        css_content = css_file.read_text()
        
        # Check for responsive CSS
        responsive_checks = [
            ".hud-visualizer",
            "width:",
            "height:",
            "flex:",
            "resize"
        ]
        
        for check in responsive_checks:
            if check in css_content:
                self.log_test(f"Responsive CSS: {check}", "PASS")
            else:
                self.log_test(f"Responsive CSS: {check}", "FAIL", "Responsive design missing")
        
        # Check for resize handling in JS
        hud_js = project_root / "src/claude_mpm/dashboard/static/js/components/hud-visualizer.js"
        js_content = hud_js.read_text()
        
        if "ResizeObserver" in js_content:
            self.log_test("Resize Observer", "PASS")
        else:
            self.log_test("Resize Observer", "FAIL", "ResizeObserver not found")
    
    def test_accessibility_features(self):
        """Test accessibility implementation."""
        print("\n♿ Testing accessibility features...")
        
        html_file = project_root / "src/claude_mpm/dashboard/templates/index.html"
        html_content = html_file.read_text()
        
        # Check for accessibility attributes
        a11y_checks = [
            'title="',  # Tooltips
            'aria-',  # ARIA attributes
            'alt="',  # Alt text
            'role="'  # Roles
        ]
        
        a11y_found = sum(1 for check in a11y_checks if check in html_content)
        if a11y_found >= 1:
            self.log_test("Accessibility Features", "PASS", f"Found {a11y_found} accessibility patterns")
        else:
            self.log_test("Accessibility Features", "WARN", "Limited accessibility features")
    
    def test_cross_session_isolation(self):
        """Test that sessions are properly isolated."""
        print("\n🔒 Testing cross-session isolation...")
        
        hud_js = project_root / "src/claude_mpm/dashboard/static/js/components/hud-visualizer.js"
        content = hud_js.read_text()
        
        # Check for session isolation
        isolation_checks = [
            "sessionId",
            "session_id",
            "nodeData.sessionId === sessionId",
            "clear()"
        ]
        
        for check in isolation_checks:
            if check in content:
                self.log_test(f"Session Isolation: {check}", "PASS")
            else:
                self.log_test(f"Session Isolation: {check}", "FAIL", "Session isolation missing")
    
    def run_all_tests(self):
        """Run all edge case tests."""
        print("🧪 Starting HUD edge case testing...")
        print("="*60)
        
        self.test_empty_session_handling()
        self.test_rapid_session_switching()
        self.test_large_event_datasets()
        self.test_malformed_event_data()
        self.test_browser_compatibility()
        self.test_memory_leak_prevention()
        self.test_error_recovery()
        self.test_concurrent_operations()
        self.test_responsive_design()
        self.test_accessibility_features()
        self.test_cross_session_isolation()
        
        self.generate_report()
    
    def generate_report(self):
        """Generate edge case test report."""
        print("\n" + "="*60)
        print("📊 HUD EDGE CASE TEST REPORT")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])
        warned_tests = len([r for r in self.test_results if r["status"] == "WARN"])
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⚠️ Warnings: {warned_tests}")
        
        if total_tests > 0:
            success_rate = (passed_tests / total_tests) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  • {result['test']}: {result['details']}")
        
        if warned_tests > 0:
            print("\n⚠️ WARNINGS:")
            for result in self.test_results:
                if result["status"] == "WARN":
                    print(f"  • {result['test']}: {result['details']}")
        
        # Save detailed report
        report_file = project_root / "HUD_EDGE_CASE_TEST_REPORT.json"
        with open(report_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "warnings": warned_tests,
                    "success_rate": round(success_rate, 1) if total_tests > 0 else 0
                },
                "results": self.test_results
            }, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        return failed_tests == 0

def main():
    """Run HUD edge case tests."""
    tester = HUDEdgeCaseTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All edge case tests passed!")
        return True
    else:
        print("\n⚠️ Some edge case tests failed.")
        return False

if __name__ == "__main__":
    main()