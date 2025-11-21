"""
Mermaid Diagram Generator Service for Claude MPM
================================================

This service generates Mermaid diagrams for code visualization based on
analysis results from the Code Analyzer agent.

WHY: Visual representations of code structure help developers understand
complex codebases more quickly. Mermaid diagrams can be rendered in
documentation and provide interactive exploration capabilities.

DESIGN DECISION: We support multiple diagram types (entry points, module
dependencies, class hierarchies, and call graphs) to cover different
aspects of code structure analysis.
"""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from claude_mpm.services.core.base import SyncBaseService


class DiagramType(Enum):
    """Supported Mermaid diagram types for code visualization."""

    ENTRY_POINTS = "entry_points"
    MODULE_DEPS = "module_deps"
    CLASS_HIERARCHY = "class_hierarchy"
    CALL_GRAPH = "call_graph"


@dataclass
class DiagramConfig:
    """Configuration for diagram generation."""

    title: Optional[str] = None
    direction: str = "TB"  # Top-Bottom by default
    theme: str = "default"
    max_depth: int = 5
    include_external: bool = False
    show_parameters: bool = True
    show_return_types: bool = True


class MermaidGeneratorService(SyncBaseService):
    """
    Service for generating Mermaid diagrams from code analysis results.

    This service provides methods to generate various types of diagrams
    including entry points, module dependencies, class hierarchies, and
    call graphs.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Mermaid generator service."""
        super().__init__(service_name="MermaidGeneratorService", config=config)
        self._node_id_counter = 0
        self._node_id_cache: Dict[str, str] = {}
        self._reserved_keywords = {
            "graph",
            "subgraph",
            "end",
            "class",
            "classDef",
            "click",
            "style",
            "linkStyle",
            "interpolate",
            "flowchart",
            "pie",
            "sequenceDiagram",
            "gantt",
            "stateDiagram",
            "erDiagram",
            "journey",
            "gitGraph",
            "mindmap",
            "timeline",
            "quadrantChart",
            "sankey",
            "xychart",
            "block",
            "start",
            "stop",
            "operation",
            "subroutine",
            "condition",
            "inputoutput",
            "parallel",
            "database",
        }

    def initialize(self) -> bool:
        """Initialize the service."""
        try:
            self.log_info("Initializing MermaidGeneratorService")
            self._initialized = True
            return True
        except Exception as e:
            self.log_error(f"Failed to initialize: {e}")
            return False

    def shutdown(self) -> None:
        """Shutdown the service."""
        self.log_info("Shutting down MermaidGeneratorService")
        self._node_id_cache.clear()
        self._shutdown = True

    def generate_diagram(
        self,
        diagram_type: DiagramType,
        analysis_results: Dict[str, Any],
        config: Optional[DiagramConfig] = None,
    ) -> str:
        """
        Generate a Mermaid diagram based on analysis results.

        Args:
            diagram_type: Type of diagram to generate
            analysis_results: Code analysis results from Code Analyzer agent
            config: Optional configuration for diagram generation

        Returns:
            Mermaid diagram syntax as string

        Raises:
            ValueError: If diagram type is not supported or data is invalid
        """
        if not self._initialized:
            raise RuntimeError("Service not initialized")

        config = config or DiagramConfig()

        # Reset node ID cache for each new diagram
        self._node_id_cache.clear()
        self._node_id_counter = 0

        try:
            if diagram_type == DiagramType.ENTRY_POINTS:
                return self._generate_entry_points_diagram(analysis_results, config)
            if diagram_type == DiagramType.MODULE_DEPS:
                return self._generate_module_deps_diagram(analysis_results, config)
            if diagram_type == DiagramType.CLASS_HIERARCHY:
                return self._generate_class_hierarchy_diagram(analysis_results, config)
            if diagram_type == DiagramType.CALL_GRAPH:
                return self._generate_call_graph_diagram(analysis_results, config)
            raise ValueError(f"Unsupported diagram type: {diagram_type}")
        except Exception as e:
            # Handle both DiagramType enums and plain strings
            type_name = (
                diagram_type.value
                if hasattr(diagram_type, "value")
                else str(diagram_type)
            )
            self.log_error(f"Failed to generate {type_name} diagram: {e}")
            raise

    def _generate_entry_points_diagram(
        self, analysis_results: Dict[str, Any], config: DiagramConfig
    ) -> str:
        """Generate entry points flow diagram."""
        lines = []
        title = config.title or "Application Entry Points"

        # Start diagram
        lines.append(f"flowchart {config.direction}")
        lines.append(f"    %% {title}")
        lines.append("")

        # Get entry points from analysis results
        entry_points = analysis_results.get("entry_points", {})

        if not entry_points:
            lines.append("    NoEntryPoints[No entry points found]")
            return "\n".join(lines)

        # Create start node
        lines.append("    Start([Application Start])")
        lines.append("")

        # Process each entry point
        for entry_type, entries in entry_points.items():
            if not entries:
                continue

            # Create subgraph for each entry type
            subgraph_id = self._sanitize_node_id(f"subgraph_{entry_type}")
            lines.append(
                f"    subgraph {subgraph_id}[{entry_type.replace('_', ' ').title()}]"
            )

            for entry in entries:
                if isinstance(entry, dict):
                    file_path = entry.get("file", "")
                    func_name = entry.get("function", "main")
                    line_num = entry.get("line", 0)

                    # Handle None or invalid file paths
                    if not file_path or not isinstance(file_path, (str, Path)):
                        file_path = "unknown"

                    # Create node for entry point
                    node_id = self._get_node_id(f"{file_path}:{func_name}")
                    try:
                        path_name = (
                            Path(file_path).name
                            if file_path != "unknown"
                            else "unknown"
                        )
                    except (TypeError, OSError):
                        path_name = "unknown"
                    node_label = self._escape_label(f"{path_name}::{func_name}")

                    if line_num:
                        node_label += f" (L{line_num})"

                    lines.append(f"        {node_id}[{node_label}]")

            lines.append("    end")
            lines.append("")

        # Connect start to entry points
        for entry_type, entries in entry_points.items():
            if entries:
                for entry in entries[:3]:  # Limit connections to avoid clutter
                    if isinstance(entry, dict):
                        file_path = entry.get("file", "")
                        func_name = entry.get("function", "main")

                        # Handle None or invalid file paths
                        if not file_path or not isinstance(file_path, (str, Path)):
                            file_path = "unknown"

                        node_id = self._get_node_id(f"{file_path}:{func_name}")
                        lines.append(f"    Start --> {node_id}")

        # Add styling
        lines.append("")
        lines.append(
            "    classDef entryPoint fill:#90EE90,stroke:#333,stroke-width:2px"
        )
        lines.append("    classDef startNode fill:#FFD700,stroke:#333,stroke-width:3px")
        lines.append("    class Start startNode")

        return "\n".join(lines)

    def _generate_module_deps_diagram(
        self, analysis_results: Dict[str, Any], config: DiagramConfig
    ) -> str:
        """Generate module dependency diagram."""
        lines = []
        title = config.title or "Module Dependencies"

        # Start diagram
        lines.append(f"flowchart {config.direction}")
        lines.append(f"    %% {title}")
        lines.append("")

        # Get dependencies from analysis results
        dependencies = analysis_results.get("dependencies", {})
        imports_data = analysis_results.get("imports", {})

        # Handle None values
        if dependencies is None:
            dependencies = {}
        if imports_data is None:
            imports_data = {}

        # Check if we have any meaningful data
        has_deps = bool(dependencies and any(v for v in dependencies.values() if v))
        has_imports = bool(imports_data and any(v for v in imports_data.values() if v))

        if not has_deps and not has_imports:
            lines.append("    NoDeps[No dependencies found]")
            return "\n".join(lines)

        # Track all modules and their relationships
        modules: Set[str] = set()
        edges: List[Tuple[str, str, str]] = []  # (from, to, label)

        # Process dependencies
        for module, deps in dependencies.items():
            module_name = self._extract_module_name(module)
            modules.add(module_name)

            if isinstance(deps, list):
                for dep in deps:
                    dep_name = self._extract_module_name(str(dep))
                    if not config.include_external and self._is_external_module(
                        dep_name
                    ):
                        continue
                    modules.add(dep_name)
                    edges.append((module_name, dep_name, "depends"))

        # Process imports
        for file_path, imports in imports_data.items():
            module_name = self._extract_module_name(file_path)
            modules.add(module_name)

            if isinstance(imports, list):
                for imp in imports:
                    if isinstance(imp, dict):
                        import_from = imp.get("from", imp.get("module", ""))
                        if import_from:
                            import_name = self._extract_module_name(import_from)
                            if not config.include_external and self._is_external_module(
                                import_name
                            ):
                                continue
                            modules.add(import_name)
                            edges.append((module_name, import_name, "imports"))

        # Create nodes for all modules
        external_modules = set()
        internal_modules = set()

        for module in modules:
            node_id = self._get_node_id(module)
            node_label = self._escape_label(module)

            if self._is_external_module(module):
                lines.append(f"    {node_id}[({node_label})]")
                external_modules.add(node_id)
            else:
                lines.append(f"    {node_id}[{node_label}]")
                internal_modules.add(node_id)

        lines.append("")

        # Create edges
        for from_module, to_module, rel_type in edges:
            from_id = self._get_node_id(from_module)
            to_id = self._get_node_id(to_module)

            if rel_type == "imports":
                lines.append(f"    {from_id} --> {to_id}")
            else:
                lines.append(f"    {from_id} -.-> {to_id}")

        # Add styling
        lines.append("")
        lines.append("    classDef internal fill:#87CEEB,stroke:#333,stroke-width:2px")
        lines.append("    classDef external fill:#FFB6C1,stroke:#333,stroke-width:1px")

        if internal_modules:
            lines.append(f"    class {','.join(internal_modules)} internal")
        if external_modules:
            lines.append(f"    class {','.join(external_modules)} external")

        return "\n".join(lines)

    def _generate_class_hierarchy_diagram(
        self, analysis_results: Dict[str, Any], config: DiagramConfig
    ) -> str:
        """Generate class hierarchy diagram."""
        lines = []
        title = config.title or "Class Hierarchy"

        # Start diagram
        lines.append("classDiagram")
        lines.append(f"    %% {title}")
        lines.append("")

        # Get classes from analysis results
        classes = analysis_results.get("classes", {})

        if not classes:
            lines.append("    class NoClasses {")
            lines.append("        <<placeholder>>")
            lines.append("        No classes found")
            lines.append("    }")
            return "\n".join(lines)

        # Process each class
        for class_name, class_info in classes.items():
            if not isinstance(class_info, dict):
                continue

            safe_name = self._sanitize_class_name(class_name)

            # Define class
            lines.append(f"    class {safe_name} {{")

            # Add class type annotation if it's special
            if class_info.get("is_abstract"):
                lines.append("        <<abstract>>")
            elif class_info.get("is_interface"):
                lines.append("        <<interface>>")
            elif class_info.get("is_enum"):
                lines.append("        <<enumeration>>")

            # Add attributes
            attributes = class_info.get("attributes", [])
            if attributes:
                for attr in attributes[:10]:  # Limit to avoid clutter
                    if isinstance(attr, dict):
                        attr_name = attr.get("name", "")
                        attr_type = attr.get("type", "Any")
                        visibility = attr.get("visibility", "+")
                        if config.show_return_types:
                            lines.append(
                                f"        {visibility}{attr_name}: {attr_type}"
                            )
                        else:
                            lines.append(f"        {visibility}{attr_name}")
                    elif isinstance(attr, str):
                        lines.append(f"        +{attr}")

            # Add methods
            methods = class_info.get("methods", [])
            if methods:
                for method in methods[:10]:  # Limit to avoid clutter
                    if isinstance(method, dict):
                        method_name = method.get("name", "")
                        params = method.get("parameters", [])
                        return_type = method.get("return_type", "None")
                        visibility = method.get("visibility", "+")

                        if config.show_parameters and params:
                            param_str = (
                                ", ".join(params)
                                if isinstance(params, list)
                                else str(params)
                            )
                            method_sig = f"{method_name}({param_str})"
                        else:
                            method_sig = f"{method_name}()"

                        if config.show_return_types:
                            lines.append(
                                f"        {visibility}{method_sig}: {return_type}"
                            )
                        else:
                            lines.append(f"        {visibility}{method_sig}")
                    elif isinstance(method, str):
                        lines.append(f"        +{method}()")

            lines.append("    }")
            lines.append("")

        # Add relationships
        for class_name, class_info in classes.items():
            if not isinstance(class_info, dict):
                continue

            safe_name = self._sanitize_class_name(class_name)

            # Inheritance relationships
            bases = class_info.get("bases", [])
            if bases:
                for base in bases:
                    if isinstance(base, str):
                        safe_base = self._sanitize_class_name(base)
                        if safe_base in [self._sanitize_class_name(c) for c in classes]:
                            lines.append(f"    {safe_base} <|-- {safe_name}")

            # Composition relationships
            compositions = class_info.get("compositions", [])
            if compositions:
                for comp in compositions:
                    if isinstance(comp, str):
                        safe_comp = self._sanitize_class_name(comp)
                        if safe_comp in [self._sanitize_class_name(c) for c in classes]:
                            lines.append(f"    {safe_name} *-- {safe_comp}")

            # Association relationships
            associations = class_info.get("associations", [])
            if associations:
                for assoc in associations:
                    if isinstance(assoc, str):
                        safe_assoc = self._sanitize_class_name(assoc)
                        if safe_assoc in [
                            self._sanitize_class_name(c) for c in classes
                        ]:
                            lines.append(f"    {safe_name} --> {safe_assoc}")

        return "\n".join(lines)

    def _generate_call_graph_diagram(
        self, analysis_results: Dict[str, Any], config: DiagramConfig
    ) -> str:
        """Generate function call graph diagram."""
        lines = []
        title = config.title or "Function Call Graph"

        # Start diagram
        lines.append(f"flowchart {config.direction}")
        lines.append(f"    %% {title}")
        lines.append("")

        # Get functions and call relationships
        functions = analysis_results.get("functions", {})
        call_graph = analysis_results.get("call_graph", {})

        if not functions and not call_graph:
            lines.append("    NoFunctions[No functions found]")
            return "\n".join(lines)

        # Track all functions and their calls
        all_functions: Set[str] = set()
        calls: List[Tuple[str, str, Optional[str]]] = []  # (caller, callee, label)

        # Process call graph
        for caller, callees in call_graph.items():
            all_functions.add(caller)

            if isinstance(callees, list):
                for callee in callees:
                    if isinstance(callee, dict):
                        func_name = callee.get("function", callee.get("name", ""))
                        if func_name:
                            all_functions.add(func_name)
                            call_count = callee.get("count", 0)
                            label = str(call_count) if call_count > 1 else None
                            calls.append((caller, func_name, label))
                    elif isinstance(callee, str):
                        all_functions.add(callee)
                        calls.append((caller, callee, None))

        # Process functions to add those not in call graph
        for func_name, func_info in functions.items():
            all_functions.add(func_name)

            # Check for calls within function
            if isinstance(func_info, dict):
                func_calls = func_info.get("calls", [])
                for call in func_calls:
                    if isinstance(call, str):
                        all_functions.add(call)
                        calls.append((func_name, call, None))

        # Create nodes for all functions
        entry_functions = set()
        regular_functions = set()

        for func in all_functions:
            node_id = self._get_node_id(func)
            node_label = self._escape_label(func)

            # Check if this is an entry point
            is_entry = func in ["main", "__main__", "run", "start", "execute"]

            if is_entry:
                lines.append(f"    {node_id}[/{node_label}/]")
                entry_functions.add(node_id)
            # Check if function has specific characteristics
            elif func.startswith("_") and not func.startswith("__"):
                lines.append(f"    {node_id}[{node_label}]:::private")
            elif func.startswith("__") and func.endswith("__"):
                lines.append(f"    {node_id}[{node_label}]:::magic")
            else:
                lines.append(f"    {node_id}[{node_label}]")
                regular_functions.add(node_id)

        lines.append("")

        # Create edges for calls
        for caller, callee, label in calls:
            caller_id = self._get_node_id(caller)
            callee_id = self._get_node_id(callee)

            if label:
                lines.append(f"    {caller_id} -->|{label}| {callee_id}")
            else:
                lines.append(f"    {caller_id} --> {callee_id}")

        # Add styling
        lines.append("")
        lines.append("    classDef entry fill:#90EE90,stroke:#333,stroke-width:3px")
        lines.append("    classDef regular fill:#87CEEB,stroke:#333,stroke-width:2px")
        lines.append("    classDef private fill:#FFE4B5,stroke:#333,stroke-width:1px")
        lines.append("    classDef magic fill:#DDA0DD,stroke:#333,stroke-width:2px")

        if entry_functions:
            lines.append(f"    class {','.join(entry_functions)} entry")
        if regular_functions:
            lines.append(f"    class {','.join(regular_functions)} regular")

        return "\n".join(lines)

    def _sanitize_node_id(self, identifier: str) -> str:
        """
        Sanitize an identifier to be a valid Mermaid node ID.

        Args:
            identifier: Raw identifier string

        Returns:
            Sanitized identifier safe for use as node ID
        """
        # Replace common problematic characters
        sanitized = identifier.replace(".", "_")
        sanitized = sanitized.replace("/", "_")
        sanitized = sanitized.replace("\\", "_")
        sanitized = sanitized.replace("-", "_")
        sanitized = sanitized.replace(" ", "_")
        sanitized = sanitized.replace(":", "_")
        sanitized = sanitized.replace("(", "_")
        sanitized = sanitized.replace(")", "_")
        sanitized = sanitized.replace("[", "_")
        sanitized = sanitized.replace("]", "_")
        sanitized = sanitized.replace("{", "_")
        sanitized = sanitized.replace("}", "_")
        sanitized = sanitized.replace("<", "_")
        sanitized = sanitized.replace(">", "_")
        sanitized = sanitized.replace(",", "_")
        sanitized = sanitized.replace(";", "_")
        sanitized = sanitized.replace("'", "_")
        sanitized = sanitized.replace('"', "_")
        sanitized = sanitized.replace("`", "_")
        sanitized = sanitized.replace("@", "_")
        sanitized = sanitized.replace("#", "_")
        sanitized = sanitized.replace("$", "_")
        sanitized = sanitized.replace("%", "_")
        sanitized = sanitized.replace("^", "_")
        sanitized = sanitized.replace("&", "_")
        sanitized = sanitized.replace("*", "_")
        sanitized = sanitized.replace("+", "_")
        sanitized = sanitized.replace("=", "_")
        sanitized = sanitized.replace("|", "_")
        sanitized = sanitized.replace("~", "_")
        sanitized = sanitized.replace("!", "_")
        sanitized = sanitized.replace("?", "_")

        # Remove consecutive underscores
        sanitized = re.sub(r"_+", "_", sanitized)

        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")

        # Ensure it doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = f"n_{sanitized}"

        # Ensure it's not empty
        if not sanitized:
            sanitized = "node"

        # Check against reserved keywords
        if sanitized.lower() in self._reserved_keywords:
            sanitized = f"{sanitized}_node"

        return sanitized

    def _sanitize_class_name(self, class_name: str) -> str:
        """
        Sanitize a class name for use in class diagrams.

        Args:
            class_name: Raw class name

        Returns:
            Sanitized class name
        """
        # For class diagrams, we need simpler names
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "", class_name)

        # Ensure it doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = f"C_{sanitized}"

        # Ensure it's not empty
        if not sanitized:
            sanitized = "Class"

        return sanitized

    def _escape_label(self, label: str) -> str:
        """
        Escape special characters in labels for Mermaid.

        Args:
            label: Raw label text

        Returns:
            Escaped label safe for Mermaid
        """
        # Escape ampersand first to avoid double-escaping
        escaped = label.replace("&", "&amp;")
        # Then escape other special characters
        escaped = escaped.replace('"', '\\"')
        escaped = escaped.replace("'", "\\'")
        escaped = escaped.replace("`", "\\`")
        escaped = escaped.replace("[", "&#91;")
        escaped = escaped.replace("]", "&#93;")
        escaped = escaped.replace("{", "&#123;")
        escaped = escaped.replace("}", "&#125;")
        escaped = escaped.replace("<", "&lt;")
        escaped = escaped.replace(">", "&gt;")
        escaped = escaped.replace("|", "&#124;")

        # Limit length to avoid overly long labels
        if len(escaped) > 50:
            escaped = escaped[:47] + "..."

        return escaped

    def _get_node_id(self, identifier: str) -> str:
        """
        Get or create a unique node ID for an identifier.

        Args:
            identifier: Original identifier

        Returns:
            Unique node ID
        """
        # Always return the cached ID for the same identifier
        if identifier in self._node_id_cache:
            return self._node_id_cache[identifier]

        # Generate a unique ID
        sanitized = self._sanitize_node_id(identifier)

        # Ensure uniqueness across all generated IDs
        base_id = sanitized
        counter = 1
        used_ids = set(self._node_id_cache.values())
        while sanitized in used_ids:
            sanitized = f"{base_id}_{counter}"
            counter += 1

        self._node_id_cache[identifier] = sanitized
        return sanitized

    def _extract_module_name(self, path_or_module: str) -> str:
        """
        Extract a clean module name from a file path or module string.

        Args:
            path_or_module: File path or module name

        Returns:
            Clean module name
        """
        # Remove common file extensions
        clean = re.sub(r"\.(py|js|ts|java|cpp|c|h|hpp)$", "", path_or_module)

        # Convert path separators to dots
        clean = clean.replace("/", ".")
        clean = clean.replace("\\", ".")

        # Remove leading dots
        clean = clean.lstrip(".")

        # Remove common prefixes
        prefixes_to_remove = ["src.", "lib.", "pkg.", "app.", "modules."]
        for prefix in prefixes_to_remove:
            if clean.startswith(prefix):
                clean = clean[len(prefix) :]

        # Take last few components if too long
        parts = clean.split(".")
        if len(parts) > 3:
            clean = ".".join(parts[-3:])

        return clean or "module"

    def _is_external_module(self, module_name: str) -> bool:
        """
        Check if a module is external (third-party).

        Args:
            module_name: Module name to check

        Returns:
            True if module appears to be external
        """
        # Common external/system module patterns
        external_patterns = [
            r"^(sys|os|re|json|typing|pathlib|datetime|collections|itertools)",
            r"^(numpy|pandas|matplotlib|scipy|sklearn|tensorflow|torch|keras)",
            r"^(requests|urllib|http|flask|django|fastapi|aiohttp)",
            r"^(pytest|unittest|mock|coverage)",
            r"^(logging|warnings|traceback|inspect)",
            r"^(asyncio|threading|multiprocessing|concurrent)",
            r"^(boto3|azure|google|aws)",
        ]

        for pattern in external_patterns:
            if re.match(pattern, module_name):
                return True

        # Check for version numbers (common in external packages)
        if re.search(r"\d+\.\d+", module_name):
            return True

        # Check for common external package naming patterns
        # Single-level modules without dots are often external, but not always
        if module_name.count(".") == 0:
            # Check if it's a known stdlib module or starts with underscore (private)
            if module_name.startswith("_") and not module_name.startswith("__"):
                return True
            # Don't assume all single-level modules are external
            # Let specific pattern matching above handle known external modules

        return False

    def validate_mermaid_syntax(self, diagram: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that the generated Mermaid syntax is correct.

        Args:
            diagram: Mermaid diagram syntax to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not diagram or not diagram.strip():
                return False, "Empty diagram"

            lines = diagram.strip().split("\n")

            if not lines:
                return False, "Empty diagram"

            # Find the first non-comment line for diagram type validation
            first_content_line = None
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("%%"):
                    first_content_line = stripped
                    break

            if not first_content_line:
                return False, "No content found after comments"

            # Check for valid diagram type declaration
            valid_starts = [
                "graph",
                "flowchart",
                "sequenceDiagram",
                "classDiagram",
                "stateDiagram",
                "erDiagram",
                "gantt",
                "pie",
                "journey",
                "gitGraph",
                "mindmap",
                "timeline",
                "quadrantChart",
                "sankey",
                "xychart",
                "block",
            ]

            if not any(first_content_line.startswith(start) for start in valid_starts):
                return False, f"Invalid diagram type: {first_content_line}"

            # Check for balanced brackets and quotes
            open_brackets = diagram.count("[")
            close_brackets = diagram.count("]")
            if open_brackets != close_brackets:
                return (
                    False,
                    f"Unbalanced brackets: {open_brackets} open, {close_brackets} close",
                )

            # Check for balanced parentheses
            open_parens = diagram.count("(")
            close_parens = diagram.count(")")
            if open_parens != close_parens:
                return (
                    False,
                    f"Unbalanced parentheses: {open_parens} open, {close_parens} close",
                )

            # Check for balanced braces in class diagrams
            if "classDiagram" in first_content_line:
                open_braces = diagram.count("{")
                close_braces = diagram.count("}")
                if open_braces != close_braces:
                    return (
                        False,
                        f"Unbalanced braces: {open_braces} open, {close_braces} close",
                    )

            # Check for valid subgraph blocks
            if "subgraph" in diagram:
                # Only count subgraph declarations (with space after)
                subgraph_pattern = r"\bsubgraph\s+"
                subgraph_count = len(re.findall(subgraph_pattern, diagram))

                # Count all 'end' statements that close blocks
                end_pattern = r"^\s*end\s*$"
                end_count = len(re.findall(end_pattern, diagram, re.MULTILINE))

                if subgraph_count > end_count:
                    return (
                        False,
                        f"Unmatched subgraph blocks: {subgraph_count} subgraphs, {end_count} ends",
                    )

            return True, None

        except Exception as e:
            return False, f"Validation error: {e!s}"

    def format_diagram_with_metadata(
        self, diagram: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format a diagram with metadata comments.

        Args:
            diagram: Mermaid diagram syntax
            metadata: Optional metadata to include

        Returns:
            Formatted diagram with metadata
        """
        lines = []

        # Add metadata as comments if provided
        if metadata:
            lines.append("%% Diagram Metadata")
            lines.append(f"%% Generated: {metadata.get('timestamp', 'Unknown')}")
            lines.append(f"%% Source: {metadata.get('source', 'Code Analysis')}")
            lines.append(f"%% Type: {metadata.get('type', 'Unknown')}")

            if "stats" in metadata:
                lines.append("%% Statistics:")
                for key, value in metadata["stats"].items():
                    lines.append(f"%%   {key}: {value}")

            lines.append("")

        # Add the diagram
        lines.append(diagram)

        return "\n".join(lines)
