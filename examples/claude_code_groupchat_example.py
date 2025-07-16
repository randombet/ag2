#!/usr/bin/env python3
"""
Example of using ClaudeCodeAgent in AG2 GroupChat and multi-agent orchestration.

This example demonstrates how the refactored ClaudeCodeAgent works seamlessly
with AG2's orchestration patterns like GroupChat, allowing it to participate
naturally in multi-agent conversations and automatically use its tools when needed.
"""

import asyncio
import os

from autogen import AssistantAgent, GroupChat, GroupChatManager, LLMConfig, UserProxyAgent
from autogen.agentchat.contrib.claude_code_agent import ClaudeCodeAgent


def setup_workspace():
    """Set up workspace for the example."""
    print("Setting up workspace...")

    os.makedirs("./project_workspace", exist_ok=True)

    # Create a sample Python file that needs improvement
    sample_code = """
# A simple calculator with some issues
def calculate(x, y, op):
    if op == "add":
        return x + y
    elif op == "sub":
        return x - y
    elif op == "mul":
        return x * y
    elif op == "div":
        return x / y  # No error handling!
    else:
        return None

# Main function without proper structure
if __name__ == "__main__":
    result = calculate(10, 5, "add")
    print(result)
    result = calculate(10, 0, "div")  # This will cause issues!
    print(result)
"""

    with open("./project_workspace/calculator.py", "w") as f:
        f.write(sample_code)

    print("Workspace setup complete!")


async def groupchat_coding_collaboration():
    """Example of ClaudeCodeAgent working in a GroupChat with other agents."""
    print("\n=== GroupChat Coding Collaboration Example ===")

    # Configure LLM for all agents
    llm_config = LLMConfig(
        model="gpt-4o-mini",
        api_type="openai",
        temperature=0.1,
    )

    # Create various agents for the collaboration
    with llm_config:
        # Project manager agent
        project_manager = AssistantAgent(
            name="project_manager",
            system_message="""You are a project manager who coordinates coding tasks.
            You review requirements, break down tasks, and ensure quality standards.
            When coding tasks come up, you coordinate with the Claude Code agent and code reviewer.""",
            description="Coordinates coding projects and ensures quality standards",
        )

        # Code reviewer agent
        code_reviewer = AssistantAgent(
            name="code_reviewer",
            system_message="""You are a senior code reviewer who focuses on:
            - Code quality and best practices
            - Security considerations
            - Performance optimization
            - Documentation and maintainability

            You work with the Claude Code agent to implement improvements.""",
            description="Reviews code quality, security, and best practices",
        )

        # Claude Code agent - the main coding expert
        claude_coder = ClaudeCodeAgent(
            name="claude_coder",
            llm_config=llm_config,
            working_directory="./project_workspace",
            description="Expert coder using Claude Code CLI for advanced coding tasks",
        )

    # Human user proxy
    user_proxy = UserProxyAgent(
        name="user",
        human_input_mode="TERMINATE",
        code_execution_config={"work_dir": "./project_workspace", "use_docker": False},
        description="Human user who initiates tasks and provides feedback",
    )

    # Create GroupChat
    groupchat = GroupChat(
        agents=[user_proxy, project_manager, claude_coder, code_reviewer],
        messages=[],
        speaker_selection_method="auto",
        max_round=15,
    )

    # Create GroupChat manager
    manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config, name="chat_manager")

    # Start the collaborative coding session
    print("Starting collaborative coding session...")

    task_message = """I have a Python calculator file at ./project_workspace/calculator.py that needs improvement.

Please:
1. Analyze the current code for issues
2. Improve error handling and code quality
3. Add proper documentation and type hints
4. Make the code more robust and maintainable

Work together to create a high-quality solution."""

    # Initiate the GroupChat
    chat_result = await asyncio.create_task(user_proxy.a_initiate_chat(manager, message=task_message))

    return chat_result


async def nested_chat_example():
    """Example using ClaudeCodeAgent in nested chats."""
    print("\n=== Nested Chat Example ===")

    llm_config = LLMConfig(
        model="gpt-4o-mini",
        api_type="openai",
        temperature=0.1,
    )

    with llm_config:
        # Main coordinator agent
        coordinator = AssistantAgent(
            name="coordinator",
            system_message="""You coordinate software development tasks.
            When you need code analysis, generation, or file operations,
            initiate a nested chat with the Claude Code agent.""",
            description="Coordinates development tasks and manages nested conversations",
        )

        # Claude Code agent for nested conversations
        claude_coder = ClaudeCodeAgent(
            name="claude_coder",
            llm_config=llm_config,
            working_directory="./project_workspace",
        )

    # Configure nested chat
    nested_chat_queue = [
        {
            "recipient": claude_coder,
            "message": "Please analyze the calculator.py file and suggest improvements",
            "summary_method": "reflection_with_llm",
            "max_turns": 3,
        }
    ]

    coordinator.register_nested_chats(trigger=claude_coder, chat_queue=nested_chat_queue)

    # User proxy
    user = UserProxyAgent(name="user", human_input_mode="NEVER", code_execution_config=False)

    # Start nested chat conversation
    print("Starting nested chat...")
    result = await asyncio.create_task(
        user.a_initiate_chat(
            coordinator,
            message="I need you to work with the Claude Code agent to improve our calculator.py file",
            max_turns=2,
        )
    )

    return result


async def sequential_chat_example():
    """Example using ClaudeCodeAgent in sequential chats."""
    print("\n=== Sequential Chat Example ===")

    llm_config = LLMConfig(
        model="gpt-4o-mini",
        api_type="openai",
        temperature=0.1,
    )

    with llm_config:
        # Analysis agent
        analyzer = AssistantAgent(
            name="analyzer",
            system_message="You analyze code files and identify issues and improvement opportunities.",
            description="Analyzes code and identifies improvement opportunities",
        )

        # Claude Code agent
        claude_coder = ClaudeCodeAgent(
            name="claude_coder",
            llm_config=llm_config,
            working_directory="./project_workspace",
        )

        # Tester agent
        tester = AssistantAgent(
            name="tester",
            system_message="You create and run tests for code to ensure it works correctly.",
            description="Creates and runs tests for code validation",
        )

    # User proxy
    user = UserProxyAgent(
        name="user",
        human_input_mode="NEVER",
        code_execution_config={"work_dir": "./project_workspace", "use_docker": False},
    )

    # Define sequential chat sequence
    chat_sequence = [
        {
            "recipient": analyzer,
            "message": "Analyze the calculator.py file in the project workspace",
            "max_turns": 2,
            "summary_method": "last_msg",
        },
        {
            "recipient": claude_coder,
            "message": "Based on the analysis, improve the calculator.py file",
            "max_turns": 3,
            "summary_method": "reflection_with_llm",
        },
        {
            "recipient": tester,
            "message": "Create and run tests for the improved calculator",
            "max_turns": 2,
            "summary_method": "last_msg",
        },
    ]

    # Execute sequential chats
    print("Starting sequential chat workflow...")
    results = []
    for chat_config in chat_sequence:
        print(f"\n--- Starting chat with {chat_config['recipient'].name} ---")
        result = await asyncio.create_task(user.a_initiate_chat(**chat_config))
        results.append(result)

    return results


async def main():
    """Main example runner."""
    try:
        # Set up workspace
        setup_workspace()

        print("=== ClaudeCodeAgent GroupChat Integration Examples ===")
        print("These examples show how ClaudeCodeAgent works seamlessly in AG2's multi-agent patterns\n")

        # Run different orchestration examples
        print("1. Running GroupChat collaboration...")
        groupchat_result = await groupchat_coding_collaboration()

        print("\n" + "=" * 60)
        print("2. Running nested chat example...")
        nested_result = await nested_chat_example()

        print("\n" + "=" * 60)
        print("3. Running sequential chat example...")
        sequential_results = await sequential_chat_example()

        print("\n=== All examples completed successfully! ===")
        print(f"GroupChat completed with {len(groupchat_result.chat_history)} messages")
        print(f"Nested chat completed with {len(nested_result.chat_history)} messages")
        print(f"Sequential chats: {len(sequential_results)} conversations completed")

    except Exception as e:
        print(f"Error running examples: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Claude Code CLI is installed: npm install --location=global @anthropic-ai/claude-code")
        print("2. Ensure you have proper API keys configured")
        print("3. Check that the workspace directory is accessible")


if __name__ == "__main__":
    asyncio.run(main())
