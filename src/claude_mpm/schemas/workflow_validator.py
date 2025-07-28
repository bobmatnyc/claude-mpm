#!/usr/bin/env python3
"""
Ticket Workflow Schema Validator
================================

Utility module for validating and working with ticket workflow schemas.

WHY: This module exists to ensure workflow definitions are valid and consistent
before they are used in the ticketing system. By validating workflows at load
time, we prevent runtime errors and ensure all workflows follow the same structure.

DESIGN DECISIONS:
- Uses jsonschema for validation to leverage existing JSON Schema standards
- Provides both validation and helper functions for common workflow operations
- Returns detailed error messages to help users fix invalid workflows
- Validates business logic beyond just schema structure

Usage:
    from claude_mpm.schemas.workflow_validator import WorkflowValidator
    
    validator = WorkflowValidator()
    
    # Validate a workflow
    errors = validator.validate_workflow(workflow_dict)
    if errors:
        print(f"Validation failed: {errors}")
    
    # Load and validate from file
    workflow = validator.load_workflow_file("standard_workflow.json")
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import jsonschema
    from jsonschema import Draft7Validator, validators
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    logging.warning("jsonschema not available, workflow validation disabled")

logger = logging.getLogger(__name__)


class WorkflowValidator:
    """
    Validates ticket workflow definitions against the schema.
    
    WHY: Ensures workflow definitions are valid before use, preventing
    runtime errors and ensuring consistency across all workflows.
    """
    
    def __init__(self, schema_path: Optional[Path] = None):
        """
        Initialize the workflow validator.
        
        Args:
            schema_path: Path to the workflow schema file. If not provided,
                        uses the default schema location.
        """
        self.schema_path = schema_path or self._get_default_schema_path()
        self.schema = self._load_schema()
        self._validator = None
        
        if JSONSCHEMA_AVAILABLE and self.schema:
            self._validator = Draft7Validator(self.schema)
    
    def _get_default_schema_path(self) -> Path:
        """Get the default path to the workflow schema."""
        return Path(__file__).parent / "ticket_workflow_schema.json"
    
    def _load_schema(self) -> Optional[Dict[str, Any]]:
        """Load the workflow schema from file."""
        try:
            if self.schema_path.exists():
                with open(self.schema_path, 'r') as f:
                    return json.load(f)
            else:
                logger.error(f"Schema file not found: {self.schema_path}")
                return None
        except Exception as e:
            logger.error(f"Failed to load schema: {e}")
            return None
    
    def validate_workflow(self, workflow: Dict[str, Any]) -> List[str]:
        """
        Validate a workflow definition.
        
        WHY: Validates both schema structure and business logic to ensure
        the workflow is not only syntactically correct but also logically
        consistent and usable.
        
        Args:
            workflow: Workflow definition dictionary
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Schema validation
        if JSONSCHEMA_AVAILABLE and self._validator:
            for error in self._validator.iter_errors(workflow):
                errors.append(f"Schema error at {'.'.join(str(p) for p in error.path)}: {error.message}")
        
        # Business logic validation
        if not errors:  # Only validate logic if schema is valid
            logic_errors = self._validate_business_logic(workflow)
            errors.extend(logic_errors)
        
        return errors
    
    def _validate_business_logic(self, workflow: Dict[str, Any]) -> List[str]:
        """
        Validate workflow business logic beyond schema requirements.
        
        WHY: Schema validation ensures structure, but we also need to validate
        that the workflow makes logical sense (e.g., transitions reference
        existing statuses, mappings are consistent, etc.)
        """
        errors = []
        
        # Extract status and resolution IDs
        status_ids = {s['id'] for s in workflow.get('status_states', {}).get('states', [])}
        resolution_ids = {r['id'] for r in workflow.get('resolution_types', {}).get('types', [])}
        
        # Validate default status exists
        default_status = workflow.get('status_states', {}).get('default_status')
        if default_status and default_status not in status_ids:
            errors.append(f"Default status '{default_status}' not found in status definitions")
        
        # Validate transitions reference existing statuses
        for i, transition in enumerate(workflow.get('transitions', {}).get('rules', [])):
            from_status = transition.get('from_status')
            to_status = transition.get('to_status')
            
            if from_status != '*' and from_status not in status_ids:
                errors.append(f"Transition {i}: from_status '{from_status}' not found")
            
            if to_status not in status_ids:
                errors.append(f"Transition {i}: to_status '{to_status}' not found")
        
        # Validate status-resolution mappings
        for i, mapping in enumerate(workflow.get('status_resolution_mapping', {}).get('mappings', [])):
            status_id = mapping.get('status_id')
            if status_id not in status_ids:
                errors.append(f"Status-resolution mapping {i}: status '{status_id}' not found")
            
            # Check resolution IDs (unless wildcard)
            for resolution in mapping.get('allowed_resolutions', []):
                if resolution != '*' and resolution not in resolution_ids:
                    errors.append(f"Status-resolution mapping {i}: resolution '{resolution}' not found")
            
            # Check default resolution exists in allowed resolutions
            default_res = mapping.get('default_resolution')
            allowed_res = mapping.get('allowed_resolutions', [])
            if default_res and '*' not in allowed_res and default_res not in allowed_res:
                errors.append(f"Status-resolution mapping {i}: default resolution '{default_res}' not in allowed resolutions")
        
        # Validate there's at least one initial status
        initial_statuses = [s for s in workflow.get('status_states', {}).get('states', []) 
                           if s.get('category') == 'initial']
        if not initial_statuses:
            errors.append("No initial status defined (category='initial')")
        
        # Validate there's at least one terminal status
        terminal_statuses = [s for s in workflow.get('status_states', {}).get('states', []) 
                            if s.get('category') == 'terminal']
        if not terminal_statuses:
            errors.append("No terminal status defined (category='terminal')")
        
        # Validate escalation rules reference existing statuses
        for i, rule in enumerate(workflow.get('business_rules', {}).get('escalation_rules', [])):
            condition_status = rule.get('condition', {}).get('status')
            if condition_status and condition_status not in status_ids:
                errors.append(f"Escalation rule {i}: condition status '{condition_status}' not found")
            
            action_status = rule.get('action', {}).get('change_status')
            if action_status and action_status not in status_ids:
                errors.append(f"Escalation rule {i}: action status '{action_status}' not found")
        
        return errors
    
    def load_workflow_file(self, filepath: Path) -> Optional[Dict[str, Any]]:
        """
        Load and validate a workflow from file.
        
        Args:
            filepath: Path to workflow JSON file
            
        Returns:
            Validated workflow dictionary or None if invalid
        """
        try:
            with open(filepath, 'r') as f:
                workflow = json.load(f)
            
            errors = self.validate_workflow(workflow)
            if errors:
                logger.error(f"Workflow validation failed for {filepath}:")
                for error in errors:
                    logger.error(f"  - {error}")
                return None
            
            return workflow
            
        except Exception as e:
            logger.error(f"Failed to load workflow from {filepath}: {e}")
            return None
    
    def get_valid_transitions(self, workflow: Dict[str, Any], from_status: str) -> List[Dict[str, Any]]:
        """
        Get valid transitions from a given status.
        
        WHY: Helper function to easily determine what transitions are available
        from a specific status, supporting both specific and wildcard rules.
        
        Args:
            workflow: Workflow definition
            from_status: Current status ID
            
        Returns:
            List of valid transition rules
        """
        transitions = []
        
        for rule in workflow.get('transitions', {}).get('rules', []):
            rule_from = rule.get('from_status')
            if rule_from == from_status or rule_from == '*':
                transitions.append(rule)
        
        return transitions
    
    def get_allowed_resolutions(self, workflow: Dict[str, Any], status: str) -> Tuple[List[str], bool]:
        """
        Get allowed resolutions for a given status.
        
        WHY: Helper function to determine which resolutions are valid for a
        specific status, and whether a resolution is required.
        
        Args:
            workflow: Workflow definition
            status: Status ID
            
        Returns:
            Tuple of (allowed_resolution_ids, is_required)
        """
        for mapping in workflow.get('status_resolution_mapping', {}).get('mappings', []):
            if mapping.get('status_id') == status:
                allowed = mapping.get('allowed_resolutions', [])
                required = mapping.get('requires_resolution', False)
                
                # Handle wildcard
                if '*' in allowed:
                    all_resolutions = [r['id'] for r in workflow.get('resolution_types', {}).get('types', [])]
                    return all_resolutions, required
                
                return allowed, required
        
        return [], False
    
    def validate_transition(self, workflow: Dict[str, Any], from_status: str, 
                          to_status: str, data: Dict[str, Any]) -> List[str]:
        """
        Validate a specific status transition.
        
        WHY: Ensures a proposed transition is valid according to the workflow
        rules and that all required fields are provided.
        
        Args:
            workflow: Workflow definition
            from_status: Current status
            to_status: Target status
            data: Transition data (should include required fields)
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Find applicable transition rules
        valid_transitions = self.get_valid_transitions(workflow, from_status)
        matching_rule = None
        
        for rule in valid_transitions:
            if rule.get('to_status') == to_status:
                matching_rule = rule
                break
        
        if not matching_rule:
            errors.append(f"No valid transition from '{from_status}' to '{to_status}'")
            return errors
        
        # Check required fields
        required_fields = matching_rule.get('required_fields', [])
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Required field '{field}' missing for transition")
        
        # If transitioning to a terminal status, check resolution requirements
        target_status = next((s for s in workflow.get('status_states', {}).get('states', []) 
                             if s['id'] == to_status), None)
        
        if target_status and target_status.get('category') == 'terminal':
            allowed_resolutions, requires_resolution = self.get_allowed_resolutions(workflow, to_status)
            
            if requires_resolution and 'resolution' not in data:
                errors.append(f"Resolution required for status '{to_status}'")
            elif 'resolution' in data and data['resolution'] not in allowed_resolutions:
                errors.append(f"Resolution '{data['resolution']}' not allowed for status '{to_status}'")
        
        return errors


def create_example_workflows():
    """
    Create example workflow files for testing and demonstration.
    
    WHY: Provides ready-to-use workflow examples that demonstrate different
    use cases and configuration options.
    """
    examples_dir = Path(__file__).parent / "examples"
    examples_dir.mkdir(exist_ok=True)
    
    # Bug tracking workflow
    bug_workflow = {
        "schema_version": "1.0.0",
        "workflow_id": "bug_tracking",
        "workflow_version": "1.0.0",
        "metadata": {
            "name": "Bug Tracking Workflow",
            "description": "Workflow optimized for software bug tracking",
            "workflow_type": "bug_tracking"
        },
        "status_states": {
            "states": [
                {"id": "reported", "name": "Reported", "category": "initial"},
                {"id": "confirmed", "name": "Confirmed", "category": "active"},
                {"id": "in_progress", "name": "In Progress", "category": "active"},
                {"id": "fixed", "name": "Fixed", "category": "active"},
                {"id": "verified", "name": "Verified", "category": "terminal"},
                {"id": "closed", "name": "Closed", "category": "terminal"},
                {"id": "rejected", "name": "Rejected", "category": "terminal"}
            ]
        },
        "resolution_types": {
            "types": [
                {"id": "fixed", "name": "Fixed", "category": "successful"},
                {"id": "cannot_reproduce", "name": "Cannot Reproduce", "category": "invalid"},
                {"id": "duplicate", "name": "Duplicate", "category": "invalid"},
                {"id": "by_design", "name": "By Design", "category": "invalid"},
                {"id": "wont_fix", "name": "Won't Fix", "category": "unsuccessful"}
            ]
        },
        "transitions": {
            "rules": [
                {"from_status": "reported", "to_status": "confirmed", "name": "Confirm Bug"},
                {"from_status": "reported", "to_status": "rejected", "name": "Reject"},
                {"from_status": "confirmed", "to_status": "in_progress", "name": "Start Fix"},
                {"from_status": "in_progress", "to_status": "fixed", "name": "Mark Fixed"},
                {"from_status": "fixed", "to_status": "verified", "name": "Verify Fix"},
                {"from_status": "verified", "to_status": "closed", "name": "Close"}
            ]
        },
        "status_resolution_mapping": {
            "mappings": [
                {
                    "status_id": "verified",
                    "allowed_resolutions": ["fixed"],
                    "requires_resolution": true
                },
                {
                    "status_id": "closed",
                    "allowed_resolutions": ["*"],
                    "requires_resolution": true
                },
                {
                    "status_id": "rejected",
                    "allowed_resolutions": ["cannot_reproduce", "duplicate", "by_design", "wont_fix"],
                    "requires_resolution": true
                }
            ]
        }
    }
    
    with open(examples_dir / "bug_tracking_workflow.json", 'w') as f:
        json.dump(bug_workflow, f, indent=2)
    
    logger.info("Created example workflow files")


if __name__ == "__main__":
    # Example usage
    validator = WorkflowValidator()
    
    # Load and validate the standard workflow
    example_path = Path(__file__).parent / "examples" / "standard_workflow.json"
    if example_path.exists():
        workflow = validator.load_workflow_file(example_path)
        if workflow:
            print(f"Successfully loaded workflow: {workflow['metadata']['name']}")
            
            # Test some helper functions
            transitions = validator.get_valid_transitions(workflow, "open")
            print(f"\nValid transitions from 'open': {[t['name'] for t in transitions]}")
            
            resolutions, required = validator.get_allowed_resolutions(workflow, "resolved")
            print(f"\nResolutions for 'resolved' status: {resolutions} (required: {required})")