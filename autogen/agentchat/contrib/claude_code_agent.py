# Copyright (c) 2023 - 2025, AG2ai, Inc., AG2ai open-source projects maintainers and core contributors
#
# SPDX-License-Identifier: Apache-2.0

import os
import subprocess
from typing import Any, Callable, Literal, Optional, Union

from ...doc_utils import export_module
from ...llm_config import LLMConfig
from ...runtime_logging import log_new_agent, logging_enabled
from ..conversable_agent import ConversableAgent
from ..user_proxy_agent import UserProxyAgent
from .claude_code_cli_tools import (
    TOOL_DESCRIPTIONS,
    TOOL_FUNCTIONS_MAP,
    _set_claude_code_config,
)


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

        # Internal UserProxy is created only when needed for standalone usage
        self._user_proxy = None
        self._claude_functions = {}

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

        for name, func in TOOL_FUNCTIONS_MAP.items():
            register_function(
                func,
                caller=self,  # ClaudeCodeAgent suggests the tool
                executor=executor_agent,  # UserProxyAgent executes the tool
                description=TOOL_DESCRIPTIONS[name],
            )

        # Store the functions for later reference
        self._claude_functions = TOOL_FUNCTIONS_MAP

    def register_claude_code_functions_with(self, executor_agent):
        """Register Claude Code functions with an external executor agent.

        This allows the ClaudeCodeAgent to work with external UserProxyAgents
        in multi-agent scenarios where function execution should be handled
        by a specific external agent.

        Args:
            executor_agent: The external agent that will execute the functions
        """
        self._register_functions_with_executor(executor_agent)

    def _get_or_create_user_proxy(self):
        """Get or create the internal UserProxy for standalone usage."""
        if self._user_proxy is None:
            self._user_proxy = UserProxyAgent(
                name="user",
                human_input_mode="NEVER",
                code_execution_config={"work_dir": self.working_directory, "use_docker": False},
                description="Human user who requests coding assistance",
            )
            # Register functions with the internal user proxy
            self._register_functions_with_executor(self._user_proxy)
        return self._user_proxy

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
