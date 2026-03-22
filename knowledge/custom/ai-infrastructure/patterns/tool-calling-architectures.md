# Tool Calling Architectures

## Overview

AI agents interact with external systems through tool calls. The architecture of this interaction layer determines security boundaries, reliability, and how easily the system can evolve. This document covers the major patterns, their tradeoffs, and security considerations.

## Pattern 1: Direct Function Calling

The agent runtime directly invokes functions defined in the host application. The LLM returns a structured tool call, and the host executes it in-process.

```python
# Tool definition
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_customer",
            "description": "Look up a customer by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"}
                },
                "required": ["customer_id"]
            }
        }
    }
]

# Execution loop
response = await client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=tools,
)

for tool_call in response.choices[0].message.tool_calls:
    fn = tool_registry[tool_call.function.name]
    result = fn(**json.loads(tool_call.function.arguments))
    messages.append({"role": "tool", "content": json.dumps(result), "tool_call_id": tool_call.id})
```

**Advantages:** Simple, low latency, no network hops.
**Disadvantages:** Tools run in the same process -- a bad tool can crash the agent. No isolation.

## Pattern 2: MCP (Model Context Protocol) Servers

Tools are served by standalone MCP servers that expose capabilities over a standardized protocol. The agent connects to one or more MCP servers and discovers tools dynamically.

```
Agent Runtime
  |-- MCP Client --> MCP Server: Database Tools
  |-- MCP Client --> MCP Server: File System Tools
  |-- MCP Client --> MCP Server: API Integration Tools
```

**Advantages:**
- Tools are isolated in separate processes or containers
- Dynamic discovery: agents can connect to new tool servers at runtime
- Standardized protocol means tool servers are reusable across agents
- Each MCP server can have its own security boundary and resource limits

**Disadvantages:**
- Network overhead for every tool call
- Protocol complexity: need to handle connection lifecycle, reconnection, timeouts
- Tool discovery can lead to prompt bloat if too many tools are exposed

**Implementation considerations:**

```python
class MCPToolRouter:
    def __init__(self):
        self.servers: dict[str, MCPClient] = {}

    async def connect(self, server_name: str, uri: str):
        client = MCPClient(uri)
        await client.initialize()
        self.servers[server_name] = client

    async def list_tools(self) -> list[ToolDefinition]:
        """Aggregate tools from all connected MCP servers."""
        all_tools = []
        for name, client in self.servers.items():
            tools = await client.list_tools()
            for tool in tools:
                tool.metadata["source_server"] = name
            all_tools.extend(tools)
        return all_tools

    async def execute(self, tool_name: str, arguments: dict) -> ToolResult:
        server = self._find_server_for_tool(tool_name)
        return await server.call_tool(tool_name, arguments)
```

## Pattern 3: Webhook-Driven (Async Tools)

For long-running operations, the agent dispatches a request and receives results via webhook callback. The agent loop suspends and resumes when the callback arrives.

```
Agent --> Task Queue --> Worker --> [long operation] --> Webhook --> Agent resumes
```

**When to use:**
- Operations that take minutes or hours (CI/CD pipelines, batch processing, human approvals)
- When the agent should not hold resources while waiting

**Implementation:**

```python
class AsyncToolExecutor:
    def __init__(self, callback_url: str):
        self.callback_url = callback_url
        self.pending: dict[str, asyncio.Future] = {}

    async def execute_async(self, tool_name: str, args: dict) -> str:
        """Dispatch and return a task ID. Result arrives via webhook."""
        task_id = str(uuid.uuid4())
        future = asyncio.get_event_loop().create_future()
        self.pending[task_id] = future

        await self.dispatch(tool_name, args, task_id, self.callback_url)
        return task_id

    async def handle_webhook(self, task_id: str, result: dict):
        """Called when the webhook fires."""
        if task_id in self.pending:
            self.pending[task_id].set_result(result)

    async def wait_for_result(self, task_id: str, timeout: float = 300) -> dict:
        return await asyncio.wait_for(self.pending[task_id], timeout=timeout)
```

## Pattern 4: API Gateway with Tool Proxy

A centralized gateway sits between the agent and all external APIs. The gateway handles authentication, rate limiting, request transformation, and audit logging.

```
Agent --> Tool Proxy Gateway --> External API A
                             --> External API B
                             --> Internal Service C
```

**Advantages:**
- Centralized security policy enforcement
- Rate limiting across all agents
- Request/response logging for audit trails
- Secret management: agents never see API keys

## Security Considerations

### 1. Input Validation

Never trust tool arguments from the LLM. Validate every parameter.

```python
def execute_tool(name: str, args: dict) -> dict:
    schema = tool_schemas[name]
    try:
        validated = schema.validate(args)  # Pydantic, jsonschema, etc.
    except ValidationError as e:
        return {"error": f"Invalid arguments: {e}"}
    return tool_functions[name](**validated)
```

### 2. Permission Boundaries

Tools should operate under the principle of least privilege. A customer support agent should not have access to billing mutation tools.

```python
class ToolPermissionGuard:
    def __init__(self, allowed_tools: set[str], read_only: bool = False):
        self.allowed_tools = allowed_tools
        self.read_only = read_only

    def check(self, tool_name: str, args: dict) -> bool:
        if tool_name not in self.allowed_tools:
            raise PermissionDenied(f"Tool {tool_name} not in allowed set")
        if self.read_only and self._is_mutation(tool_name):
            raise PermissionDenied(f"Read-only mode: cannot call {tool_name}")
        return True
```

### 3. Rate Limiting

Prevent runaway agents from overwhelming downstream services.

```python
class ToolRateLimiter:
    def __init__(self, max_calls_per_minute: int = 60):
        self.limiter = TokenBucket(max_calls_per_minute, period=60)

    async def execute(self, tool_fn, args):
        if not self.limiter.acquire():
            raise RateLimitExceeded("Tool call rate limit exceeded")
        return await tool_fn(**args)
```

### 4. Prompt Injection Defense

Tool outputs can contain adversarial content. Sanitize tool results before feeding them back to the LLM.

```python
def sanitize_tool_output(output: str) -> str:
    """Strip potential prompt injection from tool results."""
    # Remove common injection patterns
    dangerous_patterns = [
        r"ignore previous instructions",
        r"you are now",
        r"system:\s",
    ]
    for pattern in dangerous_patterns:
        output = re.sub(pattern, "[FILTERED]", output, flags=re.IGNORECASE)
    return output
```

### 5. Secret Management

API keys and credentials should never appear in the agent's context window. Use environment-level injection or credential brokering.

```python
# BAD: key in tool definition
tools = [{"function": {"name": "call_api", "parameters": {"api_key": "REDACTED"}}}]  # pragma: allowlist secret

# GOOD: key injected at execution time
def call_api(endpoint: str, payload: dict) -> dict:
    api_key = os.environ["EXTERNAL_API_KEY"]  # Never in LLM context
    return requests.post(endpoint, json=payload, headers={"Authorization": f"Bearer {api_key}"})
```

## Error Handling

Tool calls fail. The agent needs structured error information to recover.

```python
class ToolResult:
    success: bool
    data: dict | None
    error: ToolError | None

class ToolError:
    code: str          # "rate_limited", "not_found", "permission_denied", "timeout"
    message: str       # Human-readable
    retryable: bool    # Should the agent retry?
    retry_after: float | None  # Seconds to wait before retry
```

Provide the error code and retryability flag so the agent can make an informed decision about whether to retry, try a different approach, or escalate.

## Choosing an Architecture

| Factor | Direct | MCP | Webhook | Gateway |
|--------|--------|-----|---------|---------|
| Latency | Lowest | Low | High | Medium |
| Isolation | None | Process-level | Full | Full |
| Security | Manual | Per-server | Per-worker | Centralized |
| Complexity | Low | Medium | High | Medium |
| Dynamic tools | No | Yes | No | No |
| Long-running ops | No | No | Yes | No |

Most production systems use a combination. Direct function calling for simple, trusted tools. MCP servers for isolated, reusable tool packages. Webhook patterns for long-running operations. A gateway for external API access with centralized policy.
