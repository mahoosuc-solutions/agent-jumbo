# Task Planner Tool

The **task_planner** tool helps you manage complex multi-step tasks within your conversation. Use it to decompose work into steps, track progress, and stay organized.

## When to Use

Use this tool when:
- A task requires 3 or more distinct steps
- You need to track progress across multiple tool calls
- The task involves sequences like: research → analysis → creation → validation

## Available Actions

### create_plan
Create a step-by-step plan for a complex task.
- **steps** (required): List of step descriptions, e.g. ["Research X", "Analyze Y", "Write report"]

### update_step
Mark a step as complete or failed after executing it.
- **step_number** (required): Which step (1-based)
- **status** (required): "done", "failed", or "skipped"
- **result** (required): Brief result summary

### add_step
Add a new step to the existing plan.
- **description** (required): Step description

### get_progress
Show the current plan status with completion indicators.

## Workflow

1. Analyze the user's request and identify the steps needed
2. Call `create_plan` with a list of 3-8 clear steps
3. Execute each step in order using your other tools (search, code execution, etc.)
4. After each step completes, call `update_step` with the result
5. When all steps are done, use the `response` tool to deliver the final result

## Important Rules

- Execute steps SEQUENTIALLY — complete one before starting the next
- Do NOT delegate to subordinate agents — handle everything yourself
- Each step should map to ONE main tool call
- Always update the plan after each step so progress is tracked
- The plan appears in your context every iteration so you know where you are
- If a step fails, mark it failed and decide whether to retry or skip

## Example

```json
{
    "tool_name": "task_planner",
    "tool_args": {
        "action": "create_plan",
        "steps": [
            "Search for the top 5 AI agent frameworks",
            "Compare their features and capabilities",
            "Analyze pricing and licensing",
            "Write a recommendation summary",
            "Format the final report"
        ]
    }
}
```

Then after completing step 1:
```json
{
    "tool_name": "task_planner",
    "tool_args": {
        "action": "update_step",
        "step_number": 1,
        "status": "done",
        "result": "Found: LangChain, CrewAI, AutoGen, AG2, Semantic Kernel"
    }
}
```
