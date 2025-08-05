#!/usr/bin/env python3
"""
Component-level testing for HUD functionality.
Tests specific components and edge cases.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

class HUDComponentTester:
    """Test HUD components in detail."""
    
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
    
    def test_cytoscape_initialization(self):
        """Test Cytoscape.js initialization code."""
        print("\n🔬 Testing Cytoscape.js initialization...")
        
        hud_js = project_root / "src/claude_mpm/web/static/js/components/hud-visualizer.js"
        if not hud_js.exists():
            self.log_test("Cytoscape Initialization", "FAIL", "HUD visualizer file not found")
            return
        
        content = hud_js.read_text()
        
        # Check initialization logic
        init_checks = [
            "initializeCytoscape()",
            "cytoscape.use(cytoscapeDagre)",
            "cytoscape({",
            "container: this.container",
            "elements: []",
            "style: [",
            "layout: this.layoutConfig"
        ]
        
        for check in init_checks:
            if check in content:
                self.log_test(f"Init Check: {check}", "PASS")
            else:
                self.log_test(f"Init Check: {check}", "FAIL", "Initialization code missing")
    
    def test_node_style_definitions(self):
        """Test that node styles are properly defined."""
        print("\n🎨 Testing node style definitions...")
        
        hud_js = project_root / "src/claude_mpm/web/static/js/components/hud-visualizer.js"
        content = hud_js.read_text()
        
        # Check for style selectors
        style_selectors = [
            "selector: 'node'",
            "selector: 'edge'", 
            "selector: '.pm-node'",
            "selector: '.agent-node'",
            "selector: '.tool-node'",
            "selector: '.todo-node'",
            "selector: 'node:active'"
        ]
        
        for selector in style_selectors:
            if selector in content:
                self.log_test(f"Style Selector: {selector}", "PASS")
            else:
                self.log_test(f"Style Selector: {selector}", "FAIL", "Style selector missing")
        
        # Check for essential style properties
        style_properties = [
            "'background-color': 'data(color)'",
            "'border-color': 'data(borderColor)'",
            "'label': 'data(label)'",
            "'shape': 'data(shape)'",
            "'width': 'data(width)'",
            "'height': 'data(height)'"
        ]
        
        for prop in style_properties:
            if prop in content:
                self.log_test(f"Style Property: {prop}", "PASS")
            else:
                self.log_test(f"Style Property: {prop}", "FAIL", "Style property missing")
    
    def test_event_relationship_logic(self):
        """Test event relationship creation logic."""
        print("\n🔗 Testing event relationship logic...")
        
        hud_js = project_root / "src/claude_mpm/web/static/js/components/hud-visualizer.js"
        content = hud_js.read_text()
        
        # Check relationship patterns
        relationship_patterns = [
            "tool_call",
            "agent",  
            "todo",
            "findParentNode(",
            "addEdge(",
            "sessionId === sessionId",
            "nodeTypes.includes("
        ]
        
        for pattern in relationship_patterns:
            if pattern in content:
                self.log_test(f"Relationship Pattern: {pattern}", "PASS")
            else:
                self.log_test(f"Relationship Pattern: {pattern}", "FAIL", "Pattern missing")
    
    def test_resize_handling(self):
        """Test that resize handling is properly implemented."""
        print("\n📏 Testing resize handling...")
        
        hud_js = project_root / "src/claude_mpm/web/static/js/components/hud-visualizer.js"
        content = hud_js.read_text()
        
        resize_checks = [
            "ResizeObserver",
            "setupResizeHandler",
            "this.cy.resize()",
            "this.cy.fit()",
            "resizeObserver.observe"
        ]
        
        for check in resize_checks:
            if check in content:
                self.log_test(f"Resize Check: {check}", "PASS")
            else:
                self.log_test(f"Resize Check: {check}", "FAIL", "Resize handling missing")
    
    def test_node_interaction(self):
        """Test node interaction handling."""
        print("\n🖱️ Testing node interaction...")
        
        hud_js = project_root / "src/claude_mpm/web/static/js/components/hud-visualizer.js"
        content = hud_js.read_text()
        
        interaction_checks = [
            "this.cy.on('tap', 'node'",
            "highlightConnectedNodes(",
            "node.neighborhood()",
            "style('opacity'",
            "addEventListener('click'"
        ]
        
        for check in interaction_checks:
            if check in content:
                self.log_test(f"Interaction Check: {check}", "PASS")
            else:
                self.log_test(f"Interaction Check: {check}", "FAIL", "Interaction handling missing")
    
    def test_layout_controls(self):
        """Test layout control functionality."""
        print("\n🎛️ Testing layout controls...")
        
        hud_js = project_root / "src/claude_mpm/web/static/js/components/hud-visualizer.js"
        content = hud_js.read_text()
        
        control_checks = [
            "hud-reset-layout",
            "hud-center-view", 
            "resetLayout()",
            "centerView()",
            "this.cy.layout(",
            "this.cy.fit()",
            "this.cy.center()"
        ]
        
        for check in control_checks:
            if check in content:
                self.log_test(f"Control Check: {check}", "PASS")
            else:
                self.log_test(f"Control Check: {check}", "FAIL", "Control functionality missing")
    
    def test_session_integration(self):
        """Test session management integration."""
        print("\n📋 Testing session integration...")
        
        dashboard_js = project_root / "src/claude_mpm/web/static/js/dashboard.js"  
        content = dashboard_js.read_text()
        
        session_checks = [
            "updateHUDButtonState",
            "selectedSession",
            "hudToggleBtn.disabled",
            "Select a session to enable HUD",
            "Toggle HUD visualizer"
        ]
        
        for check in session_checks:
            if check in content:
                self.log_test(f"Session Check: {check}", "PASS")
            else:
                self.log_test(f"Session Check: {check}", "FAIL", "Session integration missing")
    
    def test_performance_optimizations(self):
        """Test performance optimization features."""
        print("\n⚡ Testing performance optimizations...")
        
        hud_js = project_root / "src/claude_mpm/web/static/js/components/hud-visualizer.js"
        content = hud_js.read_text()
        
        perf_checks = [
            "if (!this.isActive)",
            "nodes.has(id)",
            "return;", 
            "Map(",
            "setTimeout("
        ]
        
        for check in perf_checks:
            if check in content:
                self.log_test(f"Performance Check: {check}", "PASS")
            else:
                self.log_test(f"Performance Check: {check}", "FAIL", "Performance optimization missing")
    
    def test_error_handling(self):
        """Test error handling in HUD components."""
        print("\n🛡️ Testing error handling...")
        
        hud_js = project_root / "src/claude_mpm/web/static/js/components/hud-visualizer.js"
        content = hud_js.read_text()
        
        error_checks = [
            "if (!this.container)",
            "console.error(",
            "return false",
            "try {",
            "} catch"
        ]
        
        error_found = any(check in content for check in error_checks)
        if error_found:
            self.log_test("Error Handling", "PASS", "Error handling patterns found")
        else:
            self.log_test("Error Handling", "WARN", "Limited error handling detected")
    
    def test_memory_management(self):
        """Test memory management practices."""
        print("\n🧠 Testing memory management...")
        
        hud_js = project_root / "src/claude_mpm/web/static/js/components/hud-visualizer.js"
        content = hud_js.read_text()
        
        memory_checks = [
            "clear()",
            "nodes.clear()",
            "this.cy.elements().remove()",
            "deactivate()",
            "this.isActive = false"
        ]
        
        for check in memory_checks:
            if check in content:
                self.log_test(f"Memory Check: {check}", "PASS")
            else:
                self.log_test(f"Memory Check: {check}", "FAIL", "Memory management missing")
    
    def test_color_utilities(self):
        """Test color utility functions."""
        print("\n🌈 Testing color utilities...")
        
        hud_js = project_root / "src/claude_mpm/web/static/js/components/hud-visualizer.js"
        content = hud_js.read_text()
        
        color_checks = [
            "darkenColor(",
            "parseInt(color.replace",
            "Math.round(",
            "toString(16)"
        ]
        
        for check in color_checks:
            if check in content:
                self.log_test(f"Color Check: {check}", "PASS")
            else:
                self.log_test(f"Color Check: {check}", "FAIL", "Color utility missing")
    
    def run_all_tests(self):
        """Run all component tests."""
        print("🧪 Starting HUD component testing...")
        print("="*60)
        
        self.test_cytoscape_initialization()
        self.test_node_style_definitions()
        self.test_event_relationship_logic()
        self.test_resize_handling()
        self.test_node_interaction()
        self.test_layout_controls()
        self.test_session_integration()
        self.test_performance_optimizations()
        self.test_error_handling()
        self.test_memory_management()
        self.test_color_utilities()
        
        self.generate_report()
    
    def generate_report(self):
        """Generate component test report."""
        print("\n" + "="*60)
        print("📊 HUD COMPONENT TEST REPORT")
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
        report_file = project_root / "HUD_COMPONENT_TEST_REPORT.json"
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
    """Run HUD component tests."""
    tester = HUDComponentTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All component tests passed!")
        return True
    else:
        print("\n⚠️ Some component tests failed.")
        return False

if __name__ == "__main__":
    main()