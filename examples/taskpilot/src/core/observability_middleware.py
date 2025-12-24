"""Observability middleware - library integration layer.

This module handles all observability concerns (metrics, traces, logs, policy, guardrails)
by integrating with the agent-observable-core library. It does NOT contain any
project-specific business logic.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Callable, Awaitable, Optional, Any

from agent_framework import AgentRunContext, agent_middleware  # type: ignore
from agent_observable_core import (  # type: ignore
    get_metric_standardizer,
    get_trace_standardizer,
)
from agent_observable_core.exceptions import (  # type: ignore
    PolicyViolationError,
    GuardrailsBlockedError,
    ToolValidationError,
)
from agent_observable_core.llm_cost_tracker import track_llm_metrics  # type: ignore
from agent_observable_policy import OPAToolValidator  # type: ignore

from taskpilot.core.observable import (  # type: ignore
    get_request_id,
    get_metrics,
    get_tracer,
    TraceContext,
    get_guardrails,
    get_decision_logger,
    get_opa,
    record_error,
)
from taskpilot.core.text_extraction import (  # type: ignore
    extract_text_from_messages,
    extract_text_from_context,
    is_async_generator,
)
from taskpilot.core.task_hooks import detect_agent_type  # type: ignore
from taskpilot.core.types import AgentType  # type: ignore

logger = logging.getLogger(__name__)

# Get standardizers for generic metrics and traces
metric_standardizer = get_metric_standardizer(service_name="taskpilot")
trace_standardizer = get_trace_standardizer(service_name="taskpilot")
TRACE_WORKFLOW_RUN = trace_standardizer.workflow_run()


def trace_agent_run(agent_name: str) -> str:
    """Get standardized trace name for agent run."""
    return trace_standardizer.agent_run(agent_name)


def create_observability_middleware(
    agent_name: str,
    hooks: Optional[Any] = None,
) -> Callable[[AgentRunContext, Callable], Awaitable[None]]:
    """Create observability middleware (library integration only).
    
    This middleware handles:
    - Metrics collection (workflow, agent, tool, LLM)
    - Distributed tracing (OpenTelemetry)
    - Policy enforcement (OPA, keyword filters)
    - Guardrails (NeMo input/output validation)
    - Cost tracking (LLM tokens and costs)
    - Error tracking
    
    Args:
        agent_name: Name of the agent (e.g., "PlannerAgent")
        hooks: Optional hooks object for project-specific extensions
        
    Returns:
        Middleware function
    """
    
    async def observability_middleware(
        context: AgentRunContext,
        next: Callable[[AgentRunContext], Awaitable[None]]
    ) -> None:
        """Observability middleware - handles all library integration."""
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
        
        # Get agent type from hooks if available, otherwise use utility function
        agent_type = None
        if hooks:
            if hasattr(hooks, 'detect_agent_type'):
                agent_type = hooks.detect_agent_type(agent_name)
            elif hasattr(hooks, '_detect_agent_type'):
                agent_type = hooks._detect_agent_type(agent_name)
        else:
            agent_type = detect_agent_type(agent_name)
        
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
            if decision_logger:
                try:
                    await decision_logger.start()
                except RuntimeError:
                    # Already started or event loop issue, continue
                    pass
            
            # Record metrics (use standardized metric names)
            metrics = get_metrics()
            metrics.increment_counter(metric_standardizer.agent_invocations(agent_name))
            
            try:
                # Extract input from messages
                if hooks and hasattr(hooks, 'extract_input_text'):
                    input_text = hooks.extract_input_text(context)
                else:
                    input_text = extract_text_from_messages(context.messages)
                
                # Add operation context to span for better trace visibility
                if input_text:
                    span.tags["input_length"] = str(len(input_text))
                    span.tags["input_preview"] = input_text[:100] + "..." if len(input_text) > 100 else input_text
                
                # Call hooks.on_agent_start if available
                if hooks and hasattr(hooks, 'on_agent_start'):
                    additional_tags = hooks.on_agent_start(agent_name, input_text, context, request_id)
                    if additional_tags:
                        span.tags.update(additional_tags)
                
                logger.info(f"[AUDIT] {agent_name} Input: {input_text} (request_id={request_id})")
                
                # NeMo Guardrails input validation
                guardrails = get_guardrails()
                if guardrails:
                    allowed, reason = await guardrails.validate_input(input_text)
                else:
                    allowed, reason = True, "Guardrails not enabled"
                if not allowed:
                    metrics.increment_counter(metric_standardizer.agent_guardrails_blocked(agent_name))
                    error = GuardrailsBlockedError(
                        check_type="input",
                        reason=reason,
                        details={"agent_name": agent_name, "request_id": request_id}
                    )
                    logger.error(f"[GUARDRAILS] [{error.error_code}] Input blocked: {reason} (request_id={request_id})")
                    raise error
                
                # Simple keyword-based policy enforcement
                if input_text and "delete" in input_text.lower():
                    metrics.increment_counter(metric_standardizer.agent_policy_violations(agent_name))
                    metrics.increment_counter(metric_standardizer.policy_violations_total())  # Aggregate for Golden Signals
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
                is_async_gen = is_async_generator(context.result)
                
                # Extract output text
                if hooks and hasattr(hooks, 'extract_output_text'):
                    output_text = hooks.extract_output_text(context, context.result)
                else:
                    output_text = extract_text_from_context(context, is_async_gen)
                
                # Ensure we have a string
                if not isinstance(output_text, str):
                    output_text = str(output_text) if output_text else ""
                
                # For reviewer, try one more aggressive extraction if still empty
                if agent_type and agent_type == AgentType.REVIEWER and not output_text:
                    # Last resort: Try to get from string representation if it contains REVIEW
                    result_str = str(context.result)
                    if 'REVIEW' in result_str.upper():
                        import re
                        match = re.search(r'REVIEW', result_str, re.IGNORECASE)
                        if match:
                            output_text = 'REVIEW'
                            logger.info(f"[TASK] Extracted REVIEW from result string representation")
                
                # Log output
                logger.info(f"[AUDIT] {agent_name} Output: {output_text} (request_id={request_id})")
                
                # NeMo Guardrails output validation
                if guardrails:
                    allowed, reason = await guardrails.validate_output(output_text)
                else:
                    allowed, reason = True, "Guardrails not enabled"
                if not allowed:
                    metrics.increment_counter(metric_standardizer.agent_guardrails_output_blocked(agent_name))
                    logger.error(f"[GUARDRAILS] Output blocked: {reason} (request_id={request_id})")
                    raise ValueError(f"Output validation failed: {reason}")
                
                # Validate tool calls with OPA (if any were made)
                tool_calls_made = False
                if hasattr(context.result, 'agent_run_response'):
                    agent_response = context.result.agent_run_response
                    if hasattr(agent_response, 'messages'):
                        for msg in agent_response.messages:
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                tool_calls_made = True
                                # Validate each tool call with OPA
                                opa = get_opa()
                                decision_logger = get_decision_logger()
                                metrics = get_metrics()
                                opa_validator = OPAToolValidator(
                                    use_embedded=True,
                                    embedded_opa=opa,
                                    decision_logger=decision_logger,
                                    package="taskpilot.tool_calls",
                                    metrics_collector=metrics,
                                    service_name="taskpilot",
                                )
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
                        track_llm_metrics(context.result, agent_name, metrics, service_name="taskpilot")
                    elif hasattr(context.result, 'usage'):
                        track_llm_metrics(context.result, agent_name, metrics, service_name="taskpilot")
                except Exception as e:
                    logger.debug(f"Failed to track LLM metrics: {e}")
                
                # Record latency metric (use standardized metric name)
                latency_ms = (time.time() - start_time) * 1000
                metrics.record_histogram(metric_standardizer.agent_latency_ms(agent_name), latency_ms)
                
                # Add rich context to span for better trace visibility
                span.tags["latency_ms"] = str(latency_ms)
                span.tags["output_length"] = str(len(output_text)) if output_text else "0"
                if output_text:
                    span.tags["output_preview"] = output_text[:200] + "..." if len(output_text) > 200 else output_text
                
                # Add tool call information
                if tool_calls_made:
                    span.tags["tool_calls"] = "yes"
                
                span.logs.append({
                    "timestamp": time.time(),
                    "fields": {
                        "latency_ms": latency_ms,
                        "input": input_text[:500] if input_text else "",
                        "output": output_text[:500] if output_text else ""
                    }
                })
                
                # Call hooks.on_agent_complete if available
                if hooks and hasattr(hooks, 'on_agent_complete'):
                    hooks.on_agent_complete(agent_name, output_text, context, request_id, latency_ms)
                
                # Record success metric
                metrics.increment_counter(metric_standardizer.agent_success(agent_name))
                
            except Exception as e:
                # Record error with error code if available
                metrics.increment_counter(metric_standardizer.agent_errors(agent_name))
                
                # Extract error code if it's a BaseAgentException
                error_code = None
                if hasattr(e, 'error_code'):
                    error_code = e.error_code
                    logger.error(f"[{error_code}] Agent {agent_name} error: {e.message} (request_id={request_id})", exc_info=True)
                else:
                    logger.error(f"Agent {agent_name} error: {e} (request_id={request_id})", exc_info=True)
                
                # Call hooks.on_agent_error if available
                if hooks and hasattr(hooks, 'on_agent_error'):
                    hooks.on_agent_error(agent_name, e, context, request_id)
                
                record_error(e, agent_name=agent_name, request_id=request_id)
                raise  # Re-raise to maintain error propagation
    
    # Apply decorator to the returned function for MS Agent Framework recognition
    return agent_middleware(observability_middleware)
