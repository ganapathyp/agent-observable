from typing import Any
from agent_framework import WorkflowBuilder, FunctionExecutor  # type: ignore
# Import directly from tools.tools to avoid circular import with core.__init__
from taskpilot.tools.tools import create_task_workflow, notify_external_system_workflow  # type: ignore

def _is_approved(response: Any) -> bool:
    """Check if response contains APPROVE.
    
    The condition receives AgentExecutorResponse from agent executors.
    Need to extract text from agent_run_response.
    """
    # Handle string directly
    if isinstance(response, str):
        return "APPROVE" in response.upper()
    
    # Handle AgentExecutorResponse - extract from agent_run_response
    if hasattr(response, 'agent_run_response'):
        agent_response = response.agent_run_response
        # AgentRunResponse has .text attribute
        if hasattr(agent_response, 'text'):
            text = agent_response.text
            return "APPROVE" in text.upper()
        # Or might have .messages
        if hasattr(agent_response, 'messages') and agent_response.messages:
            last_msg = agent_response.messages[-1]
            if hasattr(last_msg, 'content'):
                content = last_msg.content
                if isinstance(content, str):
                    return "APPROVE" in content.upper()
                if hasattr(content, 'text'):
                    return "APPROVE" in content.text.upper()
    
    # Handle objects with .text attribute
    if hasattr(response, 'text'):
        return "APPROVE" in str(response.text).upper()
    
    # Handle event objects with .data attribute
    if hasattr(response, 'data'):
        data = response.data
        if isinstance(data, str):
            return "APPROVE" in data.upper()
        return "APPROVE" in str(data).upper()
    
    # Fallback: convert to string and check
    response_str = str(response).upper()
    return "APPROVE" in response_str

def build_workflow(planner, reviewer, executor):
    # Wrap tools in FunctionExecutors using workflow-compatible functions
    create_task_executor = FunctionExecutor(create_task_workflow)
    notify_executor = FunctionExecutor(notify_external_system_workflow)
    
    
    builder = WorkflowBuilder()
    
    # Chain planner -> reviewer
    # The planner creates the task (via create_task_workflow if we add it)
    # For now, we'll store tasks when they're created by the executor
    builder.add_chain([planner, reviewer])
    
    # Chain tools: create_task -> notify_external_system
    builder.add_chain([create_task_executor, notify_executor])
    
    # Connect executor to the tool chain
    builder.add_edge(executor, create_task_executor)
    
    # Add conditional edge from reviewer to executor (only if APPROVE)
    builder.add_edge(
        reviewer,
        executor,
        condition=_is_approved
    )
    
    # Set planner as the start executor
    builder.set_start_executor(planner)
    
    return builder.build()
