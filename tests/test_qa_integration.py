#!/usr/bin/env python3
"""QA Integration Test - Full workflow verification."""

import sys
import tempfile
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.services.agents.deployment import AgentDeploymentService
from claude_mpm.services.agents.registry import DeployedAgentDiscovery
from claude_mpm.services.simple_instructions_synthesizer import SimpleInstructionsSynthesizer
from claude_mpm.services.async_session_logger import AsyncSessionLogger

def test_full_integration():
    """Test the full deploy -> inject -> log workflow."""
    print("=== QA Integration Test: Full Workflow ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_root = Path(tmpdir)
        templates_dir = temp_root / "templates"
        agents_dir = temp_root / "agents" 
        deployment_dir = temp_root / "deployment"
        responses_dir = temp_root / "responses"
        
        # Create template files
        templates_dir.mkdir(parents=True)
        base_template = {
            "role": "test",
            "capabilities": ["testing"],
            "instructions": "Test instructions"
        }
        
        # Create a simple template
        engineer_template = templates_dir / "engineer.md"
        engineer_template.write_text("""# Engineer Agent
Test engineering agent for QA integration test.
""")
        
        # Create base agent
        agents_dir.mkdir(parents=True)
        base_agent_file = agents_dir / "base_agent.json"
        base_agent_file.write_text(json.dumps(base_template, indent=2))
        
        try:
            # Step 1: Deploy agents
            print("Step 1: Deploying agents...")
            deployment_service = AgentDeploymentService(
                templates_dir=templates_dir,
                base_agent_path=base_agent_file
            )
            
            results = deployment_service.deploy_agents(
                target_dir=deployment_dir,
                force_rebuild=True
            )
            
            if not results.get("deployed"):
                print("  ❌ No agents deployed")
                return False
            
            print(f"  ✓ Deployed {len(results['deployed'])} agents")
            
            # Step 2: Test agent discovery and precedence
            print("Step 2: Testing agent discovery...")
            discovery = DeployedAgentDiscovery(deployment_dir)
            agents = discovery.get_available_agents()
            
            if not agents:
                print("  ❌ No agents discovered")
                return False
            
            # Test precedence method
            try:
                precedence = discovery.get_precedence_order()
                print(f"  ✓ Precedence order: {precedence}")
            except Exception as e:
                print(f"  ❌ Precedence method failed: {e}")
                return False
            
            print(f"  ✓ Discovered {len(agents)} agents")
            
            # Step 3: Test instruction synthesis
            print("Step 3: Testing instruction synthesis...")
            synthesizer = SimpleInstructionsSynthesizer()
            
            instructions = synthesizer.synthesize_instructions(
                agent_configs=agents,
                user_prompt="Test prompt for QA integration"
            )
            
            if not instructions or len(instructions) < 100:
                print("  ❌ Instructions synthesis failed or too short")
                return False
            
            print(f"  ✓ Generated {len(instructions)} characters of instructions")
            
            # Step 4: Test response logging with both loggers
            print("Step 4: Testing response logging...")
            
            # AsyncSessionLogger
            async_logger = AsyncSessionLogger(base_dir=responses_dir / "async")
            async_success = async_logger.log_response(
                request_summary="QA integration test request",
                response_content="QA integration test response with deployment results",
                agent="qa_integration_test"
            )
            
            if not async_success:
                print("  ❌ AsyncSessionLogger failed")
                return False
            
            # Flush and check file
            async_logger.flush(timeout=5)
            async_files = list((responses_dir / "async").glob("**/*.json"))
            
            if not async_files:
                print("  ❌ No async log files created")
                return False
                
            print(f"  ✓ Created {len(async_files)} async log files")
            
            # Step 5: Verify log content
            print("Step 5: Verifying log content...")
            
            with open(async_files[0], 'r') as f:
                log_data = json.load(f)
            
            required_fields = ['timestamp', 'session_id', 'metadata']
            missing_fields = [field for field in required_fields if field not in log_data]
            
            if missing_fields:
                print(f"  ❌ Missing required fields: {missing_fields}")
                return False
            
            print(f"  ✓ Log data validated: {list(log_data.keys())}")
            
            print("\n=== Integration Test Results ===")
            print("✅ PASS: Full workflow integration successful")
            
            print(f"\nStatistics:")
            print(f"  - Agents deployed: {len(results['deployed'])}")
            print(f"  - Agents discovered: {len(agents)}")
            print(f"  - Instructions length: {len(instructions)} chars")
            print(f"  - Log files created: {len(async_files)}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Integration test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_full_integration()
    sys.exit(0 if success else 1)