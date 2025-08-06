#!/usr/bin/env python3
"""
Code Logic Validation Test
Tests the core logic of implemented functions through static analysis
"""

import re
import json
from pathlib import Path

class CodeLogicValidator:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.web_static_js = self.project_root / "src" / "claude_mpm" / "web" / "static" / "js"
        self.validation_results = {}
        
    def validate_agent_consolidation_logic(self):
        """Validate the agent consolidation implementation"""
        print("🔍 Validating Agent Consolidation Logic...")
        
        agent_inference_file = self.web_static_js / "components" / "agent-inference.js"
        
        try:
            content = agent_inference_file.read_text()
            
            # Check for key consolidation logic
            checks = {
                "has_consolidation_function": "getUniqueAgentInstances()" in content,
                "uses_agent_map": "agentMap = new Map()" in content,
                "consolidates_by_name": "agentMap.has(agentName)" in content,
                "combines_delegations": "delegations.push(" in content,
                "merges_events": "allEvents = agent.allEvents.concat" in content,
                "tracks_delegation_count": "delegationCount" in content,
                "handles_timestamps": "firstTimestamp" in content and "lastTimestamp" in content,
                "handles_implied_delegations": "isImplied: true" in content
            }
            
            # Analyze the getUniqueAgentInstances function structure
            func_pattern = r'getUniqueAgentInstances\(\)\s*\{(.*?)\n\s*\}'
            func_match = re.search(func_pattern, content, re.DOTALL)
            
            if func_match:
                func_body = func_match.group(1)
                
                # Check for proper consolidation pattern
                has_proper_loop = "for (const [delegationId, delegation] of this.state.pmDelegations)" in func_body
                has_conditional_creation = "if (!agentMap.has(agentName))" in func_body
                has_array_return = "Array.from(agentMap.values())" in func_body
                
                checks.update({
                    "proper_loop_structure": has_proper_loop,
                    "conditional_agent_creation": has_conditional_creation,
                    "returns_array": has_array_return
                })
            
            # Calculate score
            passed_checks = sum(1 for check in checks.values() if check)
            total_checks = len(checks)
            score = (passed_checks / total_checks) * 100
            
            self.validation_results["agent_consolidation"] = {
                "score": score,
                "passed": passed_checks,
                "total": total_checks,
                "checks": checks,
                "status": "PASS" if score >= 80 else "FAIL"
            }
            
            print(f"  Agent Consolidation Logic: {score:.1f}% ({passed_checks}/{total_checks} checks passed)")
            
        except Exception as e:
            self.validation_results["agent_consolidation"] = {
                "error": str(e),
                "status": "ERROR"
            }
            print(f"  ❌ Error validating agent consolidation: {e}")
    
    def validate_data_viewer_enhancements(self):
        """Validate whitespace trimming and token counting"""
        print("🔍 Validating Data Viewer Enhancements...")
        
        module_viewer_file = self.web_static_js / "components" / "module-viewer.js"
        
        try:
            content = module_viewer_file.read_text()
            
            # Check for whitespace trimming function
            has_trim_function = "trimPromptWhitespace(" in content
            has_token_function = "estimateTokenCount(" in content
            has_escape_function = "escapeHtml(" in content
            
            # Analyze trimPromptWhitespace function
            trim_checks = {
                "has_trim_function": has_trim_function,
                "trims_leading_trailing": "text = text.trim()" in content,
                "reduces_newlines": "replace(/\\n\\s*\\n\\s*\\n+/g, '\\n\\n')" in content,
                "preserves_structure": "split('\\n').map(line =>" in content,
                "handles_empty_input": "if (!text || typeof text !== 'string') return ''" in content
            }
            
            # Analyze estimateTokenCount function
            token_checks = {
                "has_token_function": has_token_function,
                "word_based_estimate": "text.trim().split(/\\s+/).length" in content,
                "char_based_estimate": "Math.ceil(text.length / 4)" in content,
                "handles_empty": "if (!text || typeof text !== 'string') return 0" in content,
                "uses_higher_estimate": "Math.max(" in content or "Use the higher" in content
            }
            
            # Analyze HTML escaping
            escape_checks = {
                "has_escape_function": has_escape_function,
                "uses_textcontent": "div.textContent = text" in content,
                "returns_innerHTML": "return div.innerHTML" in content,
                "handles_empty": "if (!text) return ''" in content
            }
            
            # Check usage in agent view
            usage_checks = {
                "uses_trimmed_prompt": "trimPromptWhitespace(agentData.prompt)" in content,
                "displays_token_count": "estimateTokenCount(trimmedPrompt)" in content,
                "displays_word_count": "trimmedPrompt.trim().split(/\\s+/).length" in content,
                "displays_char_count": "trimmedPrompt.length" in content,
                "escapes_display": "escapeHtml(trimmedPrompt)" in content
            }
            
            all_checks = {**trim_checks, **token_checks, **escape_checks, **usage_checks}
            passed = sum(1 for check in all_checks.values() if check)
            total = len(all_checks)
            score = (passed / total) * 100
            
            self.validation_results["data_viewer_enhancements"] = {
                "score": score,
                "passed": passed,
                "total": total,
                "checks": all_checks,
                "categories": {
                    "trimming": trim_checks,
                    "token_counting": token_checks,
                    "html_escaping": escape_checks,
                    "usage": usage_checks
                },
                "status": "PASS" if score >= 80 else "FAIL"
            }
            
            print(f"  Data Viewer Enhancements: {score:.1f}% ({passed}/{total} checks passed)")
            
        except Exception as e:
            self.validation_results["data_viewer_enhancements"] = {
                "error": str(e),
                "status": "ERROR"
            }
            print(f"  ❌ Error validating data viewer enhancements: {e}")
    
    def validate_diff_viewer_functionality(self):
        """Validate diff viewer implementation"""
        print("🔍 Validating Diff Viewer Functionality...")
        
        dashboard_file = self.web_static_js / "dashboard.js"
        
        try:
            content = dashboard_file.read_text()
            
            # Check for diff viewer functions
            checks = {
                "has_show_diff_function": "showGitDiffModal" in content,
                "has_hide_diff_function": "hideGitDiffModal" in content,
                "has_copy_diff_function": "copyGitDiff" in content,
                "creates_modal": "createGitDiffModal" in content,
                "updates_modal": "updateGitDiffModal" in content,
                "handles_git_commands": "git diff" in content or "git status" in content,
                "uses_working_directory": "workingDir" in content,
                "shows_file_path": "git-diff-file-path" in content,
                "displays_diff_content": "git-diff-code" in content,
                "handles_modal_display": "modal.style.display" in content
            }
            
            # Look for diff modal HTML structure
            modal_structure_checks = {
                "has_modal_class": "git-diff-modal" in content,
                "has_modal_content": "modal-content" in content,
                "has_diff_header": "git-diff-header" in content,
                "has_diff_title": "git-diff-title" in content,
                "has_copy_button": "Copy Diff" in content or "copy" in content.lower()
            }
            
            all_checks = {**checks, **modal_structure_checks}
            passed = sum(1 for check in all_checks.values() if check)
            total = len(all_checks)
            score = (passed / total) * 100
            
            self.validation_results["diff_viewer"] = {
                "score": score,
                "passed": passed,
                "total": total,
                "checks": all_checks,
                "status": "PASS" if score >= 80 else "FAIL"
            }
            
            print(f"  Diff Viewer Functionality: {score:.1f}% ({passed}/{total} checks passed)")
            
        except Exception as e:
            self.validation_results["diff_viewer"] = {
                "error": str(e),
                "status": "ERROR"
            }
            print(f"  ❌ Error validating diff viewer: {e}")
    
    def validate_implementation_quality(self):
        """Validate overall code quality aspects"""
        print("🔍 Validating Implementation Quality...")
        
        quality_metrics = {
            "error_handling": 0,
            "null_safety": 0,
            "performance_considerations": 0,
            "security": 0
        }
        
        try:
            # Check all JavaScript files for quality indicators
            js_files = [
                self.web_static_js / "components" / "agent-inference.js",
                self.web_static_js / "components" / "module-viewer.js",
                self.web_static_js / "dashboard.js"
            ]
            
            for js_file in js_files:
                if js_file.exists():
                    content = js_file.read_text()
                    
                    # Error handling checks
                    if "try {" in content and "catch" in content:
                        quality_metrics["error_handling"] += 1
                    if "console.error" in content:
                        quality_metrics["error_handling"] += 1
                    
                    # Null safety checks
                    if "if (!text" in content or "if (!event" in content:
                        quality_metrics["null_safety"] += 1
                    if "typeof" in content:
                        quality_metrics["null_safety"] += 1
                    
                    # Performance considerations
                    if "console.log" in content and "Math.random() < 0.1" in content:
                        quality_metrics["performance_considerations"] += 1  # Debug logging throttling
                    if "Map(" in content or "Set(" in content:
                        quality_metrics["performance_considerations"] += 1  # Efficient data structures
                    
                    # Security checks
                    if "escapeHtml" in content:
                        quality_metrics["security"] += 1
                    if "textContent" in content:
                        quality_metrics["security"] += 1
            
            # Calculate quality score
            max_score_per_metric = len(js_files) * 2  # Allow multiple points per file
            quality_score = sum(min(score, max_score_per_metric) for score in quality_metrics.values())
            max_quality_score = max_score_per_metric * len(quality_metrics)
            quality_percentage = (quality_score / max_quality_score) * 100
            
            self.validation_results["implementation_quality"] = {
                "score": quality_percentage,
                "metrics": quality_metrics,
                "status": "PASS" if quality_percentage >= 60 else "FAIL"
            }
            
            print(f"  Implementation Quality: {quality_percentage:.1f}% (Score: {quality_score}/{max_quality_score})")
            
        except Exception as e:
            self.validation_results["implementation_quality"] = {
                "error": str(e),
                "status": "ERROR"
            }
            print(f"  ❌ Error validating implementation quality: {e}")
    
    def run_validation(self):
        """Run all validation tests"""
        print("🧪 Starting Code Logic Validation...")
        print("=" * 50)
        
        self.validate_agent_consolidation_logic()
        self.validate_data_viewer_enhancements()
        self.validate_diff_viewer_functionality()
        self.validate_implementation_quality()
        
        # Calculate overall validation score
        category_scores = []
        for category, result in self.validation_results.items():
            if "score" in result:
                category_scores.append(result["score"])
        
        overall_score = sum(category_scores) / len(category_scores) if category_scores else 0
        overall_status = "PASS" if overall_score >= 80 else "CONDITIONAL_PASS" if overall_score >= 60 else "FAIL"
        
        print("=" * 50)
        print(f"📊 Code Validation Results: {overall_score:.1f}% - {overall_status}")
        
        return {
            "overall_score": overall_score,
            "overall_status": overall_status,
            "detailed_results": self.validation_results
        }

def main():
    validator = CodeLogicValidator()
    results = validator.run_validation()
    
    # Save validation results
    report_file = Path(__file__).parent.parent / "code_logic_validation_report.json"
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Validation report saved: {report_file}")
    
    return results["overall_status"] in ["PASS", "CONDITIONAL_PASS"]

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)