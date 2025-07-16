#!/usr/bin/env python3
"""
Pytest test suite for standalone Claude Code CLI tools.
Tests the individual CLI functions independent of the ClaudeCodeAgent.
"""

from unittest.mock import MagicMock, patch

import pytest

from autogen.agentchat.contrib.claude_code_cli_tools import (
    _get_claude_code_config,
    _run_claude_code_command,
    _set_claude_code_config,
    claude_code_analysis,
    claude_code_execute,
    claude_code_file_operations,
    claude_code_generation,
)


@pytest.fixture
def test_workspace(tmp_path):
    """Create a temporary test workspace with sample files."""
    # Create test files
    calculator_content = """def add(a, b):
    return a + b

def divide(a, b):
    return a / b  # No error handling for division by zero!

if __name__ == "__main__":
    print(add(5, 3))
    print(divide(10, 0))  # This will crash!
"""

    hello_content = 'print("Hello, World!")\n'
    readme_content = """# Test Project
This is a test project for Claude Code CLI testing.
"""

    # Write test files
    (tmp_path / "calculator.py").write_text(calculator_content)
    (tmp_path / "hello.py").write_text(hello_content)
    (tmp_path / "README.md").write_text(readme_content)

    return str(tmp_path)


@pytest.fixture
def cli_config(test_workspace):
    """Configure Claude Code CLI for testing."""
    original_config = _get_claude_code_config()

    # Set test configuration - CLI will automatically fall back to file-based simulation
    _set_claude_code_config(claude_code_path="claude", working_directory=test_workspace, timeout=30)

    yield test_workspace

    # Restore original configuration
    _set_claude_code_config(**original_config)


class TestClaudeCodeCLIConfig:
    """Test configuration management for Claude Code CLI."""

    def test_get_config(self):
        """Test getting CLI configuration."""
        config = _get_claude_code_config()

        assert isinstance(config, dict)
        assert "claude_code_path" in config
        assert "working_directory" in config
        assert "timeout" in config

    def test_set_config(self):
        """Test setting CLI configuration."""
        original_config = _get_claude_code_config()

        # Set new configuration
        test_config = {"claude_code_path": "test-claude", "working_directory": "/test/dir", "timeout": 60}
        _set_claude_code_config(**test_config)

        # Verify configuration was set
        current_config = _get_claude_code_config()
        for key, value in test_config.items():
            assert current_config[key] == value

        # Restore original configuration
        _set_claude_code_config(**original_config)


class TestClaudeCodeFileOperations:
    """Test file operations CLI function."""

    def test_file_read_operation(self, cli_config):
        """Test reading a file."""
        result = claude_code_file_operations(operation="read", file_path="calculator.py")

        assert result["success"] is True
        assert result["return_code"] == 0
        assert "calculator.py" in result["stdout"]
        # Verify the file content is actually read from the test file
        assert "def add(a, b):" in result["stdout"] or "add" in result["stdout"]
        assert "def divide(a, b):" in result["stdout"] or "divide" in result["stdout"]

    def test_file_list_operation(self, cli_config):
        """Test listing files."""
        result = claude_code_file_operations(operation="list", file_path=".")

        assert result["success"] is True
        assert result["return_code"] == 0
        assert "directory contents" in result["stdout"].lower()

    def test_file_write_operation(self, cli_config):
        """Test writing a file."""
        result = claude_code_file_operations(
            operation="write", file_path="test_output.py", content="print('Hello from test')"
        )

        assert result["success"] is True
        assert result["return_code"] == 0
        assert "successfully" in result["stdout"].lower()

    def test_file_search_operation(self, cli_config):
        """Test searching files."""
        result = claude_code_file_operations(operation="search", file_path=".", content="def add")

        assert result["success"] is True
        assert result["return_code"] == 0

    def test_invalid_operation(self, cli_config):
        """Test invalid file operation."""
        result = claude_code_file_operations(operation="invalid_op", file_path="test.py")

        assert result["success"] is False
        assert "unsupported operation" in result["error"].lower()

    def test_file_operations_with_options(self, cli_config):
        """Test file operations with additional options."""
        result = claude_code_file_operations(operation="read", file_path="calculator.py", options="--verbose")

        assert result["success"] is True


class TestClaudeCodeAnalysis:
    """Test code analysis CLI function."""

    def test_analyze_task(self, cli_config):
        """Test analyzing code."""
        result = claude_code_analysis(task="analyze", target="calculator.py")

        assert result["success"] is True
        assert result["return_code"] == 0
        # Check that the analysis contains meaningful content about the actual file
        stdout_lower = result["stdout"].lower()
        assert "calculator.py" in stdout_lower

        # Check for specific analysis content based on actual file simulation
        assert "add" in stdout_lower or "function" in stdout_lower
        assert "divide" in stdout_lower or "error" in stdout_lower
        # File-based simulation should detect issues
        assert any(keyword in stdout_lower for keyword in ["error", "handling", "issue", "bug", "division", "zero"])

    def test_explain_task(self, cli_config):
        """Test explaining code."""
        result = claude_code_analysis(task="explain", target="calculator.py")

        assert result["success"] is True
        assert result["return_code"] == 0

    def test_review_task(self, cli_config):
        """Test reviewing code."""
        result = claude_code_analysis(task="review", target="calculator.py")

        assert result["success"] is True
        assert result["return_code"] == 0

    def test_debug_task(self, cli_config):
        """Test debugging code."""
        result = claude_code_analysis(task="debug", target="calculator.py")

        assert result["success"] is True
        assert result["return_code"] == 0

    def test_analysis_with_context(self, cli_config):
        """Test analysis with additional context."""
        result = claude_code_analysis(
            task="analyze", target="calculator.py", context="Focus on error handling and edge cases"
        )

        assert result["success"] is True
        assert result["return_code"] == 0

    def test_analysis_with_options(self, cli_config):
        """Test analysis with command options."""
        result = claude_code_analysis(task="analyze", target="calculator.py", options="--detailed --format json")

        assert result["success"] is True
        assert result["return_code"] == 0


class TestClaudeCodeGeneration:
    """Test code generation CLI function."""

    def test_create_task(self, cli_config):
        """Test creating code."""
        result = claude_code_generation(task="create", description="A simple function to calculate factorial")

        assert result["success"] is True
        assert result["return_code"] == 0

    def test_generate_task(self, cli_config):
        """Test generating code."""
        result = claude_code_generation(task="generate", description="Unit tests for calculator functions")

        assert result["success"] is True
        assert result["return_code"] == 0

    def test_scaffold_task(self, cli_config):
        """Test scaffolding code."""
        result = claude_code_generation(task="scaffold", description="A Python class for handling user authentication")

        assert result["success"] is True
        assert result["return_code"] == 0

    def test_generation_with_output_path(self, cli_config):
        """Test generation with output path."""
        result = claude_code_generation(task="create", description="A utility function", output_path="utils.py")

        assert result["success"] is True
        assert result["return_code"] == 0

    def test_generation_with_template(self, cli_config):
        """Test generation with template."""
        result = claude_code_generation(task="create", description="A new class", template="class_template")

        assert result["success"] is True
        assert result["return_code"] == 0

    def test_generation_with_options(self, cli_config):
        """Test generation with additional options."""
        result = claude_code_generation(
            task="create", description="A helper function", options="--with-tests --format python"
        )

        assert result["success"] is True
        assert result["return_code"] == 0


class TestClaudeCodeExecute:
    """Test general Claude Code CLI execution."""

    def test_simple_execution(self, cli_config):
        """Test simple Claude Code execution."""
        result = claude_code_execute(prompt="Analyze the calculator.py file for potential improvements")

        assert result["success"] is True
        assert result["return_code"] == 0

    def test_execution_with_context(self, cli_config):
        """Test execution with additional context."""
        result = claude_code_execute(
            prompt="Create a test file for the calculator", additional_context="Focus on edge cases and error handling"
        )

        assert result["success"] is True
        assert result["return_code"] == 0

    def test_complex_prompt(self, cli_config):
        """Test execution with complex prompt."""
        prompt = """
        Please analyze all Python files in this workspace and:
        1. Identify potential bugs
        2. Suggest improvements
        3. Check for security issues
        4. Recommend testing strategies
        """

        result = claude_code_execute(prompt=prompt)

        assert result["success"] is True
        assert result["return_code"] == 0


class TestClaudeCodeCLICommand:
    """Test the low-level CLI command execution."""

    def test_file_simulation_execution(self, cli_config):
        """Test command execution with file-based simulation."""
        result = _run_claude_code_command(args=["analyze", "calculator.py"], cwd=cli_config, timeout=30)

        assert result["success"] is True
        assert result["return_code"] == 0
        assert "calculator.py" in result["stdout"]
        # Verify analysis content includes actual file analysis
        assert "add" in result["stdout"].lower()
        assert "divide" in result["stdout"].lower()

    @patch("subprocess.run")
    def test_real_command_execution_success(self, mock_run, cli_config):
        """Test successful real command execution."""
        # Configure the mock
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Analysis complete"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        # Temporarily set a real claude path to trigger subprocess.run
        original_config = _get_claude_code_config()
        _set_claude_code_config(claude_code_path="real-claude-command")

        try:
            result = _run_claude_code_command(args=["analyze", "test.py"], timeout=10)

            assert result["success"] is True
            assert result["return_code"] == 0
            assert result["stdout"] == "Analysis complete"
            assert result["stderr"] == ""
        finally:
            # Restore original configuration
            _set_claude_code_config(**original_config)

    @patch("subprocess.run")
    def test_real_command_execution_failure(self, mock_run, cli_config):
        """Test failed real command execution."""
        # Configure the mock for failure
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = ""
        mock_process.stderr = "Error: File not found"
        mock_run.return_value = mock_process

        # Temporarily set a real claude path to trigger subprocess.run
        original_config = _get_claude_code_config()
        _set_claude_code_config(claude_code_path="real-claude-command")

        try:
            result = _run_claude_code_command(args=["analyze", "nonexistent.py"], timeout=10)

            assert result["success"] is False
            assert result["return_code"] == 1
            assert result["stderr"] == "Error: File not found"
        finally:
            # Restore original configuration
            _set_claude_code_config(**original_config)

    @patch("subprocess.run")
    def test_command_timeout(self, mock_run, cli_config):
        """Test command timeout handling."""
        # Configure the mock to raise TimeoutExpired
        from subprocess import TimeoutExpired

        mock_run.side_effect = TimeoutExpired("claude", 5)

        # Temporarily set a real claude path to trigger subprocess.run
        original_config = _get_claude_code_config()
        _set_claude_code_config(claude_code_path="real-claude-command")

        try:
            result = _run_claude_code_command(args=["analyze", "large_file.py"], timeout=5)

            assert result["success"] is False
            assert result["return_code"] == -1
            assert "timed out" in result["stderr"]
        finally:
            # Restore original configuration
            _set_claude_code_config(**original_config)


class TestClaudeCodeIntegration:
    """Integration tests combining multiple CLI functions."""

    def test_analyze_then_generate(self, cli_config):
        """Test analyzing code then generating improvements."""
        # First analyze the code
        analysis_result = claude_code_analysis(task="analyze", target="calculator.py")

        assert analysis_result["success"] is True

        # Then generate improvements based on analysis
        generation_result = claude_code_generation(
            task="create",
            description="Improved calculator with proper error handling",
            output_path="improved_calculator.py",
        )

        assert generation_result["success"] is True

    def test_read_analyze_execute_workflow(self, cli_config):
        """Test a complete workflow: read, analyze, execute."""
        # Read the file
        read_result = claude_code_file_operations(operation="read", file_path="calculator.py")
        assert read_result["success"] is True

        # Analyze the code
        analyze_result = claude_code_analysis(task="analyze", target="calculator.py")
        assert analyze_result["success"] is True

        # Execute a general improvement task
        execute_result = claude_code_execute(prompt="Based on the analysis, suggest specific code improvements")
        assert execute_result["success"] is True

    def test_error_handling_consistency(self, cli_config):
        """Test that all functions handle errors consistently."""
        # Test file operations with invalid operation
        file_result = claude_code_file_operations(operation="invalid", file_path="test.py")
        assert file_result["success"] is False
        assert "error" in file_result or "Error" in str(file_result)

        # All other functions should succeed with file-based simulation
        # Use an existing file for analysis
        analysis_result = claude_code_analysis("analyze", "calculator.py")
        assert analysis_result["success"] is True

        generation_result = claude_code_generation("create", "test function")
        assert generation_result["success"] is True

        execute_result = claude_code_execute("test prompt")
        assert execute_result["success"] is True


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main(["-v", __file__])
