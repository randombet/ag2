#!/usr/bin/env python3
"""
Quick test of ClaudeCodeAgent function calling.
"""

import os

from autogen import LLMConfig
from autogen.agentchat.contrib.claude_code_agent import ClaudeCodeAgent


def test_claude_agent_functions():
    """Test the ClaudeCodeAgent function registration and calling."""
    print("🧪 Testing ClaudeCodeAgent function calling...\n")

    # Configure LLM
    llm_config = LLMConfig(
        model="gpt-4o-mini",
        api_type="openai",
        temperature=0.1,
    )

    # Create workspace
    test_workspace = "./test_workspace"
    os.makedirs(test_workspace, exist_ok=True)

    try:
        # Create ClaudeCodeAgent in mock mode for quick testing
        with llm_config:
            claude_agent = ClaudeCodeAgent(
                name="test_claude",
                llm_config=llm_config,
                working_directory=test_workspace,
                mock_mode=True,  # Use mock for quick test
                timeout=30,
            )

        print(f"✅ Agent created with {len(claude_agent._tools)} registered tools")

        # List the registered tools
        print("\n📋 Registered tools:")
        for tool in claude_agent._tools:
            print(f"   - {tool.name}: {tool.description}")

        # Test direct function call
        print("\n🔧 Testing direct function call...")
        result = claude_agent._claude_code_file_operations_sync(
            operation="read", file_path="test.py", content=None, options=None
        )

        print("✅ Function call successful!")
        print(f"📄 Result preview: {result['stdout'][:100]}...")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Cleanup
        if os.path.exists(test_workspace):
            os.rmdir(test_workspace)


if __name__ == "__main__":
    success = test_claude_agent_functions()
    if success:
        print("\n🎉 All function tests passed!")
    else:
        print("\n💥 Function tests failed.")
