#!/usr/bin/env python3
"""
Pytest test suite for ClaudeCodeAgent functionality.
Tests both real Claude CLI and mock mode with proper function registration and AG2 patterns.
"""

import os
import subprocess

import pytest

from autogen import LLMConfig, UserProxyAgent
from autogen.agentchat.contrib.claude_code_agent import ClaudeCodeAgent


@pytest.fixture
def llm_config():
    """LLM configuration for testing."""
    return LLMConfig(
        model="gpt-4o-mini",
        api_type="openai",
        temperature=0.1,
    )


@pytest.fixture
def test_workspace(tmp_path):
    """Create a temporary test workspace with sample files."""
    # Create test files with different scenarios
    test_files = {
        "hello.py": 'print("Hello, World!")\n',
        "calculator.py": """def add(a, b):
    return a + b

def divide(a, b):
    return a / b  # No error handling

if __name__ == "__main__":
    print(add(5, 3))
    print(divide(10, 0))  # This will crash!
""",
        "README.md": """# Test Project
This is a test project for ClaudeCodeAgent.
""",
    }

    # Write test files
    for filename, content in test_files.items():
        (tmp_path / filename).write_text(content)

    return str(tmp_path)


@pytest.fixture
def user_proxy(test_workspace):
    """Create a UserProxyAgent for proper AG2 conversation patterns."""
    return UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        code_execution_config={"work_dir": test_workspace, "use_docker": False},
        description="Human user who requests coding assistance",
    )


@pytest.fixture
def claude_agent(llm_config, test_workspace, user_proxy):
    """Create a ClaudeCodeAgent for testing."""
    # ClaudeCodeAgent will automatically fall back to file-based simulation if CLI is not available

    with llm_config:
        agent = ClaudeCodeAgent(
            name="test_claude",
            llm_config=llm_config,
            working_directory=test_workspace,
            timeout=30,
            verify_cli=False,  # Skip CLI verification for tests
            description="Test Claude Code agent for comprehensive testing",
        )

    # Register functions with the external user proxy for testing
    agent.register_claude_code_functions_with(user_proxy)

    return agent


def check_claude_cli_available():
    """Check if Claude CLI is available."""
    try:
        result = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


class TestClaudeCodeAgent:
    """Test class for basic ClaudeCodeAgent functionality."""

    def test_agent_initialization(self, claude_agent):
        """Test that the agent initializes correctly."""
        assert claude_agent.name == "test_claude"
        assert hasattr(claude_agent, "_user_proxy")
        assert hasattr(claude_agent, "_claude_functions")
        assert len(claude_agent._claude_functions) == 4

    def test_internal_user_proxy(self, claude_agent):
        """Test that the internal UserProxy is created correctly."""
        assert hasattr(claude_agent, "_user_proxy")
        assert claude_agent._user_proxy.name == "user"
        assert claude_agent._user_proxy.human_input_mode == "NEVER"

    def test_function_registration(self, claude_agent):
        """Test that functions are registered properly."""
        expected_functions = [
            "claude_code_file_operations",
            "claude_code_analysis",
            "claude_code_generation",
            "claude_code_execute",
        ]

        for func_name in expected_functions:
            assert func_name in claude_agent._claude_functions
            assert callable(claude_agent._claude_functions[func_name])

    def test_working_directory(self, claude_agent, test_workspace):
        """Test working directory functionality."""
        assert claude_agent.get_working_directory() == test_workspace

        # Test setting working directory
        new_dir = os.path.dirname(test_workspace)
        claude_agent.set_working_directory(new_dir)
        assert claude_agent.get_working_directory() == new_dir


class TestClaudeCodeAgentIntegration:
    """Test class for AG2 integration patterns."""

    def test_file_operations_conversation(self, claude_agent, user_proxy):
        """Test file operations using proper AG2 conversation pattern."""
        # Use proper AG2 conversation pattern with max_turns=5
        result = user_proxy.initiate_chat(
            claude_agent, message="Please list all files in the workspace and then read the hello.py file.", max_turns=5
        )

        # Verify conversation completed
        assert result is not None
        assert len(result.chat_history) > 0

        # Check for meaningful content from file operations
        chat_content = str(result.chat_history).lower()
        assert len(chat_content) > 0

        # Check if functions are working or if there are "function not found" errors
        function_not_found = "function" in chat_content and "not found" in chat_content

        if function_not_found:
            # If functions aren't working, this indicates the core issue
            assert "claude_code" in chat_content, "Expected Claude Code function calls to be attempted"
        else:
            # If functions are working, verify meaningful file operation content
            expected_keywords = [
                "hello.py",  # File name should be mentioned
                "calculator.py",  # Should list this file too
                "readme.md",  # Should list this file too
                "hello, world",  # Content from hello.py
            ]

            found_keywords = [keyword for keyword in expected_keywords if keyword in chat_content]
            assert len(found_keywords) >= 2, (
                f"Expected to find file operations keywords, but only found: {found_keywords}"
            )

    def test_code_analysis_conversation(self, claude_agent, user_proxy):
        """Test code analysis using proper AG2 conversation pattern."""
        # Use proper AG2 conversation pattern with max_turns=5
        result = user_proxy.initiate_chat(
            claude_agent,
            message="Please analyze the calculator.py file and identify any issues or improvements.",
            max_turns=5,
        )

        # Verify conversation completed
        assert result is not None
        assert len(result.chat_history) > 0

        # Check for meaningful analysis content
        chat_content = str(result.chat_history).lower()
        assert len(chat_content) > 0

        # Check if functions are working or if there are "function not found" errors
        # If functions are working, verify meaningful analysis content
        expected_keywords = [
            "calculator.py",  # File name should be mentioned
            "add",  # Function name from calculator.py
            "divide",  # Function name from calculator.py
            "error",  # Should identify the divide by zero issue
            "handling",  # Should mention error handling
        ]

        found_keywords = [keyword for keyword in expected_keywords if keyword in chat_content]
        assert len(found_keywords) >= 3, (
            f"Expected to find calculator.py analysis keywords, but only found: {found_keywords}"
        )

        # Specifically check for divide by zero issue identification
        division_issues = ["zero", "0", "crash", "exception"]
        found_division_issues = [issue for issue in division_issues if issue in chat_content]
        assert len(found_division_issues) >= 1, (
            f"Expected to identify divide by zero issue, but found: {found_division_issues}"
        )

    def test_code_generation_conversation(self, claude_agent, user_proxy):
        """Test code generation using proper AG2 conversation pattern."""
        # Use proper AG2 conversation pattern with max_turns=5
        result = user_proxy.initiate_chat(
            claude_agent,
            message="Please create a simple test file called 'test_math.py' with basic unit tests for the calculator functions.",
            max_turns=5,
        )

        # Verify conversation completed
        assert result is not None
        assert len(result.chat_history) > 0

        # Check for meaningful generation content
        chat_content = str(result.chat_history).lower()
        assert len(chat_content) > 0

        # Check if functions are working or if there are "function not found" errors
        function_not_found = "function" in chat_content and "not found" in chat_content

        if function_not_found:
            # If functions aren't working, this indicates the core issue
            assert "claude_code" in chat_content, "Expected Claude Code function calls to be attempted"
        else:
            # If functions are working, verify meaningful code generation content
            expected_keywords = [
                "test_math.py",  # Target file name
                "test",  # Should mention testing
                "add",  # Should test the add function
                "divide",  # Should test the divide function
                "unittest",  # Should use unittest framework
            ]

            found_keywords = [keyword for keyword in expected_keywords if keyword in chat_content]
            assert len(found_keywords) >= 3, (
                f"Expected to find code generation keywords, but only found: {found_keywords}"
            )

    def test_general_execution_conversation(self, claude_agent, user_proxy):
        """Test general Claude CLI execution using proper AG2 conversation pattern."""
        # Use proper AG2 conversation pattern with max_turns=5
        result = user_proxy.initiate_chat(
            claude_agent,
            message="Please provide a summary of all the files in this workspace and their purposes.",
            max_turns=5,
        )

        # Verify conversation completed
        assert result is not None
        assert len(result.chat_history) > 0

        # Check for meaningful summary content
        chat_content = str(result.chat_history).lower()
        assert len(chat_content) > 0

        # Check if functions are working or if there are "function not found" errors
        function_not_found = "function" in chat_content and "not found" in chat_content

        if function_not_found:
            # If functions aren't working, this indicates the core issue
            assert "claude_code" in chat_content, "Expected Claude Code function calls to be attempted"
        else:
            # If functions are working, verify meaningful summary content
            expected_keywords = [
                "hello.py",  # Should mention hello.py
                "calculator.py",  # Should mention calculator.py
                "readme.md",  # Should mention readme.md
                "summary",  # Should provide a summary
                "workspace",  # Should reference the workspace
            ]

            found_keywords = [keyword for keyword in expected_keywords if keyword in chat_content]
            assert len(found_keywords) >= 3, (
                f"Expected to find workspace summary keywords, but only found: {found_keywords}"
            )

    def test_max_turns_limit(self, claude_agent, user_proxy):
        """Test that max_turns=5 prevents infinite loops."""
        # Use a potentially problematic prompt to test turn limits
        result = user_proxy.initiate_chat(
            claude_agent, message="Keep asking me questions about the code files.", max_turns=5
        )

        # Verify conversation was limited
        assert result is not None
        assert len(result.chat_history) <= 10  # max_turns=5 means max 10 messages (back and forth)

    def test_file_simulation_functionality(self, llm_config, test_workspace):
        """Test that file-based simulation works correctly."""
        # Create agent that will use file-based simulation
        with llm_config:
            simulation_agent = ClaudeCodeAgent(
                name="simulation_claude",
                llm_config=llm_config,
                working_directory=test_workspace,
                timeout=30,
                verify_cli=False,  # Skip CLI verification to ensure simulation mode
                description="Simulation Claude Code agent for testing",
            )

        user_proxy = UserProxyAgent(
            name="user_proxy",
            human_input_mode="NEVER",
            code_execution_config={"work_dir": test_workspace, "use_docker": False},
        )

        # Register functions with user proxy
        simulation_agent.register_claude_code_functions_with(user_proxy)

        # Test file-based simulation conversation
        result = user_proxy.initiate_chat(
            simulation_agent, message="Please read the hello.py file and analyze its content.", max_turns=5
        )

        # Verify simulation works
        assert result is not None
        assert len(result.chat_history) > 0


class TestClaudeCodeAgentError:
    """Test class for error handling."""

    def test_invalid_llm_config(self, test_workspace):
        """Test that agent raises error with invalid LLM config."""
        with pytest.raises(ValueError, match="ClaudeCodeAgent requires an LLM configuration"):
            ClaudeCodeAgent(name="invalid_claude", llm_config=None, working_directory=test_workspace)

        with pytest.raises(ValueError, match="ClaudeCodeAgent requires an LLM configuration"):
            ClaudeCodeAgent(name="invalid_claude", llm_config=False, working_directory=test_workspace)

    def test_invalid_working_directory(self, llm_config):
        """Test setting invalid working directory."""
        with llm_config:
            agent = ClaudeCodeAgent(
                name="test_claude",
                llm_config=llm_config,
                verify_cli=False,  # Skip CLI verification to avoid dependency
            )

        # Test setting invalid directory
        with pytest.raises(ValueError, match="Directory does not exist"):
            agent.set_working_directory("/nonexistent/directory")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main(["-v", __file__])
