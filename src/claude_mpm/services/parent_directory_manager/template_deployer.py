"""Template deployment functionality for Claude PM Framework.

This module handles template deployment logic including version comparison,
template rendering, and deployment decision making.
"""

import re
import platform
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum

# Import framework detection utilities
from ...utils.framework_detection import is_framework_source_directory


class DeploymentContext(Enum):
    """Context for template deployment operations."""
    FRAMEWORK = "framework"
    PROJECT = "project"
    USER = "user"


class TemplateDeployer:
    """Handles template deployment operations for Claude PM Framework."""
    
    def __init__(self, framework_path: Path, logger):
        """Initialize template deployer.
        
        Args:
            framework_path: Path to framework directory
            logger: Logger instance for output
        """
        self.framework_path = framework_path
        self.logger = logger
    
    def should_skip_deployment(self, target_file: Path, template_content: str, force: bool) -> Tuple[bool, str]:
        """Determine if deployment should be skipped based on version comparison.
        
        Args:
            target_file: Target file path for deployment
            template_content: Template content to deploy
            force: Force deployment regardless of version
            
        Returns:
            Tuple of (should_skip, reason_message)
        """
        if force:
            return False, "Force flag set"
        
        if not target_file.exists():
            return False, "Target file does not exist"
        
        # Check if this is a framework deployment template
        if not self.is_framework_deployment_template(template_content):
            return False, "Not a framework deployment template"
        
        try:
            # Read existing content
            existing_content = target_file.read_text(encoding='utf-8')
            
            # Extract versions
            template_version = self.extract_claude_md_version(template_content)
            existing_version = self.extract_claude_md_version(existing_content)
            
            if not template_version or not existing_version:
                return False, "Could not extract versions for comparison"
            
            # Compare versions
            comparison = self.compare_versions(template_version, existing_version)
            
            if comparison <= 0:
                return True, f"Template version {template_version} is not newer than existing {existing_version}"
            
            return False, f"Template version {template_version} is newer than existing {existing_version}"
            
        except Exception as e:
            self.logger.debug(f"Error during version comparison: {e}")
            return False, f"Error during version comparison: {e}"
    
    def is_framework_deployment_template(self, content: str) -> bool:
        """Check if content is a framework deployment template.
        
        Args:
            content: Content to check
            
        Returns:
            True if content is a framework deployment template
        """
        # Check for the specific deployment header
        return "# Claude PM Framework Configuration - Deployment" in content
    
    def extract_claude_md_version(self, content: str) -> Optional[str]:
        """Extract CLAUDE_MD_VERSION from content.
        
        Args:
            content: Content to extract version from
            
        Returns:
            Version string if found, None otherwise
        """
        # Look for CLAUDE_MD_VERSION in metadata comment
        version_pattern = r'CLAUDE_MD_VERSION:\s*([^\s\n]+)'
        match = re.search(version_pattern, content)
        
        if match:
            return match.group(1).strip()
        
        return None
    
    def compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings.
        
        Handles both semantic versions (e.g., "1.2.3") and 
        framework versions with serial numbers (e.g., "014-004").
        
        Args:
            version1: First version to compare
            version2: Second version to compare
            
        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """
        # First try framework version format (e.g., "014-004")
        framework_pattern = r'^(\d+)-(\d+)$'
        
        match1 = re.match(framework_pattern, version1)
        match2 = re.match(framework_pattern, version2)
        
        if match1 and match2:
            # Compare framework versions
            major1, minor1 = int(match1.group(1)), int(match1.group(2))
            major2, minor2 = int(match2.group(1)), int(match2.group(2))
            
            if major1 != major2:
                return 1 if major1 > major2 else -1
            if minor1 != minor2:
                return 1 if minor1 > minor2 else -1
            return 0
        
        # Try semantic version format (e.g., "1.2.3")
        semantic_pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$'
        
        match1 = re.match(semantic_pattern, version1)
        match2 = re.match(semantic_pattern, version2)
        
        if match1 and match2:
            # Compare semantic versions
            for i in range(1, 4):
                v1 = int(match1.group(i))
                v2 = int(match2.group(i))
                if v1 != v2:
                    return 1 if v1 > v2 else -1
            
            # Compare pre-release versions if present
            pre1 = match1.group(4)
            pre2 = match2.group(4)
            
            if pre1 and not pre2:
                return -1  # pre-release is less than release
            elif not pre1 and pre2:
                return 1   # release is greater than pre-release
            elif pre1 and pre2:
                # Simple string comparison for pre-release
                if pre1 < pre2:
                    return -1
                elif pre1 > pre2:
                    return 1
            
            return 0
        
        # Fallback to string comparison
        if version1 < version2:
            return -1
        elif version1 > version2:
            return 1
        return 0
    
    def get_platform_notes(self) -> str:
        """Get platform-specific notes for the current system.
        
        Returns:
            Platform-specific notes string
        """
        system = platform.system().lower()
        
        if system == 'darwin':
            return """
- **macOS Users**: Ensure Python 3.8+ is installed via Homebrew or official installer
- **Command Shortcuts**: Add aliases to ~/.zshrc or ~/.bash_profile
- **Permissions**: May need to grant Terminal permissions for file access
"""
        elif system == 'linux':
            return """
- **Linux Users**: Ensure Python 3.8+ is installed via package manager
- **Command Shortcuts**: Add aliases to ~/.bashrc or ~/.zshrc
- **Permissions**: Use appropriate user permissions for .claude-pm directories
"""
        elif system == 'windows':
            return """
- **Windows Users**: Ensure Python 3.8+ is installed and added to PATH
- **Command Shortcuts**: Use PowerShell aliases or batch files
- **Permissions**: Run as Administrator if encountering permission issues
"""
        else:
            return """
- **Platform**: Ensure Python 3.8+ is installed and accessible
- **Permissions**: Ensure appropriate file system permissions
"""
    
    def get_deployment_variables(self, deployment_id: str) -> Dict[str, Any]:
        """Get variables for template deployment.
        
        Args:
            deployment_id: Unique deployment identifier
            
        Returns:
            Dictionary of deployment variables
        """
        now = datetime.now()
        
        return {
            'DEPLOYMENT_ID': deployment_id,
            'DEPLOYMENT_DATE': now.isoformat(),
            'PLATFORM_NOTES': self.get_platform_notes(),
            'FRAMEWORK_VERSION': self._get_framework_version(),
            'PYTHON_VERSION': platform.python_version(),
            'SYSTEM': platform.system(),
            'HOSTNAME': platform.node(),
        }
    
    def render_template_content(self, content: str, variables: Dict[str, Any]) -> str:
        """Render template content with handlebars-style variable substitution.
        
        Args:
            content: Template content with {{VARIABLE}} placeholders
            variables: Dictionary of variable replacements
            
        Returns:
            Rendered content with variables substituted
        """
        rendered = content
        
        # Replace handlebars variables
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            rendered = rendered.replace(placeholder, str(value))
        
        return rendered
    
    def _get_framework_version(self) -> str:
        """Get framework version from VERSION file.
        
        Returns:
            Framework version string
        """
        version_file = self.framework_path / "VERSION"
        
        if version_file.exists():
            try:
                return version_file.read_text().strip()
            except Exception:
                pass
        
        # Fallback version
        return "0.7.0"
    
    async def deploy_framework_template(
        self,
        target_directory: Path,
        force: bool = False,
        deduplication_handler=None,
        backup_manager=None,
        state_manager=None,
        quiet: bool = False
    ) -> Tuple[bool, Optional[Path], Optional[str], list]:
        """Deploy framework template with integrated deployment.
        
        Args:
            target_directory: Directory to deploy template to
            force: Force deployment even if version is current
            deduplication_handler: Handler for deduplication operations
            backup_manager: Manager for backup operations
            state_manager: Manager for state operations
            quiet: Whether to suppress info messages
            
        Returns:
            Tuple of (success, target_path, error_message, changes_made)
        """
        from ..framework_claude_md_generator import FrameworkClaudeMdGenerator
        import hashlib
        
        changes_made = []
        # Check for INSTRUCTIONS.md first, fallback to CLAUDE.md for backward compatibility
        target_path = target_directory / "INSTRUCTIONS.md"
        legacy_path = target_directory / "CLAUDE.md"
        
        # If CLAUDE.md exists but not INSTRUCTIONS.md, use CLAUDE.md path for compatibility
        if not target_path.exists() and legacy_path.exists():
            target_path = legacy_path
        backup_path = None
        
        try:
            # Check if we're in the framework source directory
            is_framework, markers = is_framework_source_directory(target_directory)
            if is_framework:
                self.logger.warning(f"🚫 Skipping INSTRUCTIONS.md/CLAUDE.md deployment - detected framework source directory")
                self.logger.debug(f"Framework markers found: {', '.join(markers)}")
                return True, target_path, None, []  # Return success but with no changes
            
            # Run deduplication if handler provided
            if deduplication_handler:
                self.logger.info("🔍 Running INSTRUCTIONS.md/CLAUDE.md deduplication before deployment...")
                dedup_actions = await deduplication_handler()
                if dedup_actions:
                    self.logger.info(f"📋 Deduplication processed {len(dedup_actions)} files")
            
            # Use the generator's deploy_to_parent method
            generator = FrameworkClaudeMdGenerator()
            
            # Set template variables for deployment
            generator.template_variables = self.get_deployment_variables("{{DEPLOYMENT_ID}}")
            
            # Create backup if file exists
            if target_path.exists() and backup_manager:
                existing_content = target_path.read_text()
                
                # Check if existing file is protected
                is_framework_template = self.is_framework_deployment_template(existing_content)
                
                if not is_framework_template:
                    # This is a project development file - PERMANENT PROTECTION
                    error_msg = "Permanent protection active: Existing file is not a framework deployment template - protecting project development file"
                    self.logger.error(f"🚫 PERMANENT PROTECTION: {error_msg}")
                    return False, target_path, error_msg, []
                
                # Create backup since it's a framework template
                # Use parent_directory_manager backup directory
                backups_dir = backup_manager.base_dir / ".claude-pm" / "backups" / "parent_directory_manager"
                backup_path = backup_manager.create_backup(target_path, backups_dir)
                if backup_path and not quiet:
                    self.logger.info(f"📁 Backup created: {backup_path}")
            
            # Deploy using generator
            success, message = generator.deploy_to_parent(target_directory, force=force)
            
            if success:
                changes_made.append(f"Deployed framework template to {target_path}")
                return True, target_path, None, changes_made
            else:
                return False, target_path, f"Deployment failed: {message}", []
                
        except Exception as e:
            self.logger.error(f"Failed to deploy framework template to {target_directory}: {e}")
            return False, target_path, str(e), []
    
    async def install_template(
        self,
        target_directory: Path,
        template_id: str,
        template_variables: Dict[str, Any] = None,
        force: bool = False,
        deduplication_handler=None,
        backup_manager=None,
        state_manager=None,
        quiet: bool = False,
        current_target_file: Optional[Path] = None
    ) -> Tuple[bool, Optional[Path], Optional[str], Optional[str], list]:
        """Install a template to a directory with version checking.
        
        Args:
            target_directory: Directory to install template to
            template_id: Template to install
            template_variables: Variables for template rendering
            force: Force installation even if version is current
            deduplication_handler: Handler for deduplication operations
            backup_manager: Manager for backup operations
            state_manager: Manager for state operations
            quiet: Whether to suppress info messages
            current_target_file: Current target file for version auto-increment
            
        Returns:
            Tuple of (success, target_path, version, error_message, changes_made)
        """
        from ..framework_claude_md_generator import FrameworkClaudeMdGenerator
        import hashlib
        
        changes_made = []
        # Check for INSTRUCTIONS.md first, fallback to CLAUDE.md for backward compatibility
        target_file = target_directory / "INSTRUCTIONS.md"
        legacy_file = target_directory / "CLAUDE.md"
        
        # If CLAUDE.md exists but not INSTRUCTIONS.md, use CLAUDE.md path for compatibility
        if not target_file.exists() and legacy_file.exists():
            target_file = legacy_file
        
        # Check if we're in the framework source directory
        is_framework, markers = is_framework_source_directory(target_directory)
        if is_framework:
            self.logger.warning(f"🚫 Skipping INSTRUCTIONS.md/CLAUDE.md installation - detected framework source directory")
            self.logger.debug(f"Framework markers found: {', '.join(markers)}")
            return True, target_file, None, None, [f"Installation skipped: framework source directory detected"]
        backup_path = None
        
        try:
            # Run deduplication if handler provided
            if deduplication_handler:
                self.logger.info("🔍 Running INSTRUCTIONS.md/CLAUDE.md deduplication before installation...")
                dedup_actions = await deduplication_handler()
                if dedup_actions:
                    self.logger.info(f"📋 Deduplication processed {len(dedup_actions)} files")
            
            # Get template content using generator
            content, template_version = await self._generate_framework_template(
                template_id, current_target_file
            )
            
            if not content:
                raise RuntimeError(
                    "Template manager removed - use Claude Code Task Tool for template management"
                )
            
            # Create backup if file exists
            if target_file.exists() and backup_manager:
                existing_content = target_file.read_text()
                # Use parent_directory_manager backup directory
                backups_dir = backup_manager.base_dir / ".claude-pm" / "backups" / "parent_directory_manager"
                backup_path = backup_manager.create_backup(target_file, backups_dir)
                if backup_path and not quiet:
                    self.logger.info(f"📁 Backup created: {backup_path}")
            
            # Check if deployment should be skipped
            should_skip, skip_reason = self.should_skip_deployment(target_file, content, force)
            is_permanent_protection = False
            
            if target_file.exists():
                existing_content = target_file.read_text()
                if not self.is_framework_deployment_template(existing_content):
                    is_permanent_protection = True
                    skip_reason = "Existing file is not a framework deployment template"
                    should_skip = True
            
            if should_skip:
                if is_permanent_protection:
                    # PERMANENT PROTECTION
                    self.logger.error(f"🚫 PERMANENT PROTECTION: {skip_reason}")
                    return False, target_file, None, f"Permanent protection active: {skip_reason}", []
                elif not force:
                    # OVERRIDABLE PROTECTION
                    self.logger.info(f"Skipped template installation: {skip_reason}")
                    return True, target_file, template_version, None, [f"Deployment skipped: {skip_reason}"]
                else:
                    # FORCE OVERRIDE
                    self.logger.warning(f"⚡ FORCE FLAG ACTIVE: Overriding version protection - {skip_reason}")
            
            # Write the content
            target_file.write_text(content)
            changes_made.append(f"Installed template {template_id} to {target_file}")
            
            if not quiet:
                self.logger.info(f"Successfully installed template {template_id} to {target_file}")
            
            return True, target_file, template_version, None, changes_made
            
        except Exception as e:
            self.logger.error(f"Failed to install template {template_id} to {target_directory}: {e}")
            # Return the appropriate target path
            target_file = target_directory / "INSTRUCTIONS.md"
            if not target_file.exists() and (target_directory / "CLAUDE.md").exists():
                target_file = target_directory / "CLAUDE.md"
            return False, target_file, None, str(e), []
    
    async def _generate_framework_template(
        self, template_id: str, current_target_file: Optional[Path] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """Generate framework template content.
        
        Args:
            template_id: Template identifier
            current_target_file: Current target file for version auto-increment
            
        Returns:
            Tuple of (content, version)
        """
        from ..framework_claude_md_generator import FrameworkClaudeMdGenerator
        
        # Check for framework INSTRUCTIONS.md/CLAUDE.md template
        if template_id in ["parent_directory_claude_md", "claude_md", "deployment_claude"]:
            # Use the generator to create the template
            generator = FrameworkClaudeMdGenerator()
            
            # Set template variables before generation
            generator.template_variables = self.get_deployment_variables("{{DEPLOYMENT_ID}}")
            
            # Check if we have an existing file for version auto-increment
            current_content = None
            if current_target_file and current_target_file.exists():
                current_content = current_target_file.read_text()
            
            # Generate the template content
            content = generator.generate(current_content=current_content)
            
            # Extract the version that was generated
            generated_version = self.extract_claude_md_version(content)
            
            return content, generated_version
        
        return None, None
    
    async def get_framework_template(
        self, 
        template_id: str, 
        current_target_file: Optional[Path],
        backup_manager,
        log_info_func
    ) -> Tuple[Optional[str], Optional[Any]]:
        """Get template from deployment framework path using the new generator.
        
        Args:
            template_id: Template identifier
            current_target_file: Current target file for version auto-increment
            backup_manager: Backup manager instance
            log_info_func: Function to log info messages
            
        Returns:
            Tuple of (content, template_version)
        """
        content, version = await self._generate_framework_template(
            template_id, current_target_file
        )
        
        if content:
            # Maintain backup functionality with the generated content
            # Try INSTRUCTIONS.md first, then fall back to CLAUDE.md
            framework_template_path = self.framework_path / "agents" / "INSTRUCTIONS.md"
            if not framework_template_path.exists():
                framework_template_path = self.framework_path / "agents" / "CLAUDE.md"
            # For wheel installations, check data directory
            if not framework_template_path.exists():
                # Check data directory for both INSTRUCTIONS.md and CLAUDE.md
                data_template_path = self.framework_path / "data" / "agents" / "INSTRUCTIONS.md"
                if not data_template_path.exists():
                    data_template_path = self.framework_path / "data" / "agents" / "CLAUDE.md"
                if data_template_path.exists():
                    framework_template_path = data_template_path
            
            if framework_template_path.exists():
                # BACKUP: Create backup before any operations
                backup_manager.backup_framework_template(framework_template_path)
            
            # Create a simple template version object for compatibility
            class SimpleTemplateVersion:
                def __init__(self, template_id, version, source, created_at, checksum, variables, metadata):
                    self.template_id = template_id
                    self.version = version
                    self.source = source
                    self.created_at = created_at
                    self.checksum = checksum
                    self.variables = variables
                    self.metadata = metadata
            
            template_version = SimpleTemplateVersion(
                template_id=template_id,
                version=version or "deployment-current",
                source="framework-generator",
                created_at=datetime.now(),
                checksum=hashlib.sha256(content.encode()).hexdigest(),
                variables=self.get_deployment_variables("{{DEPLOYMENT_ID}}"),
                metadata={"source": "framework-generator"}
            )
            
            log_info_func(f"Using framework template from generator (version: {version})")
            return content, template_version
        
        return None, None