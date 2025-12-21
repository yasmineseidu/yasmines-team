# Claude Agent SDK Patterns (Python)

**Comprehensive guide to Claude Agent SDK for Python - 2025 Edition**

Official documentation: [Platform Docs](https://platform.claude.com/docs/en/api/agent-sdk/python) | [GitHub](https://github.com/anthropics/claude-agent-sdk-python)

---

## Installation

```bash
pip install claude-agent-sdk
```

**Requirements:** Python 3.10+

**Key feature:** Claude Code CLI bundled automatically, no separate installation needed.

---

## Two Interfaces: When to Use What

### `query()` - One-off Tasks

**Use when:**
- Single, independent questions
- No conversation history needed
- Simple automation scripts
- Fresh start each time

**Cannot do:**
- Continue conversations
- Use custom tools
- Use hooks
- Handle interrupts

```python
from claude_agent_sdk import query, ClaudeAgentOptions
import asyncio

async def main():
    options = ClaudeAgentOptions(
        system_prompt="You are an expert Python developer",
        permission_mode='acceptEdits',
        cwd="/home/user/project"
    )

    async for message in query(
        prompt="Create a Python web server",
        options=options
    ):
        print(message)

asyncio.run(main())
```

### `ClaudeSDKClient` - Continuous Conversations

**Use when:**
- Multi-turn conversations
- Follow-up questions
- Custom tools needed
- Hooks needed
- Response-driven logic
- Manual session control

**Can do:**
- Remember context across queries
- Use custom tools (@tool decorator)
- Use hooks (PreToolUse, PostToolUse, etc.)
- Interrupt mid-execution
- Streaming input/output

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
import asyncio

async def main():
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write"],
        permission_mode='acceptEdits'
    )

    async with ClaudeSDKClient(options=options) as client:
        # First question
        await client.query("What's the capital of France?")
        async for message in client.receive_response():
            print(message)

        # Follow-up - Claude remembers previous context
        await client.query("What's the population?")
        async for message in client.receive_response():
            print(message)

asyncio.run(main())
```

**Rule:** Use `query()` for stateless tasks. Use `ClaudeSDKClient` for everything else.

---

## ClaudeAgentOptions: Complete Reference

```python
from claude_agent_sdk import ClaudeAgentOptions
from pathlib import Path

options = ClaudeAgentOptions(
    # Tools
    allowed_tools=["Read", "Write", "Bash", "Grep", "Glob"],
    disallowed_tools=["WebFetch"],  # Block specific tools

    # System Prompt
    system_prompt="You are a helpful assistant",  # Custom prompt
    # OR use preset:
    # system_prompt={"type": "preset", "preset": "claude_code"},
    # OR extend preset:
    # system_prompt={"type": "preset", "preset": "claude_code", "append": "Additional instructions"},

    # Permissions
    permission_mode='acceptEdits',  # 'default', 'acceptEdits', 'plan', 'bypassPermissions'
    can_use_tool=custom_permission_handler,  # Callable[[str, dict], bool]

    # MCP Servers
    mcp_servers={
        "calculator": sdk_server,  # SDK MCP server
        "external": {  # External subprocess MCP server
            "type": "stdio",
            "command": "python",
            "args": ["-m", "calculator_server"]
        }
    },

    # Hooks
    hooks={
        'PreToolUse': [HookMatcher(matcher='Bash', hooks=[validate_bash])],
        'PostToolUse': [HookMatcher(hooks=[log_tool_use])]
    },

    # Conversation
    continue_conversation=False,  # Continue most recent conversation
    resume="session-id-123",  # Resume specific session
    fork_session=False,  # Fork session instead of continuing
    max_turns=10,  # Limit conversation turns

    # Model & Output
    model="sonnet",  # "sonnet", "opus", "haiku"
    output_format={  # Structured output validation
        "type": "json_schema",
        "schema": {...}
    },

    # Working Directory
    cwd=Path("/path/to/project"),  # str or Path
    add_dirs=["/additional/dir"],  # Additional accessible dirs

    # Settings
    setting_sources=["project"],  # Load .claude settings, CLAUDE.md
    settings="/path/to/settings.json",  # Custom settings file

    # Environment
    env={"API_KEY": "secret"},  # Environment variables

    # Subagents (Programmatic)
    agents={
        "researcher": AgentDefinition(
            description="Research agent for web searches",
            prompt="You are a research specialist",
            tools=["WebSearch", "WebFetch"],
            model="sonnet"
        )
    },

    # Advanced
    include_partial_messages=False,  # Include streaming events
    stderr=lambda msg: print(msg),  # Callback for stderr
    cli_path="/custom/path/to/claude",  # Custom CLI path

    # Sandbox
    sandbox={
        "enabled": True,
        "autoAllowBashIfSandboxed": True,
        "excludedCommands": ["docker"],
        "network": {
            "allowLocalBinding": True
        }
    }
)
```

### Permission Modes

| Mode | Description | Use When |
|------|-------------|----------|
| `default` | Standard prompts for dangerous operations | Production, user approval needed |
| `acceptEdits` | Auto-accept file edits, prompt for commands | Dev workflows, frequent file changes |
| `plan` | Planning mode, no execution | Architecture design, planning |
| `bypassPermissions` | Skip all prompts (DANGEROUS) | CI/CD, automated testing |

### Setting Sources

| Value | Location | Purpose |
|-------|----------|---------|
| `"user"` | `~/.claude/settings.json` | Global user settings |
| `"project"` | `.claude/settings.json` | Project settings (version controlled) |
| `"local"` | `.claude/settings.local.json` | Local overrides (gitignored) |

**Critical:** `setting_sources` defaults to `None` (no filesystem settings loaded). Must include `"project"` to load `CLAUDE.md` files.

```python
# Load CLAUDE.md project instructions
options = ClaudeAgentOptions(
    system_prompt={"type": "preset", "preset": "claude_code"},
    setting_sources=["project"],  # Required for CLAUDE.md
    allowed_tools=["Read", "Write"]
)
```

---

## Custom Tools (SDK MCP Servers)

**In-process MCP servers** - Run tools directly in Python app, no subprocess needed.

### Why SDK MCP Servers?

✅ No subprocess management
✅ Better performance (no IPC overhead)
✅ Simpler deployment (single process)
✅ Easier debugging
✅ Type-safe with Python hints

### Creating Tools

```python
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions
from typing import Any

# Define tool with @tool decorator
@tool("calculate", "Perform mathematical calculations", {"a": float, "b": float, "operation": str})
async def calculate(args: dict[str, Any]) -> dict[str, Any]:
    """Calculate two numbers using specified operation."""
    try:
        a = args["a"]
        b = args["b"]
        op = args["operation"]

        operations = {
            "add": a + b,
            "subtract": a - b,
            "multiply": a * b,
            "divide": a / b if b != 0 else None
        }

        result = operations.get(op)
        if result is None:
            return {
                "content": [{"type": "text", "text": f"Error: Invalid operation or division by zero"}],
                "is_error": True
            }

        return {
            "content": [{"type": "text", "text": f"Result: {result}"}]
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "is_error": True
        }

@tool("get_time", "Get current time", {})
async def get_time(args: dict[str, Any]) -> dict[str, Any]:
    """Get current timestamp."""
    from datetime import datetime
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "content": [{"type": "text", "text": f"Current time: {current_time}"}]
    }

# Create SDK MCP server
calculator = create_sdk_mcp_server(
    name="calculator",
    version="1.0.0",
    tools=[calculate, get_time]
)

# Use with ClaudeSDKClient
options = ClaudeAgentOptions(
    mcp_servers={"calc": calculator},
    allowed_tools=["mcp__calc__calculate", "mcp__calc__get_time"]
)
```

### Tool Input Schema

**Simple type mapping (recommended):**
```python
@tool("greet", "Greet user", {"name": str, "age": int, "active": bool})
```

**JSON Schema (advanced validation):**
```python
@tool("search", "Search products", {
    "type": "object",
    "properties": {
        "query": {"type": "string"},
        "max_results": {"type": "integer", "minimum": 1, "maximum": 100}
    },
    "required": ["query"]
})
```

### Tool Return Format

```python
{
    "content": [
        {"type": "text", "text": "Tool output text"}
    ],
    "is_error": False  # Optional, defaults to False
}
```

### Mixed MCP Servers

```python
from claude_agent_sdk import create_sdk_mcp_server

# In-process
internal = create_sdk_mcp_server("internal", tools=[tool1, tool2])

# External subprocess
external = {
    "type": "stdio",
    "command": "python",
    "args": ["-m", "external_server"],
    "env": {"API_KEY": "secret"}
}

options = ClaudeAgentOptions(
    mcp_servers={
        "internal": internal,
        "external": external
    },
    allowed_tools=[
        "mcp__internal__tool1",
        "mcp__external__search"
    ]
)
```

---

## Hooks: Deterministic Control

**Hooks** allow your application (not Claude) to intervene at specific points for validation, modification, or blocking.

### Supported Hook Events

| Event | When | Use For |
|-------|------|---------|
| `PreToolUse` | Before tool execution | Validate inputs, block dangerous commands |
| `PostToolUse` | After tool execution | Log results, trigger follow-up actions |
| `UserPromptSubmit` | When user submits prompt | Add context, modify prompts |
| `Stop` | When stopping execution | Cleanup, save state |
| `SubagentStop` | When subagent stops | Aggregate subagent results |
| `PreCompact` | Before message compaction | Save important context |

**Not supported in Python:** SessionStart, SessionEnd, Notification

### Hook Callback Signature

```python
async def hook_callback(
    input_data: dict[str, Any],     # Hook-specific data
    tool_use_id: str | None,        # Tool use ID (tool hooks only)
    context: HookContext            # Additional context
) -> dict[str, Any]:
    # Return dict with:
    # - decision: "block" to block action
    # - systemMessage: Add to transcript
    # - hookSpecificOutput: Hook-specific data
    pass
```

### Hook Examples

**Validate bash commands:**
```python
from claude_agent_sdk import HookMatcher, HookContext
from typing import Any

async def validate_bash(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: HookContext
) -> dict[str, Any]:
    """Block dangerous bash commands."""
    if input_data['tool_name'] != 'Bash':
        return {}

    command = input_data['tool_input'].get('command', '')
    dangerous = ['rm -rf /', 'dd if=', 'mkfs']

    for pattern in dangerous:
        if pattern in command:
            return {
                'hookSpecificOutput': {
                    'hookEventName': 'PreToolUse',
                    'permissionDecision': 'deny',
                    'permissionDecisionReason': f'Dangerous command blocked: {pattern}'
                }
            }
    return {}

async def log_tool_use(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: HookContext
) -> dict[str, Any]:
    """Log all tool usage."""
    tool_name = input_data.get('tool_name', 'unknown')
    print(f"[TOOL] {tool_name} used")
    return {}

options = ClaudeAgentOptions(
    hooks={
        'PreToolUse': [
            HookMatcher(matcher='Bash', hooks=[validate_bash], timeout=120),
            HookMatcher(hooks=[log_tool_use])  # Applies to all tools
        ],
        'PostToolUse': [
            HookMatcher(hooks=[log_tool_use])
        ]
    }
)
```

**Add context to prompts:**
```python
async def enrich_prompt(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: HookContext
) -> dict[str, Any]:
    """Add timestamp to all prompts."""
    from datetime import datetime

    original = input_data.get('prompt', '')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        'hookSpecificOutput': {
            'hookEventName': 'UserPromptSubmit',
            'updatedPrompt': f"[{timestamp}] {original}"
        }
    }

options = ClaudeAgentOptions(
    hooks={
        'UserPromptSubmit': [HookMatcher(hooks=[enrich_prompt])]
    }
)
```

### HookMatcher

```python
HookMatcher(
    matcher="Bash|Write",  # Tool name pattern (regex), None = all tools
    hooks=[callback1, callback2],  # List of callbacks
    timeout=60  # Timeout in seconds for all hooks in this matcher
)
```

---

## Message Types

### Core Messages

**`UserMessage`**
```python
@dataclass
class UserMessage:
    content: str | list[ContentBlock]
```

**`AssistantMessage`**
```python
@dataclass
class AssistantMessage:
    content: list[ContentBlock]
    model: str
```

**`SystemMessage`**
```python
@dataclass
class SystemMessage:
    subtype: str
    data: dict[str, Any]
```

**`ResultMessage`**
```python
@dataclass
class ResultMessage:
    subtype: str
    duration_ms: int
    duration_api_ms: int
    is_error: bool
    num_turns: int
    session_id: str
    total_cost_usd: float | None
    usage: dict[str, Any] | None
    result: str | None
```

### Content Blocks

**`TextBlock`** - Plain text
```python
@dataclass
class TextBlock:
    text: str
```

**`ThinkingBlock`** - Extended thinking (Sonnet 4)
```python
@dataclass
class ThinkingBlock:
    thinking: str
    signature: str
```

**`ToolUseBlock`** - Tool invocation
```python
@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]
```

**`ToolResultBlock`** - Tool result
```python
@dataclass
class ToolResultBlock:
    tool_use_id: str
    content: str | list[dict[str, Any]] | None
    is_error: bool | None
```

### Processing Messages

```python
from claude_agent_sdk import (
    AssistantMessage, ResultMessage,
    TextBlock, ToolUseBlock, ToolResultBlock
)

async with ClaudeSDKClient(options) as client:
    await client.query("List files")

    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Text: {block.text}")
                elif isinstance(block, ToolUseBlock):
                    print(f"Using tool: {block.name}")
                    print(f"Input: {block.input}")
                elif isinstance(block, ToolResultBlock):
                    print(f"Tool result: {block.content}")

        elif isinstance(message, ResultMessage):
            print(f"Session: {message.session_id}")
            print(f"Cost: ${message.total_cost_usd}")
            print(f"Turns: {message.num_turns}")
```

---

## Error Handling

```python
from claude_agent_sdk import (
    ClaudeSDKError,        # Base error
    CLINotFoundError,      # Claude Code not installed
    CLIConnectionError,    # Connection failed
    ProcessError,          # Process exited with error
    CLIJSONDecodeError     # JSON parsing failed
)

try:
    async for message in query(prompt="Hello"):
        print(message)

except CLINotFoundError:
    print("Install Claude Code: pip install claude-agent-sdk")

except ProcessError as e:
    print(f"Process failed: exit code {e.exit_code}")
    print(f"Stderr: {e.stderr}")

except CLIJSONDecodeError as e:
    print(f"JSON decode error on line: {e.line}")
    print(f"Original error: {e.original_error}")

except CLIConnectionError:
    print("Failed to connect to Claude Code")

except ClaudeSDKError as e:
    print(f"SDK error: {e}")
```

---

## ClaudeSDKClient Methods

### `__init__(options)`

```python
client = ClaudeSDKClient(options=ClaudeAgentOptions(...))
```

Initialize client with configuration.

### `connect(prompt?)`

```python
await client.connect()  # Connect without initial prompt
await client.connect("Initial prompt")  # Connect with prompt
await client.connect(message_stream())  # Connect with streaming input
```

Establish connection to Claude Code. Optional initial prompt.

### `query(prompt, session_id="default")`

```python
await client.query("What is 2+2?")
await client.query(streaming_input())  # Streaming input
```

Send a new request. Supports string or `AsyncIterable[dict]` for streaming.

### `receive_messages()`

```python
async for message in client.receive_messages():
    print(message)
    # Yields ALL messages until disconnect
```

Receive all messages from Claude as async iterator. Continues until disconnect.

### `receive_response()`

```python
async for message in client.receive_response():
    print(message)
    # Yields messages until ResultMessage
```

Receive messages until and including `ResultMessage`. Use for single turn.

**Important:** Avoid `break` in iteration loops - let iteration complete naturally to prevent asyncio cleanup issues.

### `interrupt()`

```python
await client.interrupt()
```

Send interrupt signal. Only works in streaming mode.

### `disconnect()`

```python
await client.disconnect()
```

Disconnect from Claude Code.

### Context Manager

```python
async with ClaudeSDKClient(options) as client:
    await client.query("Hello")
    async for message in client.receive_response():
        print(message)
# Auto-disconnect on exit
```

Automatic connection/disconnection management.

---

## Advanced Patterns

### Continuous Conversation Interface

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock

class ConversationSession:
    def __init__(self, options: ClaudeAgentOptions = None):
        self.client = ClaudeSDKClient(options)
        self.turn_count = 0

    async def start(self):
        await self.client.connect()
        print("Conversation started. Commands: 'exit', 'interrupt', 'new'")

        while True:
            user_input = input(f"\n[Turn {self.turn_count + 1}] You: ")

            if user_input.lower() == 'exit':
                break
            elif user_input.lower() == 'interrupt':
                await self.client.interrupt()
                continue
            elif user_input.lower() == 'new':
                await self.client.disconnect()
                await self.client.connect()
                self.turn_count = 0
                print("New session started")
                continue

            await self.client.query(user_input)
            self.turn_count += 1

            print(f"[Turn {self.turn_count}] Claude: ", end="")
            async for message in self.client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(block.text, end="")
            print()

        await self.client.disconnect()
```

### Streaming Input

```python
async def message_stream():
    """Generate messages dynamically."""
    yield {"type": "text", "text": "Analyze this data:"}
    await asyncio.sleep(0.5)
    yield {"type": "text", "text": "Temperature: 25°C"}
    await asyncio.sleep(0.5)
    yield {"type": "text", "text": "Humidity: 60%"}

async with ClaudeSDKClient() as client:
    await client.query(message_stream())  # Stream input
    async for message in client.receive_response():
        print(message)
```

### Real-time Progress Monitoring

```python
from claude_agent_sdk import AssistantMessage, ToolUseBlock, ToolResultBlock, TextBlock

async with ClaudeSDKClient(options) as client:
    await client.query("Create 5 sorting algorithm implementations")

    async for message in client.receive_messages():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    if block.name == "Write":
                        print(f"🔨 Creating: {block.input.get('file_path')}")
                elif isinstance(block, ToolResultBlock):
                    print(f"✅ Tool completed")
                elif isinstance(block, TextBlock):
                    print(f"💭 {block.text[:100]}...")

        if hasattr(message, 'subtype') and message.subtype in ['success', 'error']:
            print("🎯 Task completed!")
            break
```

### Custom Permission Handler

```python
async def custom_permission_handler(
    tool_name: str,
    input_data: dict,
    context: dict
) -> dict:
    """Custom authorization logic."""

    # Block system directory writes
    if tool_name == "Write":
        path = input_data.get("file_path", "")
        if path.startswith("/system/"):
            return {
                "behavior": "deny",
                "message": "System directory write not allowed",
                "interrupt": True
            }

    # Redirect config files to sandbox
    if tool_name in ["Write", "Edit"]:
        path = input_data.get("file_path", "")
        if "config" in path:
            safe_path = f"./sandbox/{path}"
            return {
                "behavior": "allow",
                "updatedInput": {**input_data, "file_path": safe_path}
            }

    return {"behavior": "allow", "updatedInput": input_data}

options = ClaudeAgentOptions(
    can_use_tool=custom_permission_handler,
    allowed_tools=["Read", "Write", "Edit"]
)
```

### Programmatic Subagents

```python
from claude_agent_sdk import AgentDefinition

options = ClaudeAgentOptions(
    agents={
        "researcher": AgentDefinition(
            description="Research agent for web searches and data gathering",
            prompt="You are a research specialist. Use WebSearch and WebFetch to gather information.",
            tools=["WebSearch", "WebFetch", "Read"],
            model="sonnet"
        ),
        "coder": AgentDefinition(
            description="Coding agent for implementation tasks",
            prompt="You are an expert Python developer. Write clean, tested code.",
            tools=["Read", "Write", "Edit", "Bash"],
            model="opus"
        ),
        "reviewer": AgentDefinition(
            description="Code review agent",
            prompt="You are a code reviewer. Check for bugs, style, and best practices.",
            tools=["Read", "Grep", "Glob"],
            model="haiku"
        )
    }
)

# Use subagents
async for message in query(
    prompt="Task: Research Python web frameworks, implement a demo, review the code",
    options=options
):
    print(message)
```

### Structured Output Validation

```python
options = ClaudeAgentOptions(
    output_format={
        "type": "json_schema",
        "schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "files_changed": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "tests_passed": {"type": "boolean"}
            },
            "required": ["summary", "files_changed", "tests_passed"]
        }
    }
)
```

### Sandbox Configuration

```python
options = ClaudeAgentOptions(
    sandbox={
        "enabled": True,
        "autoAllowBashIfSandboxed": True,  # Auto-approve in sandbox
        "excludedCommands": ["docker", "kubectl"],  # Always bypass sandbox
        "allowUnsandboxedCommands": True,  # Model can request bypass
        "network": {
            "allowLocalBinding": True,  # Allow dev servers
            "allowUnixSockets": ["/var/run/docker.sock"],
            "allowAllUnixSockets": False
        },
        "ignoreViolations": {
            "file": ["/tmp/*"],  # Ignore violations for temp files
            "network": ["127.0.0.1"]
        }
    }
)
```

---

## Built-in Tools Reference

### File Operations

**Read** - Read file contents
```python
{"file_path": str, "offset": int?, "limit": int?}
# Returns: {"content": str, "total_lines": int, "lines_returned": int}
```

**Write** - Write/create file
```python
{"file_path": str, "content": str}
# Returns: {"message": str, "bytes_written": int, "file_path": str}
```

**Edit** - Replace text in file
```python
{"file_path": str, "old_string": str, "new_string": str, "replace_all": bool?}
# Returns: {"message": str, "replacements": int, "file_path": str}
```

### Search Operations

**Glob** - Find files by pattern
```python
{"pattern": str, "path": str?}
# Returns: {"matches": list[str], "count": int, "search_path": str}
```

**Grep** - Search file contents
```python
{
    "pattern": str,
    "path": str?,
    "glob": str?,
    "output_mode": "content"|"files_with_matches"|"count"?,
    "-i": bool?,  # Case insensitive
    "-n": bool?,  # Line numbers
    "multiline": bool?
}
# Returns: {"matches": [...], "total_matches": int}
```

### Execution

**Bash** - Execute commands
```python
{
    "command": str,
    "timeout": int?,  # milliseconds, max 600000
    "description": str?,
    "run_in_background": bool?
}
# Returns: {"output": str, "exitCode": int, "shellId": str?}
```

**BashOutput** - Get background shell output
```python
{"bash_id": str, "filter": str?}  # filter = regex
# Returns: {"output": str, "status": "running"|"completed"|"failed", "exitCode": int?}
```

**KillBash** - Kill background shell
```python
{"shell_id": str}
# Returns: {"message": str, "shell_id": str}
```

### Web Operations

**WebFetch** - Fetch and analyze web content
```python
{"url": str, "prompt": str}
# Returns: {"response": str, "url": str, "final_url": str?, "status_code": int?}
```

**WebSearch** - Search the web
```python
{"query": str, "allowed_domains": list[str]?, "blocked_domains": list[str]?}
# Returns: {"results": [...], "total_results": int, "query": str}
```

### Notebook Operations

**NotebookEdit** - Edit Jupyter notebooks
```python
{
    "notebook_path": str,
    "cell_id": str?,
    "new_source": str,
    "cell_type": "code"|"markdown"?,
    "edit_mode": "replace"|"insert"|"delete"?
}
# Returns: {"message": str, "edit_type": str, "cell_id": str?, "total_cells": int}
```

### Task Management

**TodoWrite** - Update todo list
```python
{
    "todos": [
        {
            "content": str,
            "status": "pending"|"in_progress"|"completed",
            "activeForm": str
        }
    ]
}
# Returns: {"message": str, "stats": {...}}
```

**Task** - Launch subagent
```python
{"description": str, "prompt": str, "subagent_type": str}
# Returns: {"result": str, "usage": dict?, "total_cost_usd": float?, "duration_ms": int?}
```

### MCP Operations

**ListMcpResources** - List MCP resources
```python
{"server": str?}
# Returns: {"resources": [...], "total": int}
```

**ReadMcpResource** - Read MCP resource
```python
{"server": str, "uri": str}
# Returns: {"contents": [...], "server": str}
```

---

## When to Use What: Decision Matrix

| Scenario | Use | Why |
|----------|-----|-----|
| Single question | `query()` | Simplest, no overhead |
| Multi-turn chat | `ClaudeSDKClient` | Maintains context |
| Custom validation | `ClaudeSDKClient` + hooks | Deterministic control |
| Custom tools | `ClaudeSDKClient` + SDK MCP | In-process tools |
| File operations | Built-in tools (Read/Write/Edit) | Optimized, permissions built-in |
| Search codebase | Grep/Glob | Faster than reading all files |
| Long-running commands | Bash with `run_in_background` | Non-blocking execution |
| API integrations | Custom tools (@tool decorator) | Type-safe, in-process |
| External processes | External MCP servers | When subprocess needed |
| Load project context | `setting_sources=["project"]` | CLAUDE.md, .claude/settings.json |
| Block dangerous ops | Hooks (PreToolUse) | Validate before execution |
| Audit tool usage | Hooks (PostToolUse) | Log all actions |
| Structured outputs | `output_format` with JSON schema | Validate response format |
| Multi-agent workflows | Programmatic agents | Specialized agents |
| CI/CD automation | `permission_mode='bypassPermissions'` | No user prompts |

---

## Best Practices

### 1. Always Use Async/Await

```python
# GOOD
async def main():
    async for message in query(prompt="Hello"):
        print(message)

asyncio.run(main())

# BAD - Don't use synchronous code
for message in query(prompt="Hello"):  # Won't work!
    print(message)
```

### 2. Use Context Managers for Clients

```python
# GOOD
async with ClaudeSDKClient(options) as client:
    await client.query("Hello")
    async for message in client.receive_response():
        print(message)
# Auto-disconnect

# AVOID - Manual management
client = ClaudeSDKClient(options)
await client.connect()
await client.query("Hello")
# ... might forget to disconnect
```

### 3. Avoid Break in Message Iteration

```python
# AVOID - Can cause asyncio cleanup issues
async for message in client.receive_messages():
    if condition:
        break  # Don't do this!

# GOOD - Let iteration complete naturally
found = False
async for message in client.receive_messages():
    if not found and isinstance(message, TargetType):
        # Process message
        found = True
    # Continue iteration
```

### 4. Use Specific Permission Modes

```python
# GOOD - Specific to use case
ClaudeAgentOptions(
    permission_mode='acceptEdits',  # Dev workflow
    allowed_tools=["Read", "Write", "Edit"]
)

# AVOID - Too permissive
ClaudeAgentOptions(
    permission_mode='bypassPermissions',  # Dangerous!
    allowed_tools=["*"]  # Not supported, specify tools
)
```

### 5. Load Project Settings for CLAUDE.md

```python
# GOOD - Loads project instructions
ClaudeAgentOptions(
    system_prompt={"type": "preset", "preset": "claude_code"},
    setting_sources=["project"]  # Required for CLAUDE.md
)

# AVOID - Missing project context
ClaudeAgentOptions(
    system_prompt={"type": "preset", "preset": "claude_code"}
    # No setting_sources = CLAUDE.md not loaded!
)
```

### 6. Use SDK MCP Servers for Custom Tools

```python
# GOOD - In-process, no subprocess
@tool("search", "Search products", {"query": str})
async def search(args): ...

server = create_sdk_mcp_server("api", tools=[search])

# AVOID - External subprocess unless necessary
{
    "type": "stdio",
    "command": "python",
    "args": ["-m", "simple_tool"]  # Overkill for simple tools
}
```

### 7. Validate Tool Inputs with Hooks

```python
# GOOD - Validate before execution
async def validate_bash(input_data, tool_use_id, context):
    command = input_data['tool_input'].get('command', '')
    if is_dangerous(command):
        return {
            'hookSpecificOutput': {
                'hookEventName': 'PreToolUse',
                'permissionDecision': 'deny',
                'permissionDecisionReason': 'Blocked'
            }
        }
    return {}

options = ClaudeAgentOptions(
    hooks={'PreToolUse': [HookMatcher(matcher='Bash', hooks=[validate_bash])]}
)
```

### 8. Handle Errors Gracefully

```python
# GOOD - Specific error handling
try:
    async for message in query(prompt="Hello"):
        print(message)
except CLINotFoundError:
    print("Install: pip install claude-agent-sdk")
except ProcessError as e:
    print(f"Failed: {e.stderr}")
except ClaudeSDKError as e:
    print(f"SDK error: {e}")

# AVOID - Catch-all that hides issues
try:
    async for message in query(prompt="Hello"):
        print(message)
except Exception:  # Too broad!
    pass
```

### 9. Use Appropriate Models for Subagents

```python
# GOOD - Match model to task complexity
agents={
    "architect": AgentDefinition(
        description="High-level design",
        model="opus"  # Complex reasoning
    ),
    "coder": AgentDefinition(
        description="Implementation",
        model="sonnet"  # Balanced
    ),
    "formatter": AgentDefinition(
        description="Code formatting",
        model="haiku"  # Fast, simple task
    )
}
```

### 10. Type Hints for Better IDE Support

```python
# GOOD - Type hints everywhere
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock
)
from typing import Any

async def process_response(client: ClaudeSDKClient) -> str:
    result: str = ""
    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    result += block.text
    return result
```

---

## Common Pitfalls

### ❌ Not Loading CLAUDE.md

```python
# WRONG - CLAUDE.md not loaded
options = ClaudeAgentOptions(
    system_prompt={"type": "preset", "preset": "claude_code"}
)

# CORRECT
options = ClaudeAgentOptions(
    system_prompt={"type": "preset", "preset": "claude_code"},
    setting_sources=["project"]  # Required!
)
```

### ❌ Using query() for Conversations

```python
# WRONG - Each call is new session
async for message in query(prompt="What's the capital of France?"):
    pass
async for message in query(prompt="What's the population?"):
    pass  # Claude doesn't remember previous question!

# CORRECT - Use ClaudeSDKClient
async with ClaudeSDKClient() as client:
    await client.query("What's the capital of France?")
    async for message in client.receive_response():
        pass

    await client.query("What's the population?")  # Remembers context!
    async for message in client.receive_response():
        pass
```

### ❌ Blocking Async Code

```python
# WRONG - Blocking in async function
async def process():
    async for message in query(prompt="Hello"):
        time.sleep(1)  # Blocks entire event loop!

# CORRECT
async def process():
    async for message in query(prompt="Hello"):
        await asyncio.sleep(1)  # Non-blocking
```

### ❌ Not Handling Tool Permissions

```python
# WRONG - Tools allowed but dangerous commands not blocked
options = ClaudeAgentOptions(
    allowed_tools=["Bash"],
    permission_mode='bypassPermissions'  # No validation!
)

# CORRECT - Validate dangerous operations
async def validate(tool, input_data, context):
    if tool == "Bash" and "rm -rf" in input_data.get('command', ''):
        return {"behavior": "deny"}
    return {"behavior": "allow"}

options = ClaudeAgentOptions(
    allowed_tools=["Bash"],
    can_use_tool=validate
)
```

### ❌ Not Specifying Allowed Tools

```python
# WRONG - No tools specified
options = ClaudeAgentOptions()
# Claude can't use any tools!

# CORRECT - Specify needed tools
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Write", "Bash", "Grep"]
)
```

---

## Migration from Custom BaseAgent

**Current project uses custom `BaseAgent` class. When migrating to Claude Agent SDK:**

### Before (Custom BaseAgent)

```python
from src.agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    @property
    def system_prompt(self) -> str:
        return "You are a helpful agent"

    async def process_task(self, task: dict) -> dict:
        # Process task
        result = await self._do_work(task)

        # Handoff to next agent
        task_id = await self.handoff_to(
            target_agent="sales",
            payload={"lead_id": task["lead_id"]},
            priority="high"
        )

        return {"status": "completed", "task_id": task_id}
```

### After (Claude Agent SDK)

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AgentDefinition

# Define agent as configuration
sales_agent = AgentDefinition(
    description="Sales agent for lead conversion",
    prompt="You are a sales specialist. Convert qualified leads to deals.",
    tools=["Read", "Write"],
    model="sonnet"
)

# Use SDK client
options = ClaudeAgentOptions(
    system_prompt="You are a helpful agent",
    agents={"sales": sales_agent},
    allowed_tools=["Read", "Write", "Task"]
)

async with ClaudeSDKClient(options) as client:
    # Process task
    await client.query(f"Process lead: {task}")

    async for message in client.receive_response():
        # SDK handles agent orchestration
        print(message)
```

**Key differences:**
- SDK uses configuration over classes
- Agent handoff via `Task` tool + programmatic agents
- No manual Celery task management needed
- Built-in session management

---

## Sources

- [Official Python SDK Documentation](https://platform.claude.com/docs/en/api/agent-sdk/python)
- [GitHub Repository](https://github.com/anthropics/claude-agent-sdk-python)
- [Claude Agent SDK Overview](https://platform.claude.com/docs/en/api/agent-sdk/overview)
- [Building Agents with Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Claude Agent SDK Best Practices 2025](https://skywork.ai/blog/claude-agent-sdk-best-practices-ai-agents-2025/)
- [Tutorial Repository](https://github.com/kenneth-liao/claude-agent-sdk-intro)
- [Claude Agent SDK Examples](https://github.com/anthropics/claude-agent-sdk-demos)

---

**Last Updated:** 2025-12-06
**SDK Version:** 0.1.x+
**Python:** 3.10+
