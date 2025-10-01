#!/usr/bin/env python3
"""
Comprehensive Test Suite Runner for Code Analysis Dashboard
=========================================================

WHY: Orchestrates all the individual test modules to provide a complete
validation of the code analysis functionality. Generates a comprehensive
report covering all aspects of the testing.

DESIGN DECISIONS:
- Run all test modules in logical order
- Collect and aggregate results
- Generate detailed HTML and JSON reports
- Provide clear pass/fail status for each component
- Include performance metrics and recommendations
- Support different test configurations
"""

import argparse
import asyncio
import importlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from test_code_analysis_browser import CodeAnalysisBrowserTest
from test_code_analysis_performance import CodeAnalysisPerformanceTest

# Import test modules
from test_code_analysis_socketio_client import CodeAnalysisSocketIOTest
from test_code_event_flow import CompleteEventFlowTest
from test_event_format_validation import EventFormatValidator


class ComprehensiveTestRunner:
    """Orchestrates and runs all code analysis tests."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the test runner.

        Args:
            config: Test configuration dictionary
        """
        self.config = config
        self.results = {}
        self.start_time = None
        self.end_time = None

        # Test execution order
        self.test_modules = [
            (
                "event_format_validation",
                "Event Format Validation",
                self.run_event_format_tests,
            ),
            (
                "performance_tests",
                "Performance & Error Tests",
                self.run_performance_tests,
            ),
            ("socketio_client", "Socket.IO Client Tests", self.run_socketio_tests),
            ("browser_automation", "Browser Automation Tests", self.run_browser_tests),
            (
                "complete_event_flow",
                "Complete Event Flow Tests",
                self.run_complete_flow_tests,
            ),
        ]

    async def run_event_format_tests(self) -> Dict[str, Any]:
        """Run event format validation tests."""
        print("\n" + "=" * 60)
        print("🔍 RUNNING EVENT FORMAT VALIDATION TESTS")
        print("=" * 60)

        try:
            validator = EventFormatValidator()
            results = validator.run_validation_suite()

            return {
                "module": "event_format_validation",
                "success": results.get("suite_success", False),
                "execution_time": results.get("total_time", 0),
                "details": results,
            }
        except Exception as e:
            return {
                "module": "event_format_validation",
                "success": False,
                "execution_time": 0,
                "error": str(e),
            }

    async def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance and error scenario tests."""
        print("\n" + "=" * 60)
        print("⚡ RUNNING PERFORMANCE & ERROR TESTS")
        print("=" * 60)

        try:
            tester = CodeAnalysisPerformanceTest()
            results = tester.run_performance_test_suite()

            return {
                "module": "performance_tests",
                "success": results.get("suite_success", False),
                "execution_time": results.get("total_time", 0),
                "details": results,
            }
        except Exception as e:
            return {
                "module": "performance_tests",
                "success": False,
                "execution_time": 0,
                "error": str(e),
            }

    async def run_socketio_tests(self) -> Dict[str, Any]:
        """Run Socket.IO client tests."""
        print("\n" + "=" * 60)
        print("📡 RUNNING SOCKET.IO CLIENT TESTS")
        print("=" * 60)

        try:
            # Check if we should skip if no server is available
            if not self.config.get("run_server_dependent_tests", True):
                return {
                    "module": "socketio_client",
                    "success": True,
                    "execution_time": 0,
                    "skipped": True,
                    "reason": "Server-dependent tests disabled in config",
                }

            dashboard_url = self.config.get("dashboard_url", "http://localhost:8765")
            tester = CodeAnalysisSocketIOTest(dashboard_url)
            results = await tester.run_full_test_suite()

            return {
                "module": "socketio_client",
                "success": results.get("suite_success", False),
                "execution_time": results.get("total_time", 0),
                "details": results,
            }
        except Exception as e:
            return {
                "module": "socketio_client",
                "success": False,
                "execution_time": 0,
                "error": str(e),
            }

    async def run_browser_tests(self) -> Dict[str, Any]:
        """Run browser automation tests."""
        print("\n" + "=" * 60)
        print("🌐 RUNNING BROWSER AUTOMATION TESTS")
        print("=" * 60)

        try:
            # Check if we should skip browser tests
            if not self.config.get("run_browser_tests", True):
                return {
                    "module": "browser_automation",
                    "success": True,
                    "execution_time": 0,
                    "skipped": True,
                    "reason": "Browser tests disabled in config",
                }

            dashboard_url = self.config.get("dashboard_url", "http://localhost:8765")
            browsers = self.config.get("browsers", ["chrome"])
            headless = self.config.get("headless", True)

            tester = CodeAnalysisBrowserTest(dashboard_url)
            results = await tester.run_full_test_suite(browsers, headless)

            return {
                "module": "browser_automation",
                "success": results.get("overall_success", False),
                "execution_time": results.get("total_time", 0),
                "details": results,
            }
        except Exception as e:
            return {
                "module": "browser_automation",
                "success": False,
                "execution_time": 0,
                "error": str(e),
            }

    async def run_complete_flow_tests(self) -> Dict[str, Any]:
        """Run complete event flow tests."""
        print("\n" + "=" * 60)
        print("🔄 RUNNING COMPLETE EVENT FLOW TESTS")
        print("=" * 60)

        try:
            # Check if we should skip integration tests
            if not self.config.get("run_integration_tests", True):
                return {
                    "module": "complete_event_flow",
                    "success": True,
                    "execution_time": 0,
                    "skipped": True,
                    "reason": "Integration tests disabled in config",
                }

            port = self.config.get("dashboard_port", 8765)
            timeout = self.config.get("dashboard_timeout", 30)

            tester = CompleteEventFlowTest(port, timeout)
            results = await tester.run_complete_event_flow_test()

            return {
                "module": "complete_event_flow",
                "success": results.get("suite_success", False),
                "execution_time": results.get("total_time", 0),
                "details": results,
            }
        except Exception as e:
            return {
                "module": "complete_event_flow",
                "success": False,
                "execution_time": 0,
                "error": str(e),
            }

    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are available."""
        print("🔍 Checking dependencies...")

        dependencies = {
            "socketio": True,  # python-socketio
            "selenium": True,  # selenium
            "psutil": True,  # psutil for performance tests
            "requests": True,  # requests for HTTP checks
        }

        for dep in dependencies:
            try:
                importlib.import_module(dep)
                print(f"✅ {dep} available")
            except ImportError:
                print(f"❌ {dep} not available")
                dependencies[dep] = False

        # Check for Chrome/Firefox drivers
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options as ChromeOptions

            chrome_options = ChromeOptions()
            chrome_options.add_argument("--headless")
            driver = webdriver.Chrome(options=chrome_options)
            driver.quit()
            print("✅ Chrome WebDriver available")
            dependencies["chrome_driver"] = True
        except Exception:
            print("❌ Chrome WebDriver not available")
            dependencies["chrome_driver"] = False

        return dependencies

    def generate_html_report(self, results: Dict[str, Any]) -> str:
        """Generate an HTML report of test results."""
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Analysis Dashboard Test Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }}
        .header h1 {{ margin: 0; font-size: 2.5em; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        .summary {{ padding: 30px; border-bottom: 1px solid #eee; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 20px; }}
        .summary-card {{ background: #f8f9ff; border-left: 4px solid #667eea; padding: 20px; border-radius: 4px; }}
        .summary-card h3 {{ margin: 0 0 10px 0; color: #333; }}
        .summary-card .value {{ font-size: 2em; font-weight: bold; color: #667eea; }}
        .success {{ color: #4caf50; }}
        .failure {{ color: #f44336; }}
        .test-module {{ margin: 20px 30px; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }}
        .test-module h3 {{ margin-top: 0; color: #333; }}
        .status-badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; color: white; font-weight: bold; margin-left: 10px; }}
        .status-pass {{ background-color: #4caf50; }}
        .status-fail {{ background-color: #f44336; }}
        .status-skip {{ background-color: #ff9800; }}
        .details {{ margin-top: 15px; }}
        .details summary {{ cursor: pointer; font-weight: bold; padding: 5px 0; }}
        .details[open] summary {{ border-bottom: 1px solid #ddd; margin-bottom: 10px; }}
        .metric {{ display: flex; justify-content: space-between; padding: 5px 0; }}
        .recommendations {{ background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 15px; margin: 20px 30px; }}
        .recommendations h3 {{ color: #856404; margin-top: 0; }}
        .footer {{ text-align: center; padding: 20px; color: #666; border-top: 1px solid #eee; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 Code Analysis Dashboard Test Report</h1>
            <p>Comprehensive testing results for event format fixes and dashboard functionality</p>
            <p>Generated on {timestamp}</p>
        </div>
        
        <div class="summary">
            <h2>Test Summary</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <h3>Overall Status</h3>
                    <div class="value {overall_status_class}">{overall_status}</div>
                </div>
                <div class="summary-card">
                    <h3>Modules Tested</h3>
                    <div class="value">{modules_tested}</div>
                </div>
                <div class="summary-card">
                    <h3>Tests Passed</h3>
                    <div class="value success">{tests_passed}</div>
                </div>
                <div class="summary-card">
                    <h3>Total Time</h3>
                    <div class="value">{total_time}s</div>
                </div>
            </div>
        </div>
        
        {module_results}
        
        {recommendations}
        
        <div class="footer">
            <p>Report generated by Claude MPM Comprehensive Test Suite</p>
            <p>For technical support, check the documentation or create an issue on GitHub</p>
        </div>
    </div>
</body>
</html>
"""

        # Calculate summary statistics
        total_modules = len(
            [r for r in results["test_results"] if not r.get("skipped", False)]
        )
        passed_modules = len(
            [
                r
                for r in results["test_results"]
                if r.get("success", False) and not r.get("skipped", False)
            ]
        )
        overall_status = "PASSED" if results["overall_success"] else "FAILED"
        overall_status_class = "success" if results["overall_success"] else "failure"

        # Generate module results HTML
        module_html = ""
        for result in results["test_results"]:
            module_name = result.get("module", "Unknown")
            success = result.get("success", False)
            skipped = result.get("skipped", False)

            if skipped:
                status_badge = '<span class="status-badge status-skip">SKIPPED</span>'
                status_text = f"Skipped: {result.get('reason', 'No reason provided')}"
            elif success:
                status_badge = '<span class="status-badge status-pass">PASSED</span>'
                status_text = (
                    f"Completed successfully in {result.get('execution_time', 0):.2f}s"
                )
            else:
                status_badge = '<span class="status-badge status-fail">FAILED</span>'
                error = result.get("error", "Unknown error")
                status_text = f"Failed: {error}"

            # Generate details if available
            details_html = ""
            if "details" in result and not skipped:
                details = result["details"]
                details_html = f"""
                <details class="details">
                    <summary>View Details</summary>
                    <div class="metric">
                        <span>Execution Time:</span>
                        <span>{result.get('execution_time', 0):.2f}s</span>
                    </div>
                """

                # Add specific metrics based on module type
                if (
                    module_name == "performance_tests"
                    and "performance_metrics" in details
                ):
                    metrics = details["performance_metrics"]
                    details_html += f"""
                    <div class="metric">
                        <span>Avg Throughput:</span>
                        <span>{metrics.get('avg_throughput_eps', 0):.1f} events/sec</span>
                    </div>
                    <div class="metric">
                        <span>Max Memory Usage:</span>
                        <span>{metrics.get('max_memory_usage_mb', 0):.1f} MB</span>
                    </div>
                    """
                elif module_name == "socketio_client" and "event_statistics" in details:
                    event_count = len(details.get("event_statistics", {}))
                    details_html += f"""
                    <div class="metric">
                        <span>Event Types Received:</span>
                        <span>{event_count}</span>
                    </div>
                    """
                elif (
                    module_name == "browser_automation" and "browser_results" in details
                ):
                    browser_results = details["browser_results"]
                    for browser_result in browser_results:
                        browser = browser_result.get("browser", "Unknown")
                        browser_success = browser_result.get("suite_success", False)
                        browser_status = "✅" if browser_success else "❌"
                        details_html += f"""
                        <div class="metric">
                            <span>{browser.title()} Browser:</span>
                            <span>{browser_status}</span>
                        </div>
                        """

                details_html += "</details>"

            module_html += f"""
            <div class="test-module">
                <h3>{module_name.replace('_', ' ').title()}{status_badge}</h3>
                <p>{status_text}</p>
                {details_html}
            </div>
            """

        # Generate recommendations
        recommendations_html = ""
        recommendations = []

        # Check for common issues and generate recommendations
        failed_modules = [
            r
            for r in results["test_results"]
            if not r.get("success", True) and not r.get("skipped", False)
        ]

        if failed_modules:
            recommendations.append(
                "❌ Some test modules failed. Review the detailed error messages above."
            )

        performance_result = next(
            (
                r
                for r in results["test_results"]
                if r.get("module") == "performance_tests"
            ),
            None,
        )
        if performance_result and performance_result.get("success", False):
            perf_details = performance_result.get("details", {})
            perf_metrics = perf_details.get("performance_metrics", {})
            if perf_metrics.get("avg_throughput_eps", 0) < 50:
                recommendations.append(
                    "⚠️ Event throughput is below optimal levels. Consider optimizing event processing."
                )
            if perf_metrics.get("max_memory_usage_mb", 0) > 200:
                recommendations.append(
                    "⚠️ Memory usage is high. Monitor for memory leaks in production."
                )

        format_result = next(
            (
                r
                for r in results["test_results"]
                if r.get("module") == "event_format_validation"
            ),
            None,
        )
        if format_result and not format_result.get("success", True):
            recommendations.append(
                "🔧 Event format validation failed. Ensure all events use colon format (code:category:action)."
            )

        if not recommendations:
            recommendations.append(
                "✅ All tests passed successfully! The event format fix is working correctly."
            )
            recommendations.append(
                "💡 Consider running tests regularly to catch regressions early."
            )

        if recommendations:
            recommendations_html = f"""
            <div class="recommendations">
                <h3>📋 Recommendations & Next Steps</h3>
                <ul>
                    {"".join(f"<li>{rec}</li>" for rec in recommendations)}
                </ul>
            </div>
            """

        # Fill in the template
        html_content = html_template.format(
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            overall_status=overall_status,
            overall_status_class=overall_status_class,
            modules_tested=total_modules,
            tests_passed=passed_modules,
            total_time=results.get("total_execution_time", 0),
            module_results=module_html,
            recommendations=recommendations_html,
        )

        return html_content

    async def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run the complete comprehensive test suite."""
        print("🚀 Starting Comprehensive Code Analysis Test Suite")
        print("=" * 70)
        print(f"Configuration: {json.dumps(self.config, indent=2)}")
        print("=" * 70)

        self.start_time = time.time()

        # Check dependencies first
        dependencies = self.check_dependencies()
        missing_deps = [dep for dep, available in dependencies.items() if not available]

        if missing_deps:
            print(f"\n⚠️ Warning: Missing dependencies: {', '.join(missing_deps)}")
            print("Some tests may be skipped or fail.")

        # Run all test modules
        test_results = []

        for module_id, module_name, test_function in self.test_modules:
            print(f"\n{'='*70}")
            print(f"🧪 STARTING: {module_name}")
            print(f"{'='*70}")

            try:
                result = await test_function()
                test_results.append(result)

                # Print immediate result
                if result.get("skipped", False):
                    print(f"⏭️ SKIPPED: {module_name} - {result.get('reason', '')}")
                elif result.get("success", False):
                    print(
                        f"✅ PASSED: {module_name} in {result.get('execution_time', 0):.2f}s"
                    )
                else:
                    print(
                        f"❌ FAILED: {module_name} - {result.get('error', 'Unknown error')}"
                    )

            except Exception as e:
                error_result = {
                    "module": module_id,
                    "success": False,
                    "execution_time": 0,
                    "error": f"Exception during test execution: {e!s}",
                }
                test_results.append(error_result)
                print(f"💥 EXCEPTION: {module_name} - {e!s}")

        self.end_time = time.time()

        # Calculate overall results
        total_modules = len([r for r in test_results if not r.get("skipped", False)])
        successful_modules = len(
            [
                r
                for r in test_results
                if r.get("success", False) and not r.get("skipped", False)
            ]
        )
        skipped_modules = len([r for r in test_results if r.get("skipped", False)])
        failed_modules = total_modules - successful_modules

        overall_success = successful_modules == total_modules

        # Compile comprehensive results
        comprehensive_results = {
            "overall_success": overall_success,
            "total_modules": len(test_results),
            "successful_modules": successful_modules,
            "failed_modules": failed_modules,
            "skipped_modules": skipped_modules,
            "success_rate": (
                successful_modules / total_modules if total_modules > 0 else 0
            ),
            "total_execution_time": self.end_time - self.start_time,
            "test_results": test_results,
            "configuration": self.config,
            "dependencies": dependencies,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Print final summary
        print("\n" + "=" * 70)
        print("🏆 COMPREHENSIVE TEST SUITE SUMMARY")
        print("=" * 70)
        print(f"Overall Result: {'✅ PASSED' if overall_success else '❌ FAILED'}")
        print(
            f"Modules: {successful_modules}/{total_modules} passed, {skipped_modules} skipped"
        )
        print(f"Success Rate: {comprehensive_results['success_rate']:.1%}")
        print(f"Total Time: {comprehensive_results['total_execution_time']:.2f}s")
        print(f"Timestamp: {comprehensive_results['timestamp']}")

        # Print module-by-module results
        print("\n📊 Module Results:")
        for result in test_results:
            module = result.get("module", "unknown")
            if result.get("skipped", False):
                status = "⏭️ SKIPPED"
            elif result.get("success", False):
                status = "✅ PASSED"
            else:
                status = "❌ FAILED"
            time_str = (
                f"({result.get('execution_time', 0):.2f}s)"
                if not result.get("skipped")
                else ""
            )
            print(f"  {status} - {module.replace('_', ' ').title()} {time_str}")

        return comprehensive_results


def main():
    """Main function to run comprehensive test suite."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Test Suite for Code Analysis Dashboard"
    )

    # Test configuration options
    parser.add_argument(
        "--dashboard-url",
        default="http://localhost:8765",
        help="Dashboard URL for testing",
    )
    parser.add_argument(
        "--dashboard-port",
        type=int,
        default=8765,
        help="Dashboard port for integration tests",
    )
    parser.add_argument(
        "--dashboard-timeout", type=int, default=30, help="Dashboard startup timeout"
    )
    parser.add_argument(
        "--browsers", nargs="+", default=["chrome"], help="Browsers to test with"
    )
    parser.add_argument(
        "--headless", action="store_true", help="Run browser tests in headless mode"
    )

    # Test selection options
    parser.add_argument(
        "--skip-browser-tests",
        action="store_true",
        help="Skip browser automation tests",
    )
    parser.add_argument(
        "--skip-integration-tests", action="store_true", help="Skip integration tests"
    )
    parser.add_argument(
        "--skip-server-tests", action="store_true", help="Skip server-dependent tests"
    )

    # Output options
    parser.add_argument(
        "--output-dir", default="test_results", help="Directory to save test results"
    )
    parser.add_argument(
        "--generate-html", action="store_true", help="Generate HTML report"
    )
    parser.add_argument("--save-json", action="store_true", help="Save JSON results")

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Build test configuration
    config = {
        "dashboard_url": args.dashboard_url,
        "dashboard_port": args.dashboard_port,
        "dashboard_timeout": args.dashboard_timeout,
        "browsers": args.browsers,
        "headless": args.headless,
        "run_browser_tests": not args.skip_browser_tests,
        "run_integration_tests": not args.skip_integration_tests,
        "run_server_dependent_tests": not args.skip_server_tests,
    }

    print("🧪 Claude MPM Code Analysis Dashboard - Comprehensive Test Suite")
    print("=" * 70)
    print(
        "This test suite validates the event format fixes and dashboard functionality"
    )
    print("=" * 70)

    async def run_tests():
        # Initialize and run test runner
        runner = ComprehensiveTestRunner(config)
        results = await runner.run_comprehensive_test_suite()

        # Save results
        if args.save_json:
            json_file = (
                output_dir
                / f"comprehensive_test_results_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
            )
            with json_file.open("w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n📁 JSON results saved to: {json_file}")

        if args.generate_html:
            html_content = runner.generate_html_report(results)
            html_file = (
                output_dir
                / f"test_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.html"
            )
            with html_file.open("w") as f:
                f.write(html_content)
            print(f"📄 HTML report saved to: {html_file}")

        # Exit with appropriate code
        return 0 if results["overall_success"] else 1

    # Run the async test suite
    exit_code = asyncio.run(run_tests())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
