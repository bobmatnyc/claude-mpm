#!/usr/bin/env python3
"""
Tree Sitter-based codebase analysis to find large, obsolete, or unused code.
"""

import os
import sys
from pathlib import Path
from collections import defaultdict, Counter
import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Node
import ast
import re

class CodebaseAnalyzer:
    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.parser = Parser(Language(tspython.language()))
        
        # Track various metrics
        self.file_metrics = {}
        self.function_metrics = {}
        self.class_metrics = {}
        self.import_usage = defaultdict(set)
        self.defined_symbols = defaultdict(set)
        self.used_symbols = defaultdict(set)
        
    def analyze_file(self, file_path):
        """Analyze a single Python file."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            tree = self.parser.parse(content)
            
            # Basic file metrics
            lines = content.decode('utf-8', errors='ignore').split('\n')
            self.file_metrics[file_path] = {
                'lines': len(lines),
                'size_bytes': len(content),
                'functions': 0,
                'classes': 0,
                'imports': 0,
                'complexity': 0
            }
            
            self._analyze_node(tree.root_node, file_path, content)
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    def _analyze_node(self, node, file_path, content):
        """Recursively analyze AST nodes."""
        if node.type == 'function_definition':
            self._analyze_function(node, file_path, content)
        elif node.type == 'class_definition':
            self._analyze_class(node, file_path, content)
        elif node.type == 'import_statement' or node.type == 'import_from_statement':
            self._analyze_import(node, file_path, content)
        
        # Count complexity indicators
        if node.type in ['if_statement', 'for_statement', 'while_statement', 'try_statement']:
            self.file_metrics[file_path]['complexity'] += 1
        
        # Recursively analyze children
        for child in node.children:
            self._analyze_node(child, file_path, content)
    
    def _analyze_function(self, node, file_path, content):
        """Analyze function definition."""
        self.file_metrics[file_path]['functions'] += 1
        
        # Get function name
        name_node = node.child_by_field_name('name')
        if name_node:
            func_name = content[name_node.start_byte:name_node.end_byte].decode('utf-8')
            
            # Calculate function metrics
            func_content = content[node.start_byte:node.end_byte].decode('utf-8')
            func_lines = len(func_content.split('\n'))
            
            self.function_metrics[f"{file_path}::{func_name}"] = {
                'lines': func_lines,
                'file': file_path,
                'name': func_name,
                'start_line': content[:node.start_byte].decode('utf-8').count('\n') + 1
            }
            
            self.defined_symbols[file_path].add(func_name)
    
    def _analyze_class(self, node, file_path, content):
        """Analyze class definition."""
        self.file_metrics[file_path]['classes'] += 1
        
        # Get class name
        name_node = node.child_by_field_name('name')
        if name_node:
            class_name = content[name_node.start_byte:name_node.end_byte].decode('utf-8')
            
            # Calculate class metrics
            class_content = content[node.start_byte:node.end_byte].decode('utf-8')
            class_lines = len(class_content.split('\n'))
            
            self.class_metrics[f"{file_path}::{class_name}"] = {
                'lines': class_lines,
                'file': file_path,
                'name': class_name,
                'methods': 0,
                'start_line': content[:node.start_byte].decode('utf-8').count('\n') + 1
            }
            
            self.defined_symbols[file_path].add(class_name)
            
            # Count methods in class
            for child in node.children:
                if child.type == 'function_definition':
                    self.class_metrics[f"{file_path}::{class_name}"]['methods'] += 1
    
    def _analyze_import(self, node, file_path, content):
        """Analyze import statements."""
        self.file_metrics[file_path]['imports'] += 1
        
        import_content = content[node.start_byte:node.end_byte].decode('utf-8')
        self.import_usage[file_path].add(import_content.strip())
    
    def find_python_files(self):
        """Find all Python files in the codebase."""
        python_files = []
        for root, dirs, files in os.walk(self.root_path):
            # Skip common non-source directories
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.pytest_cache', 'venv', '.venv', 'node_modules'}]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        return python_files
    
    def analyze_codebase(self):
        """Analyze the entire codebase."""
        python_files = self.find_python_files()
        print(f"Found {len(python_files)} Python files to analyze...")
        
        for file_path in python_files:
            self.analyze_file(file_path)
        
        return self.generate_report()
    
    def generate_report(self):
        """Generate analysis report."""
        report = {
            'summary': {
                'total_files': len(self.file_metrics),
                'total_lines': sum(m['lines'] for m in self.file_metrics.values()),
                'total_functions': sum(m['functions'] for m in self.file_metrics.values()),
                'total_classes': sum(m['classes'] for m in self.file_metrics.values()),
            },
            'large_files': [],
            'large_functions': [],
            'large_classes': [],
            'complex_files': [],
            'potential_unused': []
        }
        
        # Find large files (>500 lines)
        for file_path, metrics in self.file_metrics.items():
            if metrics['lines'] > 500:
                report['large_files'].append({
                    'file': str(file_path.relative_to(self.root_path)),
                    'lines': metrics['lines'],
                    'functions': metrics['functions'],
                    'classes': metrics['classes']
                })
        
        # Find large functions (>100 lines)
        for func_key, metrics in self.function_metrics.items():
            if metrics['lines'] > 100:
                report['large_functions'].append({
                    'function': func_key,
                    'file': str(metrics['file'].relative_to(self.root_path)),
                    'lines': metrics['lines'],
                    'start_line': metrics['start_line']
                })
        
        # Find large classes (>300 lines)
        for class_key, metrics in self.class_metrics.items():
            if metrics['lines'] > 300:
                report['large_classes'].append({
                    'class': class_key,
                    'file': str(metrics['file'].relative_to(self.root_path)),
                    'lines': metrics['lines'],
                    'methods': metrics['methods'],
                    'start_line': metrics['start_line']
                })
        
        # Find complex files (high complexity score)
        for file_path, metrics in self.file_metrics.items():
            if metrics['complexity'] > 20:
                report['complex_files'].append({
                    'file': str(file_path.relative_to(self.root_path)),
                    'complexity': metrics['complexity'],
                    'lines': metrics['lines']
                })
        
        # Sort results by size/complexity
        report['large_files'].sort(key=lambda x: x['lines'], reverse=True)
        report['large_functions'].sort(key=lambda x: x['lines'], reverse=True)
        report['large_classes'].sort(key=lambda x: x['lines'], reverse=True)
        report['complex_files'].sort(key=lambda x: x['complexity'], reverse=True)
        
        return report

def main():
    if len(sys.argv) > 1:
        root_path = sys.argv[1]
    else:
        root_path = "."
    
    analyzer = CodebaseAnalyzer(root_path)
    report = analyzer.analyze_codebase()
    
    print("\n" + "="*80)
    print("CODEBASE ANALYSIS REPORT")
    print("="*80)
    
    print(f"\nSUMMARY:")
    print(f"  Total files: {report['summary']['total_files']}")
    print(f"  Total lines: {report['summary']['total_lines']:,}")
    print(f"  Total functions: {report['summary']['total_functions']}")
    print(f"  Total classes: {report['summary']['total_classes']}")
    
    print(f"\nLARGE FILES (>500 lines):")
    for item in report['large_files'][:10]:  # Top 10
        print(f"  {item['file']}: {item['lines']} lines, {item['functions']} functions, {item['classes']} classes")
    
    print(f"\nLARGE FUNCTIONS (>100 lines):")
    for item in report['large_functions'][:10]:  # Top 10
        print(f"  {item['file']}:{item['start_line']} - {item['lines']} lines")
    
    print(f"\nLARGE CLASSES (>300 lines):")
    for item in report['large_classes'][:10]:  # Top 10
        print(f"  {item['file']}:{item['start_line']} - {item['lines']} lines, {item['methods']} methods")
    
    print(f"\nCOMPLEX FILES (>20 complexity):")
    for item in report['complex_files'][:10]:  # Top 10
        print(f"  {item['file']}: complexity {item['complexity']}, {item['lines']} lines")

if __name__ == "__main__":
    main()
