#!/usr/bin/env python3
"""
Demonstration of Research Agent content threshold system.

This script demonstrates how the Research agent would:
1. Check file sizes before processing
2. Trigger summarization at thresholds
3. Track cumulative content
4. Apply adaptive grep context
"""

import os
from pathlib import Path


class ResearchMemoryManager:
    """Simulates the Research agent's memory management system."""
    
    # Threshold constants from Research agent configuration
    SUMMARIZE_THRESHOLD_LINES = 200
    SUMMARIZE_THRESHOLD_SIZE = 20_000  # 20KB
    CRITICAL_FILE_SIZE = 100_000       # 100KB
    CUMULATIVE_CONTENT_LIMIT = 50_000  # 50KB
    BATCH_SUMMARIZE_COUNT = 3
    
    # File type specific thresholds (lines)
    FILE_TYPE_THRESHOLDS = {
        '.py': 500, '.js': 500, '.ts': 500,
        '.json': 100, '.yaml': 100, '.toml': 100,
        '.md': 200, '.rst': 200, '.txt': 200,
        '.csv': 50, '.sql': 50, '.xml': 50
    }
    
    def __init__(self):
        self.cumulative_size = 0
        self.files_processed = 0
        self.patterns_extracted = []
    
    def should_summarize_file(self, file_path: Path) -> tuple[bool, str]:
        """Determine if a file should be summarized based on thresholds."""
        
        # Get file size
        try:
            file_size = file_path.stat().st_size
        except:
            return False, "File not found"
        
        # Check critical size threshold
        if file_size > self.CRITICAL_FILE_SIZE:
            return True, f"Critical size ({file_size:,} bytes > 100KB) - always summarize"
        
        # Check standard size threshold
        if file_size > self.SUMMARIZE_THRESHOLD_SIZE:
            return True, f"Exceeds size threshold ({file_size:,} bytes > 20KB)"
        
        # Check line count for specific file types
        file_ext = file_path.suffix.lower()
        if file_ext in self.FILE_TYPE_THRESHOLDS:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    line_count = sum(1 for _ in f)
                
                threshold = self.FILE_TYPE_THRESHOLDS[file_ext]
                if line_count > threshold:
                    return True, f"Exceeds line threshold for {file_ext} ({line_count} > {threshold})"
            except:
                pass
        
        return False, "Within thresholds"
    
    def process_file(self, file_path: Path) -> dict:
        """Simulate processing a file with threshold checks."""
        
        result = {
            'file': str(file_path),
            'size': 0,
            'action': '',
            'reason': ''
        }
        
        try:
            file_size = file_path.stat().st_size
            result['size'] = file_size
            
            # Check if summarization needed
            should_summarize, reason = self.should_summarize_file(file_path)
            
            if should_summarize:
                result['action'] = 'SUMMARIZE'
                result['reason'] = reason
                # Simulate MCP summarizer call
                result['mcp_call'] = 'mcp__claude-mpm-gateway__document_summarizer()'
            else:
                result['action'] = 'GREP_CONTEXT'
                result['reason'] = reason
                # Use grep with adaptive context
                result['grep_command'] = self.get_adaptive_grep_command(file_path)
            
            # Update cumulative tracking
            self.cumulative_size += file_size
            self.files_processed += 1
            
            # Check cumulative thresholds
            if self.cumulative_size > self.CUMULATIVE_CONTENT_LIMIT:
                result['batch_trigger'] = f"Cumulative size limit reached ({self.cumulative_size:,} > 50KB)"
                self.trigger_batch_summarization()
            elif self.files_processed >= self.BATCH_SUMMARIZE_COUNT:
                result['batch_trigger'] = f"File count limit reached ({self.files_processed} >= 3)"
                self.trigger_batch_summarization()
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def get_adaptive_grep_command(self, file_path: Path, pattern: str = "pattern") -> str:
        """Generate adaptive grep command based on match count."""
        
        # Simulate checking match count
        # In real implementation, would run: grep -c "pattern" file
        simulated_match_count = 25  # For demonstration
        
        if simulated_match_count > 50:
            return f'grep -n -A 2 -B 2 "{pattern}" {file_path} | head -50'
        elif simulated_match_count > 20:
            return f'grep -n -A 5 -B 5 "{pattern}" {file_path} | head -40'
        else:
            return f'grep -n -A 10 -B 10 "{pattern}" {file_path}'
    
    def trigger_batch_summarization(self):
        """Simulate batch summarization and reset counters."""
        print(f"\n🔄 BATCH SUMMARIZATION TRIGGERED")
        print(f"   Cumulative size: {self.cumulative_size:,} bytes")
        print(f"   Files processed: {self.files_processed}")
        print(f"   Action: mcp__claude-mpm-gateway__document_summarizer(style='executive')")
        print(f"   Resetting counters...")
        
        # Reset counters
        self.cumulative_size = 0
        self.files_processed = 0
        self.patterns_extracted = []
    
    def get_mcp_style(self, file_path: Path) -> str:
        """Get appropriate MCP summarizer style for file type."""
        
        ext = file_path.suffix.lower()
        
        if ext in ['.py', '.js', '.ts']:
            return "bullet_points"
        elif ext in ['.md', '.rst', '.txt']:
            return "brief"
        elif ext in ['.json', '.yaml', '.toml']:
            return "detailed"
        else:
            return "brief"


def demonstrate_thresholds():
    """Demonstrate the threshold system with example files."""
    
    print("🔬 RESEARCH AGENT THRESHOLD DEMONSTRATION")
    print("=" * 60)
    
    manager = ResearchMemoryManager()
    
    # Create test scenarios
    test_files = [
        # (path, simulated_size, description)
        (Path("small_module.py"), 5_000, "Small Python file (5KB)"),
        (Path("medium_module.py"), 25_000, "Medium Python file (25KB) - triggers summarization"),
        (Path("large_config.json"), 150_000, "Large JSON file (150KB) - critical size"),
        (Path("normal_doc.md"), 8_000, "Normal documentation (8KB)"),
        (Path("another_module.py"), 15_000, "Another Python file (15KB)"),
    ]
    
    for i, (file_path, sim_size, description) in enumerate(test_files, 1):
        print(f"\n{i}. Processing: {description}")
        print(f"   File: {file_path}")
        
        # Create temporary file for simulation
        temp_path = Path(f"/tmp/{file_path.name}")
        with open(temp_path, 'w') as f:
            # Write simulated content
            f.write("x" * sim_size)
        
        result = manager.process_file(temp_path)
        
        print(f"   Size: {result['size']:,} bytes")
        print(f"   Action: {result['action']}")
        print(f"   Reason: {result['reason']}")
        
        if 'mcp_call' in result:
            print(f"   MCP Call: {result['mcp_call']}")
            print(f"   Style: {manager.get_mcp_style(file_path)}")
        elif 'grep_command' in result:
            print(f"   Grep: {result['grep_command']}")
        
        if 'batch_trigger' in result:
            print(f"   ⚠️  {result['batch_trigger']}")
        
        # Clean up temp file
        temp_path.unlink(missing_ok=True)
    
    print("\n" + "=" * 60)
    print("📊 DEMONSTRATION SUMMARY")
    print("=" * 60)
    print("\nKey Behaviors Demonstrated:")
    print("• Files >20KB trigger single-file summarization")
    print("• Files >100KB are always summarized (critical)")
    print("• Cumulative content >50KB triggers batch summarization")
    print("• Processing 3+ files triggers batch summarization")
    print("• Grep context adapts based on match count")
    print("• File types have specific line thresholds")
    print("\n✨ This ensures 85% confidence while preventing memory issues")


if __name__ == "__main__":
    demonstrate_thresholds()