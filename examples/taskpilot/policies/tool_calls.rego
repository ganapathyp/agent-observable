package taskpilot.tool_calls

import future.keywords.if

default allow = false

# Allow create_task tool for PlannerAgent
allow if {
    input.tool_name == "create_task"
    input.agent_type == "PlannerAgent"
    validate_task_params(input.parameters)
}

# Allow notify_external_system with restrictions
allow if {
    input.tool_name == "notify_external_system"
    input.agent_type in ["ExecutorAgent", "ReviewerAgent"]
    not contains(input.parameters.message, "delete")
}

# Block dangerous tool calls
deny[msg] if {
    input.tool_name == "delete_task"
    msg := "delete_task tool is not authorized"
}

# Require human approval for high-risk operations
require_approval if {
    input.tool_name == "create_task"
    input.parameters.priority == "high"
    contains(input.parameters.title, "sensitive")
}

# Validate task parameters
validate_task_params(params) if {
    params.title != ""
    count(params.title) <= 500
    params.priority in ["high", "medium", "low"]
}
