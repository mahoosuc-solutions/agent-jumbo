# Coordinator Tool

The **coordinator** tool enables multi-LLM task coordination. It decomposes complex tasks into subtasks, dispatches them to the optimal AI provider (Claude, Gemini, Ollama), executes them concurrently, and synthesizes unified results.

## Available Actions

### decompose
Preview how a complex task would be split into subtasks.
- **prompt** (required): The task to decompose
- Returns: subtask breakdown with IDs, types, recommended providers, and dependencies

### dispatch
Decompose AND execute a task with multi-LLM coordination.
- **prompt** (required): The task to execute
- Returns: execution report with per-subtask results, latency, and a synthesized response

### classify
Check which provider would be best for a specific prompt.
- **prompt** (required): The prompt to classify
- Returns: task type, recommended provider, and reason

### provider_health
Show available LLM providers with health status and model information.
- No arguments required
- Returns: provider list with health, registered models, and capabilities

### cost_report
View token usage and spending by provider.
- No arguments required
- Returns: usage statistics from the LLM router

## When to Use

Use the coordinator when:
- A task has multiple independent parts that could benefit from parallel execution
- Different parts need different model strengths (reasoning vs speed vs vision)
- You want to see which provider handles a task best
- The user explicitly asks for multi-LLM coordination

## Example

```json
{
    "tool_name": "coordinator",
    "tool_args": {
        "action": "dispatch",
        "prompt": "Research the latest AI frameworks and write a comparison analysis"
    }
}
```
