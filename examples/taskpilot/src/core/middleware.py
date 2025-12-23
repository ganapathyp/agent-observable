import logging
import re
import asyncio
import time
import uuid
from typing import Callable, Awaitable, Optional, Any
from pathlib import Path
from agent_framework import AgentRunContext, TextContent  # type: ignore
from taskpilot.core.task_store import TaskStore, get_task_store, TaskStatus  # type: ignore
from taskpilot.core.types import AgentType  # type: ignore
from taskpilot.core.guardrails.nemo_rails import NeMoGuardrailsWrapper  # type: ignore
from taskpilot.core.guardrails.decision_logger import get_decision_logger  # type: ignore
from taskpilot.core.guardrails.opa_tool_validator import OPAToolValidator  # type: ignore
from taskpilot.core.observability import (  # type: ignore
    RequestContext,
    get_request_id,
    get_metrics_collector,
    get_error_tracker,
    get_tracer,
    TraceContext,
    record_metric,
    record_error
)
from taskpilot.core.metric_names import (  # type: ignore
    WORKFLOW_RUNS,
    WORKFLOW_SUCCESS,
    WORKFLOW_ERRORS,
    WORKFLOW_LATENCY_MS,
    agent_invocations,
    agent_success,
    agent_errors,
    agent_latency_ms,
    agent_guardrails_blocked,
    agent_guardrails_output_blocked,
    agent_policy_violations,
    POLICY_VIOLATIONS_TOTAL,
    TASKS_CREATED,
    TASKS_APPROVED,
    TASKS_REJECTED,
    TASKS_REVIEW,
    TASKS_EXECUTED,
    TASKS_REVIEWER_OUTPUT_EMPTY,
    TASKS_NO_PENDING_FOR_REVIEWER
)
from taskpilot.core.trace_names import (  # type: ignore
    WORKFLOW_RUN as TRACE_WORKFLOW_RUN,
    agent_run as trace_agent_run
)
from taskpilot.core.llm_cost_tracker import track_llm_metrics  # type: ignore
from taskpilot.core.exceptions import (  # type: ignore
    PolicyViolationError,
    GuardrailsBlockedError,
    AgentExecutionError,
    ToolValidationError
)

logger = logging.getLogger(__name__)

# Global guardrails instance (lazy initialization)
_guardrails: Optional[NeMoGuardrailsWrapper] = None


def _get_guardrails() -> NeMoGuardrailsWrapper:
    """Get or create global guardrails instance."""
    global _guardrails
    if _guardrails is None:
        # Try to load config from taskpilot directory
        taskpilot_dir = Path(__file__).parent.parent.parent.parent
        config_path = taskpilot_dir / "guardrails" / "config.yml"
        _guardrails = NeMoGuardrailsWrapper(config_path=config_path if config_path.exists() else None)
    return _guardrails

def _extract_text_from_content(content) -> str:
    """Extract text from various content types."""
    if isinstance(content, str):
        return content
    if isinstance(content, TextContent):
        return content.text
    if hasattr(content, 'text'):
        return str(content.text)
    return str(content)

def _extract_text_from_messages(messages) -> str:
    """Extract text from message list, prioritizing user messages."""
    if not messages:
        return ""
    
    # Look for user messages first
    for msg in reversed(messages):
        if hasattr(msg, 'role') and msg.role == 'user':
            if hasattr(msg, 'content'):
                return _extract_text_from_content(msg.content)
            if hasattr(msg, 'text'):
                return msg.text
    
    # Fallback: get text from last message
    if messages:
        last_msg = messages[-1]
        if hasattr(last_msg, 'content'):
            return _extract_text_from_content(last_msg.content)
        if hasattr(last_msg, 'text'):
            return last_msg.text
    
    return ""

def _extract_text_from_result(result) -> str:
    """Extract text from agent run result."""
    if not result:
        return ""
    
    # Skip async generators and similar objects
    if hasattr(result, '__class__'):
        class_name = result.__class__.__name__
        if 'async_generator' in class_name.lower() or 'generator' in class_name.lower():
            logger.debug(f"Skipping {class_name} object in result extraction")
            return ""
    
    # Check for event objects with data attribute (AgentRunEvent, etc.)
    if hasattr(result, 'data'):
        data = result.data
        if isinstance(data, str):
            return data
        # If data is not a string, try to extract from it
        if data:
            return _extract_text_from_result(data)
    
    # Direct text attribute
    if hasattr(result, 'text'):
        text = result.text
        if text and isinstance(text, str):
            return text
    
    # AgentRunResponse with text
    if hasattr(result, 'agent_run_response'):
        agent_response = result.agent_run_response
        if hasattr(agent_response, 'text'):
            text = agent_response.text
            if text and isinstance(text, str):
                return text
        if hasattr(agent_response, 'messages') and agent_response.messages:
            last_msg = agent_response.messages[-1]
            if hasattr(last_msg, 'content'):
                return _extract_text_from_content(last_msg.content)
            if hasattr(last_msg, 'text'):
                return last_msg.text
    
    # Messages in result
    if hasattr(result, 'messages') and result.messages:
        last_msg = result.messages[-1]
        if hasattr(last_msg, 'content'):
            return _extract_text_from_content(last_msg.content)
        if hasattr(last_msg, 'text'):
            return last_msg.text
    
    # String representation (last resort, but only if it looks like text)
    result_str = str(result)
    if result_str and len(result_str) < 1000 and not result_str.startswith('<'):
        return result_str
    
    return ""

def _parse_task_from_planner(response: Any) -> tuple[str, str, str]:
    """Parse task information from planner output using structured parsing.
    
    Handles both function calling responses (preferred) and text responses.
    
    Args:
        response: Planner agent response (can be function call or text)
        
    Returns:
        Tuple of (title, priority, description)
    """
    from taskpilot.core.structured_output import parse_task_info_from_response  # type: ignore
    
    try:
        # Use structured output parser (handles function calls and text)
        task_info = parse_task_info_from_response(response)
        return task_info.title, task_info.priority, task_info.description
    except Exception as e:
        logger.warning(f"Structured parsing failed: {e}, using legacy parser")
        # Fallback: try to extract text and use legacy parser
        text = _extract_text_from_result(response) if hasattr(response, '__iter__') else str(response)
        return _parse_task_from_planner_legacy(text)


def _parse_task_from_planner_legacy(output: str) -> tuple[str, str, str]:
    """Legacy regex-based parsing (fallback only).
    
    Kept for backward compatibility but should not be used in new code.
    """
    title = ""
    priority = "medium"
    description = ""
    
    # Try to extract structured format
    title_match = re.search(r'\*\*Task Title:\*\*\s*(.+?)(?:\n|$)', output, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
    
    priority_match = re.search(r'\*\*Priority:\*\*\s*(.+?)(?:\n|$)', output, re.IGNORECASE)
    if priority_match:
        priority = priority_match.group(1).strip().lower()
    
    desc_match = re.search(r'\*\*Description:\*\*\s*(.+?)(?:\n\n|\Z)', output, re.IGNORECASE | re.DOTALL)
    if desc_match:
        description = desc_match.group(1).strip()
    
    # Fallback: use first line as title
    if not title:
        lines = output.split('\n')
        title = lines[0].strip() if lines else output[:50]
        description = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ""
    
    return title, priority, description

def _detect_agent_type(agent_name: str) -> Optional[AgentType]:
    """Detect agent type from agent name.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        AgentType if detected, None otherwise
    """
    name_lower = agent_name.lower()
    if "planner" in name_lower:
        return AgentType.PLANNER
    elif "reviewer" in name_lower:
        return AgentType.REVIEWER
    elif "executor" in name_lower:
        return AgentType.EXECUTOR
    return None


def create_audit_and_policy_middleware(
    agent_name: str,
    task_store: Optional[TaskStore] = None
):
    """Create middleware with agent name captured.
    
    Args:
        agent_name: Name of the agent (e.g., "PlannerAgent")
        task_store: Optional TaskStore instance. If None, uses global instance.
    
    Returns:
        Middleware function
    """
    agent_type = _detect_agent_type(agent_name)
    store = task_store or get_task_store()
    
    async def audit_and_policy(
        context: AgentRunContext,
        next: Callable[[AgentRunContext], Awaitable[None]]
    ) -> None:
        """Audit and enforce policy on agent runs.
        
        - Logs input and output for audit trail
        - Validates input/output with NeMo Guardrails
        - Enforces policy (e.g., blocks 'delete' keyword)
        - Tracks tasks in task store
        - Records metrics and traces
        """
        # Get or create request ID
        request_id = get_request_id() or str(uuid.uuid4())
        
        # Try to get parent span ID from active spans (workflow span)
        parent_span_id = None
        try:
            tracer = get_tracer()
            # Look for workflow.run span as parent
            active_spans = getattr(tracer, '_active_spans', {})
            for active_span in active_spans.values():
                if active_span.name == TRACE_WORKFLOW_RUN and active_span.request_id == request_id:
                    parent_span_id = active_span.span_id
                    break
        except Exception:
            # If we can't get parent, continue without it
            pass
        
        # Start tracing span with parent if found (use standardized trace name)
        with TraceContext(
            name=trace_agent_run(agent_name),
            request_id=request_id,
            parent_span_id=parent_span_id,
            tags={"agent_name": agent_name, "agent_type": agent_type.value if agent_type else "unknown"}
        ) as span:
            start_time = time.time()
            
            # Initialize decision logger (start background task if needed)
            decision_logger = get_decision_logger()
            try:
                await decision_logger.start()
            except RuntimeError:
                # Already started or event loop issue, continue
                pass
            
            # Record metrics (use standardized metric names)
            metrics = get_metrics_collector()
            metrics.increment_counter(agent_invocations(agent_name))
            
            try:
                # Extract input from messages
                input_text = _extract_text_from_messages(context.messages)
                
                # Add operation context to span for better trace visibility
                if input_text:
                    span.tags["input_length"] = str(len(input_text))
                    span.tags["input_preview"] = input_text[:100] + "..." if len(input_text) > 100 else input_text
                
                logger.info(f"[AUDIT] {agent_name} Input: {input_text} (request_id={request_id})")
                
                # NeMo Guardrails input validation
                guardrails = _get_guardrails()
                allowed, reason = await guardrails.validate_input(input_text)
                if not allowed:
                    metrics.increment_counter(agent_guardrails_blocked(agent_name))
                    error = GuardrailsBlockedError(
                        check_type="input",
                        reason=reason,
                        details={"agent_name": agent_name, "request_id": request_id}
                    )
                    logger.error(f"[GUARDRAILS] [{error.error_code}] Input blocked: {reason} (request_id={request_id})")
                    raise error
                
                # Legacy policy enforcement (keep for backward compatibility)
                if input_text and "delete" in input_text.lower():
                    metrics.increment_counter(agent_policy_violations(agent_name))
                    metrics.increment_counter(POLICY_VIOLATIONS_TOTAL)  # Aggregate for Golden Signals
                    error = PolicyViolationError(
                        policy_type="keyword_filter",
                        reason="'delete' keyword not allowed",
                        details={"agent_name": agent_name, "request_id": request_id, "input_preview": input_text[:100]}
                    )
                    logger.error(f"[POLICY] [{error.error_code}] Policy violation: 'delete' keyword detected (request_id={request_id})")
                    raise error
                
                # Execute the agent
                await next(context)
                
                # Extract output from result (for logging)
                # Note: context.result might be an async generator in streaming mode
                # We need to extract from the messages that were added during execution
                output_text = ""
        
                # Check if context.result is an async generator - if so, we can't extract from it directly
                # In this case, we must rely on context.messages or other sources
                is_async_gen = False
                if hasattr(context.result, '__class__'):
                    class_name = context.result.__class__.__name__
                    if 'async_generator' in class_name.lower() or 'generator' in class_name.lower():
                        is_async_gen = True
                        logger.debug(f"[DEBUG] context.result is {class_name}, skipping direct extraction")
                
                # Primary: Check context.result.agent_run_response.text (if not async generator)
                if not is_async_gen and hasattr(context.result, 'agent_run_response'):
                    agent_response = context.result.agent_run_response
                    if hasattr(agent_response, 'text') and agent_response.text:
                        output_text = agent_response.text
                    elif hasattr(agent_response, 'messages') and agent_response.messages:
                        # Get the last message from agent_run_response (this is the agent's actual output)
                        last_msg = agent_response.messages[-1]
                        if hasattr(last_msg, 'content'):
                            content = last_msg.content
                            if isinstance(content, str):
                                output_text = content
                            elif hasattr(content, 'text'):
                                output_text = content.text
                            else:
                                output_text = _extract_text_from_content(content)
                
                # Check if result has a 'data' attribute (like AgentRunEvent) - works even with async gen
                if not output_text and hasattr(context.result, 'data'):
                    data = context.result.data
                    if isinstance(data, str):
                        output_text = data
                    elif data:
                        # Try to extract from data object
                        output_text = _extract_text_from_result(data)
                
                # IMPORTANT: For async generators, context.messages is the most reliable source
                # The agent's response is added to context.messages during execution
                if not output_text and hasattr(context, 'messages') and context.messages:
                    # Get the LAST assistant message (should be this agent's response)
                    # Also check ALL messages, not just reversed, to catch any assistant response
                    assistant_messages = []
                    for msg in context.messages:
                        msg_role = getattr(msg, 'role', None)
                        role_str = str(msg_role).lower() if msg_role else ''
                        if role_str == 'assistant' or (hasattr(msg_role, 'value') and msg_role.value == 'assistant'):
                            assistant_messages.append(msg)
                    
                    # Use the last assistant message (most recent response)
                    if assistant_messages:
                        last_assistant = assistant_messages[-1]
                        if hasattr(last_assistant, 'content'):
                            content_text = _extract_text_from_content(last_assistant.content)
                            if content_text:
                                output_text = content_text
                        elif hasattr(last_assistant, 'text'):
                            output_text = last_assistant.text
                
                # Fallback: Check if result itself is a string
                if not output_text and isinstance(context.result, str):
                    output_text = context.result
                
                # Fallback: Check if context.result itself has text
                if not output_text and not is_async_gen and hasattr(context.result, 'text'):
                    output_text = context.result.text or ""
                
                # Final fallback: Use the helper function (skips async generators)
                if not output_text and not is_async_gen:
                    output_text = _extract_text_from_result(context.result)
                
                # For reviewer, try one more aggressive extraction if still empty
                if agent_type == AgentType.REVIEWER and not output_text:
                    # Last resort: Try to get from string representation if it contains REVIEW
                    result_str = str(context.result)
                    if 'REVIEW' in result_str.upper():
                        # Extract REVIEW from the string
                        import re
                        match = re.search(r'REVIEW', result_str, re.IGNORECASE)
                        if match:
                            output_text = 'REVIEW'
                            logger.info(f"[TASK] Extracted REVIEW from result string representation")
                
                # Log output for reviewer to help debug
                if agent_type == AgentType.REVIEWER:
                    if output_text:
                        logger.info(f"[AUDIT] {agent_name} Output: '{output_text}' (request_id={request_id})")
                    else:
                        logger.warning(f"[AUDIT] {agent_name} Output: EMPTY - cannot update task status (request_id={request_id})")
                else:
                    logger.info(f"[AUDIT] {agent_name} Output: {output_text} (request_id={request_id})")
                
                # NeMo Guardrails output validation
                allowed, reason = await guardrails.validate_output(output_text)
                if not allowed:
                    metrics.increment_counter(agent_guardrails_output_blocked(agent_name))
                    logger.error(f"[GUARDRAILS] Output blocked: {reason} (request_id={request_id})")
                    raise ValueError(f"Output validation failed: {reason}")
                
                # Validate tool calls with OPA (if any were made)
                # Check for tool calls in the result
                tool_calls_made = False
                if hasattr(context.result, 'agent_run_response'):
                    agent_response = context.result.agent_run_response
                    if hasattr(agent_response, 'messages'):
                        for msg in agent_response.messages:
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                tool_calls_made = True
                                # Validate each tool call with OPA
                                opa_validator = OPAToolValidator(use_embedded=True)
                                for tool_call in msg.tool_calls:
                                    tool_name = getattr(tool_call, 'function', {}).get('name', '') if hasattr(tool_call, 'function') else ''
                                    tool_params = getattr(tool_call, 'function', {}).get('arguments', {}) if hasattr(tool_call, 'function') else {}
                                    if tool_name:
                                        try:
                                            # Parse JSON arguments if string
                                            if isinstance(tool_params, str):
                                                import json
                                                tool_params = json.loads(tool_params)
                                            # Validate with OPA (this will log the decision)
                                            allowed, reason, requires_approval = await opa_validator.validate_tool_call(
                                                tool_name=tool_name,
                                                parameters=tool_params,
                                                agent_type=agent_name,
                                                agent_id=agent_name
                                            )
                                            if not allowed:
                                                error = ToolValidationError(
                                                    tool_name=tool_name,
                                                    reason=reason,
                                                    details={"agent_name": agent_name, "request_id": request_id}
                                                )
                                                logger.warning(f"[OPA] [{error.error_code}] Tool call denied: {tool_name} - {reason}")
                                        except Exception as e:
                                            logger.debug(f"Error validating tool call {tool_name}: {e}")
                
                # Track LLM token usage and cost (if available in response)
                try:
                    if hasattr(context.result, 'agent_run_response'):
                        track_llm_metrics(context.result, agent_name, metrics)
                    elif hasattr(context.result, 'usage'):
                        track_llm_metrics(context.result, agent_name, metrics)
                except Exception as e:
                    logger.debug(f"Failed to track LLM metrics: {e}")
                
                # Record latency metric (use standardized metric name)
                latency_ms = (time.time() - start_time) * 1000
                metrics.record_histogram(agent_latency_ms(agent_name), latency_ms)
                
                # Add rich context to span for better trace visibility
                span.tags["latency_ms"] = str(latency_ms)
                span.tags["output_length"] = str(len(output_text)) if output_text else "0"
                if output_text:
                    span.tags["output_preview"] = output_text[:200] + "..." if len(output_text) > 200 else output_text
                
                # Add tool call information
                if tool_calls_made:
                    span.tags["tool_calls"] = "yes"
                
                # Add task information for planner/reviewer
                if agent_type == AgentType.PLANNER:
                    try:
                        title, priority, description = _parse_task_from_planner(context.result)
                        if title:
                            span.tags["task_created"] = "yes"
                            span.tags["task_title"] = title[:100]  # Truncate for Jaeger
                            span.tags["task_priority"] = priority or "medium"
                    except:
                        pass
                elif agent_type == AgentType.REVIEWER:
                    pending_tasks = store.list_tasks(status=TaskStatus.PENDING, limit=1)
                    if pending_tasks:
                        task = pending_tasks[0]
                        span.tags["task_id"] = task.id
                        span.tags["task_title"] = task.title[:100] if task.title else ""
                        if output_text:
                            output_upper = output_text.upper()
                            if "APPROVE" in output_upper:
                                span.tags["task_action"] = "approved"
                            elif "REVIEW" in output_upper:
                                span.tags["task_action"] = "requires_review"
                            else:
                                span.tags["task_action"] = "rejected"
                
                span.logs.append({
                    "timestamp": time.time(),
                    "fields": {
                        "latency_ms": latency_ms,
                        "input": input_text[:500] if input_text else "",
                        "output": output_text[:500] if output_text else ""
                    }
                })
                
                # Track tasks based on agent type
                if agent_type == AgentType.PLANNER:
                    # Parse from context.result (supports function calls and text)
                    try:
                        title, priority, description = _parse_task_from_planner(context.result)
                        if title:
                            try:
                                # Validate create_task tool call with OPA if not already validated
                                if not tool_calls_made:
                                    opa_validator = OPAToolValidator(use_embedded=True)
                                    # Use actual parsed values, not raw context
                                    task_params = {
                                        "title": str(title) if title else "",
                                        "priority": str(priority) if priority else "medium",
                                        "description": str(description) if description else ""
                                    }
                                    await opa_validator.validate_tool_call(
                                        tool_name="create_task",
                                        parameters=task_params,
                                        agent_type=agent_name,
                                        agent_id=agent_name
                                    )
                                
                                task = store.create_task(
                                    title=title,
                                    priority=priority,
                                    description=description
                                )
                                metrics.increment_counter("tasks.created")
                                logger.info(f"[TASK] Created task: {task.id} - {title} (status: {task.status.value}, request_id={request_id})")
                            except Exception as e:
                                record_error(e, agent_name=agent_name, operation="create_task")
                                logger.error(f"Failed to create task: {e}", exc_info=True)
                    except Exception as e:
                        record_error(e, agent_name=agent_name, operation="parse_task")
                        logger.error(f"Failed to parse task from planner: {e}", exc_info=True)
                
                elif agent_type == AgentType.REVIEWER:
                    # Get the most recent PENDING task (should be the one just created by planner)
                    pending_tasks = store.list_tasks(status=TaskStatus.PENDING, limit=1)
                    if pending_tasks:
                        task = pending_tasks[0]
                        # Ensure we have output text
                        if not output_text:
                            metrics.increment_counter(TASKS_REVIEWER_OUTPUT_EMPTY)
                            logger.warning(f"[TASK] Reviewer output is empty, cannot update task {task.id} (request_id={request_id})")
                        else:
                            output_upper = output_text.upper()
                            logger.info(f"[TASK] Reviewer output extracted: '{output_text}' (length: {len(output_text)}, request_id={request_id})")
                            try:
                                if "APPROVE" in output_upper:
                                    store.update_task_status(
                                        task.id,
                                        TaskStatus.APPROVED,
                                        reviewer_response=output_text
                                    )
                                    metrics.increment_counter("tasks.approved")
                                    logger.info(f"[TASK] Task {task.id} approved (request_id={request_id})")
                                elif "REVIEW" in output_upper:
                                    store.update_task_status(
                                        task.id,
                                        TaskStatus.REVIEW,
                                        reviewer_response=output_text
                                    )
                                    metrics.increment_counter(TASKS_REVIEW)
                                    logger.info(f"[TASK] Task {task.id} requires human review (request_id={request_id})")
                                else:
                                    # Default to REJECTED if not APPROVE or REVIEW
                                    store.update_task_status(
                                        task.id,
                                        TaskStatus.REJECTED,
                                        reviewer_response=output_text
                                    )
                                    metrics.increment_counter(TASKS_REJECTED)
                                    logger.info(f"[TASK] Task {task.id} rejected (output: '{output_text[:50]}', request_id={request_id})")
                            except Exception as e:
                                record_error(e, agent_name=agent_name, operation="update_task_status", task_id=task.id)
                                logger.error(f"Failed to update task status: {e}", exc_info=True)
                    else:
                        metrics.increment_counter(TASKS_NO_PENDING_FOR_REVIEWER)
                        logger.warning(f"[TASK] No pending tasks found for reviewer to update (request_id={request_id})")
                
                elif agent_type == AgentType.EXECUTOR:
                    approved_tasks = store.list_tasks(status=TaskStatus.APPROVED, limit=1)
                    if approved_tasks:
                        task = approved_tasks[0]
                        try:
                            store.update_task_status(task.id, TaskStatus.EXECUTED)
                            metrics.increment_counter(TASKS_EXECUTED)
                            logger.info(f"[TASK] Task {task.id} executed (request_id={request_id})")
                        except Exception as e:
                            record_error(e, agent_name=agent_name, operation="execute_task", task_id=task.id)
                            logger.error(f"Failed to mark task as executed: {e}", exc_info=True)
                
                # Record success metric
                metrics.increment_counter(agent_success(agent_name))
                
            except Exception as e:
                # Record error with error code if available
                metrics.increment_counter(agent_errors(agent_name))
                
                # Extract error code if it's a BaseAgentException
                error_code = None
                if hasattr(e, 'error_code'):
                    error_code = e.error_code
                    logger.error(f"[{error_code}] Agent {agent_name} error: {e.message} (request_id={request_id})", exc_info=True)
                else:
                    logger.error(f"Agent {agent_name} error: {e} (request_id={request_id})", exc_info=True)
                
                record_error(e, agent_name=agent_name, request_id=request_id)
                raise  # Re-raise to maintain error propagation
    
    return audit_and_policy
