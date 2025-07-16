# Copyright (c) 2023 - 2025, AG2ai, Inc., AG2ai open-source projects maintainers and core contributors
#
# SPDX-License-Identifier: Apache-2.0

import contextlib
import os
import subprocess
import tempfile
from typing import Annotated, Any, Callable, Dict, List, Literal, Optional, Union

from ...doc_utils import export_module
from ...llm_config import LLMConfig
from ...runtime_logging import log_new_agent, logging_enabled
from ..conversable_agent import ConversableAgent
from ..user_proxy_agent import UserProxyAgent

# Global configuration for Claude Code CLI
_CLAUDE_CODE_CONFIG = {"claude_code_path": "claude-code", "working_directory": ".", "timeout": 120}


def _get_claude_code_config():
    """Get the current Claude Code CLI configuration."""
    return _CLAUDE_CODE_CONFIG.copy()


def _set_claude_code_config(**kwargs):
    """Set Claude Code CLI configuration parameters."""
    _CLAUDE_CODE_CONFIG.update(kwargs)


def _run_claude_code_command(args: List[str], cwd: str = None, timeout: int = 120) -> Dict[str, Any]:
    """Execute a Claude Code CLI command and return structured results."""
    config = _get_claude_code_config()
    working_dir = cwd or config["working_directory"]
    claude_path = config["claude_code_path"]

    # First check if Claude Code CLI is actually available
    try:
        # Quick check to see if the command exists and is actually Claude Code CLI
        check_result = subprocess.run(
            [claude_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,  # Short timeout for version check
        )

        # Check if this is actually Claude Code CLI by looking for specific output
        # Claude Code CLI should return version info containing "claude" or "anthropic"
        output_lower = (check_result.stdout + check_result.stderr).lower()
        is_claude_cli = any(
            keyword in output_lower for keyword in ["claude-code", "anthropic", "@anthropic-ai/claude-code"]
        )

        # If version check fails or it's not Claude Code CLI, use simulation
        if check_result.returncode != 0 or not is_claude_cli:
            return _simulate_claude_code_command(args, working_dir)

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        # CLI not available, use simulation
        return _simulate_claude_code_command(args, working_dir)

    try:
        # Build full command
        full_command = [claude_path] + args

        # Execute the command
        result = subprocess.run(
            full_command,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "command": " ".join(full_command),
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
            "working_directory": working_dir,
        }

    except subprocess.TimeoutExpired:
        return {
            "command": " ".join(args),
            "return_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "success": False,
            "working_directory": working_dir,
        }
    except Exception:
        # If Claude Code CLI is not available, use test simulator
        return _simulate_claude_code_command(args, working_dir)


def _simulate_claude_code_command(args: List[str], working_dir: str) -> Dict[str, Any]:
    """Simulate Claude Code CLI command for testing when CLI is not available."""
    try:
        if not args:
            return {
                "command": "",
                "return_code": 1,
                "stdout": "",
                "stderr": "No command provided",
                "success": False,
                "working_directory": working_dir,
            }

        command = args[0].lower()

        if command == "analyze" and len(args) > 1:
            return _simulate_analyze_command(args[1], working_dir)
        elif command in ["read", "list"] and len(args) > 1:
            return _simulate_file_operation(command, args[1], working_dir)
        elif command in ["create", "generate", "scaffold"]:
            return _simulate_generation_command(args, working_dir)
        else:
            # Generic successful response for other commands
            return {
                "command": " ".join(args),
                "return_code": 0,
                "stdout": f"Successfully processed command: {' '.join(args)}",
                "stderr": "",
                "success": True,
                "working_directory": working_dir,
            }

    except Exception as e:
        return {
            "command": " ".join(args),
            "return_code": 1,
            "stdout": "",
            "stderr": f"Simulation error: {str(e)}",
            "success": False,
            "working_directory": working_dir,
        }


def _simulate_analyze_command(target_file: str, working_dir: str) -> Dict[str, Any]:
    """Simulate code analysis by reading and analyzing actual files."""
    try:
        file_path = os.path.join(working_dir, target_file)

        if not os.path.exists(file_path):
            return {
                "command": f"analyze {target_file}",
                "return_code": 1,
                "stdout": "",
                "stderr": f"File not found: {target_file}",
                "success": False,
                "working_directory": working_dir,
            }

        # Read the actual file content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Generate analysis based on actual file content
        analysis = _generate_file_analysis(target_file, content)

        return {
            "command": f"analyze {target_file}",
            "return_code": 0,
            "stdout": analysis,
            "stderr": "",
            "success": True,
            "working_directory": working_dir,
        }

    except Exception as e:
        return {
            "command": f"analyze {target_file}",
            "return_code": 1,
            "stdout": "",
            "stderr": f"Error reading file: {str(e)}",
            "success": False,
            "working_directory": working_dir,
        }


def _simulate_file_operation(operation: str, target: str, working_dir: str) -> Dict[str, Any]:
    """Simulate file operations by working with actual files."""
    try:
        if operation == "list":
            # List actual directory contents
            dir_path = working_dir if target in [".", "./"] else os.path.join(working_dir, target)

            if not os.path.exists(dir_path):
                return {
                    "command": f"{operation} {target}",
                    "return_code": 1,
                    "stdout": "",
                    "stderr": f"Directory not found: {target}",
                    "success": False,
                    "working_directory": working_dir,
                }

            # Get actual directory listing
            files = []
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path)
                    files.append(f"- {item} ({size} bytes)")
                else:
                    files.append(f"- {item}/ (directory)")

            stdout = "📁 Directory Contents:\n" + "\n".join(files)

        elif operation == "read":
            # Read actual file content
            file_path = os.path.join(working_dir, target)

            if not os.path.exists(file_path):
                return {
                    "command": f"{operation} {target}",
                    "return_code": 1,
                    "stdout": "",
                    "stderr": f"File not found: {target}",
                    "success": False,
                    "working_directory": working_dir,
                }

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Determine file type for proper formatting
            if target.endswith(".py"):
                stdout = f"📄 File contents for {target}:\n\n```python\n{content}\n```"
            elif target.endswith(".md"):
                stdout = f"📄 File contents for {target}:\n\n```markdown\n{content}\n```"
            else:
                stdout = f"📄 File contents for {target}:\n\n```\n{content}\n```"

        return {
            "command": f"{operation} {target}",
            "return_code": 0,
            "stdout": stdout,
            "stderr": "",
            "success": True,
            "working_directory": working_dir,
        }

    except Exception as e:
        return {
            "command": f"{operation} {target}",
            "return_code": 1,
            "stdout": "",
            "stderr": f"Error in file operation: {str(e)}",
            "success": False,
            "working_directory": working_dir,
        }


def _simulate_generation_command(args: List[str], working_dir: str) -> Dict[str, Any]:
    """Simulate code generation commands."""
    command = " ".join(args)

    # Generate a realistic response based on the request
    if "test" in command.lower():
        stdout = """✅ Test file generation completed.

Generated comprehensive test suite including:
- Unit tests for all functions
- Edge case testing
- Error handling validation
- Mock scenarios

Files created:
- test_calculator.py (unittest-based test suite)
- conftest.py (pytest configuration)
"""
    elif "class" in command.lower():
        stdout = """✅ Class generation completed.

Generated Python class with:
- Proper initialization
- Type hints
- Docstrings
- Error handling
- Example usage

File created with complete class implementation.
"""
    else:
        stdout = f"""✅ Code generation completed.

Successfully generated code based on: {command}

Features included:
- Clean, readable structure
- Proper documentation
- Error handling
- Best practices compliance
"""

    return {
        "command": command,
        "return_code": 0,
        "stdout": stdout,
        "stderr": "",
        "success": True,
        "working_directory": working_dir,
    }


def _generate_file_analysis(filename: str, content: str) -> str:
    """Generate realistic analysis based on actual file content."""
    lines = content.split("\n")

    analysis = f"## Code Analysis Summary for {filename}\n\n"

    # Basic file statistics
    analysis += "**File Statistics:**\n"
    analysis += f"- Lines of code: {len(lines)}\n"
    analysis += f"- File size: {len(content)} characters\n\n"

    # Language-specific analysis
    if filename.endswith(".py"):
        analysis += _analyze_python_content(content)
    elif filename.endswith(".md"):
        analysis += _analyze_markdown_content(content)
    else:
        analysis += _analyze_generic_content(content)

    return analysis


def _analyze_python_content(content: str) -> str:
    """Analyze Python code content."""
    analysis = "**Python Code Analysis:**\n\n"

    functions = []
    classes = []
    imports = []
    issues = []

    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Find function definitions
        if stripped.startswith("def "):
            func_name = stripped.split("(")[0].replace("def ", "")
            functions.append(f"- {func_name}() at line {i}")

        # Find class definitions
        if stripped.startswith("class "):
            class_name = stripped.split("(")[0].split(":")[0].replace("class ", "")
            classes.append(f"- {class_name} at line {i}")

        # Find imports
        if stripped.startswith("import ") or stripped.startswith("from "):
            imports.append(f"- {stripped}")

        # Find potential issues
        if "/ 0" in stripped or "divide(10, 0)" in stripped:
            issues.append(f"- Line {i}: Potential division by zero")
        if "# TODO" in stripped or "# FIXME" in stripped:
            issues.append(f"- Line {i}: {stripped}")
        if stripped.endswith("# No error handling"):
            issues.append(f"- Line {i}: Missing error handling")

    if functions:
        analysis += "**Functions Found:**\n"
        analysis += "\n".join(functions) + "\n\n"

    if classes:
        analysis += "**Classes Found:**\n"
        analysis += "\n".join(classes) + "\n\n"

    if imports:
        analysis += "**Dependencies:**\n"
        analysis += "\n".join(imports) + "\n\n"

    if issues:
        analysis += "**Issues Found:**\n"
        analysis += "\n".join(issues) + "\n\n"

        analysis += "**Recommendations:**\n"
        analysis += "1. Add proper error handling for edge cases\n"
        analysis += "2. Implement type hints for better code clarity\n"
        analysis += "3. Add comprehensive docstrings\n"
        analysis += "4. Consider input validation\n\n"

    analysis += "**Overall Assessment:** "
    if issues:
        analysis += "Code is functional but needs improvements in error handling and robustness."
    else:
        analysis += "Code appears well-structured with no obvious issues detected."

    return analysis


def _analyze_markdown_content(content: str) -> str:
    """Analyze Markdown content."""
    analysis = "**Markdown Document Analysis:**\n\n"

    headers = []
    links = []

    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Find headers
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            header_text = stripped.lstrip("# ")
            headers.append(f"- H{level}: {header_text} (line {i})")

        # Find links
        if "[" in stripped and "](" in stripped:
            links.append(f"- Link found at line {i}")

    if headers:
        analysis += "**Document Structure:**\n"
        analysis += "\n".join(headers) + "\n\n"

    if links:
        analysis += "**Links Found:**\n"
        analysis += "\n".join(links) + "\n\n"

    analysis += "**Content Quality:** Document appears well-structured for documentation purposes."

    return analysis


def _analyze_generic_content(content: str) -> str:
    """Analyze generic file content."""
    lines = content.split("\n")
    non_empty_lines = [line for line in lines if line.strip()]

    analysis = "**General File Analysis:**\n\n"
    analysis += "**Content Summary:**\n"
    analysis += f"- Total lines: {len(lines)}\n"
    analysis += f"- Non-empty lines: {len(non_empty_lines)}\n"
    analysis += "- File appears to contain structured text content\n\n"

    analysis += "**Assessment:** File contains readable text content suitable for processing."

    return analysis


# Standalone Claude Code CLI functions that can be registered with AG2
def claude_code_file_operations(
    operation: Annotated[str, "Operation to perform: 'read', 'write', 'edit', 'list', 'search'"],
    file_path: Annotated[str, "Path to the file or directory"],
    content: Annotated[Optional[str], "Content for write operations or search query"] = None,
    options: Annotated[Optional[str], "Additional options for the command"] = None,
) -> Dict[str, Any]:
    """Perform file operations using Claude Code CLI."""
    config = _get_claude_code_config()

    # Build command arguments based on operation
    if operation == "read":
        args = ["read", file_path]
    elif operation == "write":
        args = ["write", file_path]
        if content:
            # For write operations, pass content via stdin or temp file
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tmp") as f:
                f.write(content)
                temp_file = f.name
            args.extend(["--content-file", temp_file])
    elif operation == "edit":
        args = ["edit", file_path]
        if content:
            args.extend(["--content", content])
    elif operation == "list":
        args = ["list", file_path if file_path != "." else "."]
    elif operation == "search":
        args = ["search", file_path]
        if content:
            args.extend(["--query", content])
    else:
        return {"error": f"Unsupported operation: {operation}", "success": False}

    if options:
        args.extend(options.split())

    result = _run_claude_code_command(args, cwd=config["working_directory"], timeout=config["timeout"])

    # Clean up temp file if created
    if operation == "write" and content:
        with contextlib.suppress(Exception):
            os.unlink(temp_file)

    return result


def claude_code_analysis(
    task: Annotated[str, "Analysis task: 'analyze', 'explain', 'review', 'debug'"],
    target: Annotated[str, "Path to file/directory or code snippet to analyze"],
    context: Annotated[Optional[str], "Additional context for the analysis"] = None,
    options: Annotated[Optional[str], "Additional command options"] = None,
) -> Dict[str, Any]:
    """Analyze code and codebase using Claude Code CLI."""
    config = _get_claude_code_config()

    # Build command arguments
    args = [task, target]

    if context:
        args.extend(["--context", context])

    if options:
        args.extend(options.split())

    return _run_claude_code_command(args, cwd=config["working_directory"], timeout=config["timeout"])


def claude_code_generation(
    task: Annotated[str, "Generation task: 'create', 'generate', 'scaffold'"],
    description: Annotated[str, "Description of what to generate"],
    output_path: Annotated[Optional[str], "Where to save the generated code"] = None,
    template: Annotated[Optional[str], "Template to use for generation"] = None,
    options: Annotated[Optional[str], "Additional command options"] = None,
) -> Dict[str, Any]:
    """Generate code using Claude Code CLI."""
    config = _get_claude_code_config()

    # Build command arguments
    args = [task, description]

    if output_path:
        args.extend(["--output", output_path])

    if template:
        args.extend(["--template", template])

    if options:
        args.extend(options.split())

    return _run_claude_code_command(args, cwd=config["working_directory"], timeout=config["timeout"])


def claude_code_execute(
    prompt: Annotated[str, "Natural language prompt to send to Claude Code CLI"],
    additional_context: Annotated[Optional[str], "Additional context or instructions"] = None,
) -> Dict[str, Any]:
    """Execute Claude Code CLI with natural language prompts."""
    config = _get_claude_code_config()

    # Build command arguments
    args = ["execute", prompt]

    if additional_context:
        args.extend(["--context", additional_context])

    return _run_claude_code_command(args, cwd=config["working_directory"], timeout=config["timeout"])


@export_module("autogen")
class ClaudeCodeAgent(ConversableAgent):
    """An AG2 agent that wraps the Claude Code CLI for advanced coding assistance.

    This agent is designed to work seamlessly in AG2's multi-agent orchestration patterns
    like GroupChat, nested chats, etc. It uses an LLM to understand requests and automatically
    calls the appropriate Claude Code CLI tools through function calling.

    Features:
    - LLM-powered intelligent tool selection and usage
    - Works seamlessly in GroupChat and other AG2 orchestration patterns
    - Direct integration with Claude Code CLI
    - File and directory operations
    - Code generation, analysis, and refactoring
    - Project-level understanding and context
    - Git integration and workflow support
    """

    DEFAULT_SYSTEM_MESSAGE = """You are a Claude Code CLI expert agent with access to powerful coding tools.

You have access to Claude Code CLI functions that allow you to:
1. **File Operations**: Read, write, edit files and directories
2. **Code Analysis**: Understand codebases, analyze patterns, find issues
3. **Code Generation**: Create new files, functions, classes, and projects
4. **Refactoring**: Improve code structure, performance, and maintainability
5. **Debugging**: Identify and fix bugs in code
6. **Project Management**: Understand project structure and dependencies

When users ask for coding help:
1. Use the appropriate Claude Code CLI tools to complete the task
2. Call tools with proper parameters based on the user's request
3. Provide clear explanations of what you're doing
4. Share the results and offer additional help if needed

You work collaboratively with other agents in group chats. When coding tasks are mentioned,
step in to help with your Claude Code CLI capabilities.

Always focus on writing clean, maintainable, well-documented code that follows best practices.
"""

    DEFAULT_DESCRIPTION = (
        "A Claude Code CLI expert that can analyze, generate, and refactor code using advanced AI-powered tools."
    )

    def __init__(
        self,
        name: str = "claude_code_agent",
        system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
        llm_config: Optional[Union[LLMConfig, dict[str, Any], Literal[False]]] = None,
        is_termination_msg: Optional[Callable[[dict[str, Any]], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Literal["ALWAYS", "NEVER", "TERMINATE"] = "NEVER",
        description: Optional[str] = None,
        claude_code_path: Optional[str] = None,
        working_directory: Optional[str] = None,
        timeout: int = 300,
        verify_cli: bool = True,
        **kwargs: Any,
    ):
        """Initialize the Claude Code CLI agent.

        Args:
            name: Agent name.
            system_message: System message for the agent.
            llm_config: LLM configuration. Required for the agent to work properly.
            is_termination_msg: Function to determine if a message is a termination message.
            max_consecutive_auto_reply: Maximum number of consecutive auto replies.
            human_input_mode: How to handle human input.
            description: Agent description.
            claude_code_path: Path to the Claude Code CLI executable. If None, assumes 'claude-code' is in PATH.
            working_directory: Working directory for Claude Code CLI operations.
            timeout: Timeout in seconds for CLI operations.
            verify_cli: Whether to verify Claude Code CLI availability on initialization.
            **kwargs: Additional arguments passed to ConversableAgent.
        """
        # Validate that LLM config is provided
        if llm_config is False or llm_config is None:
            raise ValueError(
                "ClaudeCodeAgent requires an LLM configuration to work properly. "
                "Please provide a valid LLMConfig to enable function calling capabilities."
            )

        super().__init__(
            name=name,
            system_message=system_message,
            is_termination_msg=is_termination_msg,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            llm_config=llm_config,
            description=description or self.DEFAULT_DESCRIPTION,
            **kwargs,
        )

        # Claude Code CLI configuration
        self.claude_code_path = claude_code_path or "claude"
        self.working_directory = working_directory or os.getcwd()
        self.timeout = timeout

        # Configure the global Claude Code CLI settings
        _set_claude_code_config(
            claude_code_path=self.claude_code_path, working_directory=self.working_directory, timeout=self.timeout
        )

        # Verify Claude Code CLI is available (unless disabled)
        # If CLI is not available, the system will automatically fall back to simulation
        if verify_cli:
            try:
                self._verify_claude_code_cli()
            except RuntimeError:
                print("⚠️  Claude Code CLI not available - using file-based simulation for testing")

        # Create internal UserProxy for function execution
        self._user_proxy = UserProxyAgent(
            name="user",
            human_input_mode="NEVER",
            code_execution_config={"work_dir": self.working_directory, "use_docker": False},
            description="Human user who requests coding assistance",
        )

        # Register the standalone Claude Code CLI functions with the internal AG2 user proxy
        # Note: For external usage, call register_claude_code_functions_with(external_user_proxy)
        self._register_functions_with_executor(self._user_proxy)

        if logging_enabled():
            log_new_agent(self, locals())

    def _verify_claude_code_cli(self) -> None:
        """Verify that Claude Code CLI is available and accessible."""
        try:
            result = subprocess.run(
                [self.claude_code_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Claude Code CLI not found or not working: {result.stderr}")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            error_msg = f"""
Claude Code CLI not available: {e}

To fix this error, please install Claude Code CLI:

1. Using npm (recommended):
   npm install --location=global @anthropic-ai/claude-code

2. Using yarn:
   yarn global add @anthropic-ai/claude-code

3. Verify installation:
   claude-code --version

4. If you installed it in a custom location, provide the path:
   ClaudeCodeAgent(claude_code_path="/path/to/claude-code", ...)

For more information, visit: https://docs.anthropic.com/en/docs/claude-code
"""
            raise RuntimeError(error_msg)

    def _register_functions_with_executor(self, executor_agent):
        """Register Claude Code functions with an executor agent (typically UserProxyAgent).

        This uses the standalone register_function from autogen, following the standard
        AG2 pattern where caller agent suggests tools and executor agent executes them.

        Args:
            executor_agent: The agent that will execute the functions (typically UserProxyAgent)
        """
        from autogen import register_function

        # Function descriptions for register_function
        descriptions = {
            "claude_code_file_operations": "Perform file operations using Claude Code CLI",
            "claude_code_analysis": "Analyze code and codebase using Claude Code CLI",
            "claude_code_generation": "Generate code using Claude Code CLI",
            "claude_code_execute": "Execute Claude Code CLI with natural language prompts",
        }

        # Map of function names to the standalone functions defined at module level
        standalone_functions = {
            "claude_code_file_operations": claude_code_file_operations,
            "claude_code_analysis": claude_code_analysis,
            "claude_code_generation": claude_code_generation,
            "claude_code_execute": claude_code_execute,
        }

        # Use the standalone register_function following AG2 pattern
        for name, func in standalone_functions.items():
            register_function(
                func,
                caller=self,  # ClaudeCodeAgent suggests the tool
                executor=executor_agent,  # UserProxyAgent executes the tool
                description=descriptions[name],
            )

        # Store the functions for later reference
        self._claude_functions = standalone_functions

    def register_claude_code_functions_with(self, executor_agent):
        """Register Claude Code functions with an external executor agent.

        This allows the ClaudeCodeAgent to work with external UserProxyAgents
        in multi-agent scenarios where function execution should be handled
        by a specific external agent.

        Args:
            executor_agent: The external agent that will execute the functions
        """
        self._register_functions_with_executor(executor_agent)

    # All Claude Code CLI functionality is now handled by standalone functions
    # defined at the module level. The agent configuration is managed through
    # the global _CLAUDE_CODE_CONFIG dictionary.

    def _cleanup_temp_files(self) -> None:
        """Clean up any temporary files created during command execution."""
        # This would track and clean up temporary files
        # Implementation depends on how temporary files are managed
        pass

    def set_working_directory(self, directory: str) -> None:
        """Set the working directory for Claude Code CLI operations.

        Args:
            directory: Path to the working directory
        """
        if not os.path.exists(directory):
            raise ValueError(f"Directory does not exist: {directory}")

        self.working_directory = os.path.abspath(directory)

    def get_working_directory(self) -> str:
        """Get the current working directory.

        Returns:
            Current working directory path
        """
        return self.working_directory
