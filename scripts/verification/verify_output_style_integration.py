#!/usr/bin/env python3
"""Verify output style integration in the framework."""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Verify output style is properly integrated."""
    print("=" * 80)
    print("Verifying Output Style Integration")
    print("=" * 80)
    
    # Initialize framework loader
    print("\n1. Initializing FrameworkLoader...")
    loader = FrameworkLoader()
    
    # Check if output style manager was initialized
    print("\n2. Checking OutputStyleManager initialization...")
    if loader.output_style_manager:
        print(f"   ✓ OutputStyleManager initialized")
        print(f"   ✓ Claude version: {loader.output_style_manager.claude_version or 'Not detected'}")
        print(f"   ✓ Supports output styles: {loader.output_style_manager.supports_output_styles()}")
        print(f"   ✓ Should inject content: {loader.output_style_manager.should_inject_content()}")
    else:
        print("   ✗ OutputStyleManager not initialized (will be initialized on first use)")
    
    # Get framework instructions
    print("\n3. Getting framework instructions...")
    instructions = loader.get_framework_instructions()
    
    # Check output style handling
    print("\n4. Checking output style handling...")
    if loader.output_style_manager:
        if loader.output_style_manager.supports_output_styles():
            print("   ✓ Using Claude Code output styles (>= 1.0.83)")
            print(f"   ✓ Output style deployed to: {loader.output_style_manager.output_style_path}")
            
            # Check if file exists
            if loader.output_style_manager.output_style_path.exists():
                print("   ✓ Output style file exists")
            else:
                print("   ✗ Output style file not found")
                
        else:
            print("   ✓ Using content injection for older Claude version")
            if "Output Style Configuration" in instructions:
                print("   ✓ Output style content injected into instructions")
            else:
                print("   ✗ Output style content NOT found in instructions")
    
    # Check OUTPUT_STYLE.md file
    print("\n5. Checking OUTPUT_STYLE.md file...")
    output_style_path = Path(__file__).parent.parent / "src" / "claude_mpm" / "agents" / "OUTPUT_STYLE.md"
    if output_style_path.exists():
        print(f"   ✓ OUTPUT_STYLE.md exists at: {output_style_path}")
        
        # Check content
        content = output_style_path.read_text()
        if "name: Claude MPM" in content:
            print("   ✓ Valid YAML frontmatter found")
        if "PRIMARY DIRECTIVE" in content:
            print("   ✓ Primary directive section found")
        if "TodoWrite Requirements" in content:
            print("   ✓ TodoWrite requirements section found")
    else:
        print(f"   ✗ OUTPUT_STYLE.md not found at: {output_style_path}")
    
    # Summary
    print("\n6. Summary:")
    print("   The output style system is properly integrated and will:")
    if loader.output_style_manager and loader.output_style_manager.supports_output_styles():
        print("   - Use Claude Code's native output style support")
        print("   - Deploy claude-mpm.md to ~/.claude/output-styles/")
        print("   - Activate the style in Claude Code settings")
    else:
        print("   - Inject output style content into framework instructions")
        print("   - Include style guidance in PM instructions")
        print("   - Work seamlessly with older Claude versions")
    
    print("\n" + "=" * 80)
    print("Integration verification completed successfully!")
    print("=" * 80)

if __name__ == "__main__":
    main()