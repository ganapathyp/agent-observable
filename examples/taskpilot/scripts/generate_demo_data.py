#!/usr/bin/env python3
"""
Generate comprehensive demo data for observability tools.

This script generates:
- Logs (JSON) to logs/taskpilot.log
- Traces (via OTLP) to Jaeger
- Policy Decisions (JSONL) to decision_logs.jsonl
- Metrics (via MetricsCollector API)

Scenarios covered:
1. Cost Optimization (model comparison)
2. Performance Bottleneck (slow agents)
3. Policy Violations (denied decisions)
4. Error Patterns (various error types)
"""

import asyncio
import json
import os
import random
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Try to import OpenTelemetry for traces
try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    print("⚠️  OpenTelemetry not available. Traces will not be generated.")
    print("   Install: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc")

# Try to import MetricsCollector
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from agent_observable_core.observability import MetricsCollector
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    print("⚠️  MetricsCollector not available. Metrics will not be generated.")


# Configuration
BASE_DIR = Path(__file__).parent.parent
LOGS_FILE = BASE_DIR / "logs" / "taskpilot.log"
DECISIONS_FILE = BASE_DIR / "decision_logs.jsonl"
OTLP_ENDPOINT = "http://localhost:4317"

# Ensure logs directory exists
LOGS_FILE.parent.mkdir(parents=True, exist_ok=True)


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"req-{uuid.uuid4().hex[:8]}"


def generate_timestamp(offset_seconds: int = 0) -> str:
    """Generate ISO 8601 timestamp."""
    dt = datetime.utcnow() + timedelta(seconds=offset_seconds)
    return dt.isoformat() + "Z"


def write_log_entry(entry: Dict[str, Any]) -> None:
    """Write a log entry to taskpilot.log."""
    with open(LOGS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def write_decision_entry(entry: Dict[str, Any]) -> None:
    """Write a policy decision entry to decision_logs.jsonl."""
    with open(DECISIONS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def generate_workflow_logs(scenario: str, count: int = 10) -> List[str]:
    """Generate workflow execution logs."""
    request_ids = []
    
    for i in range(count):
        request_id = generate_request_id()
        request_ids.append(request_id)
        
        # Workflow start
        write_log_entry({
            "timestamp": generate_timestamp(offset_seconds=-i*10),
            "level": "INFO",
            "name": "taskpilot.core.middleware",
            "message": f"[WORKFLOW] Started workflow execution",
            "request_id": request_id,
            "workflow_type": "task_creation",
            "scenario": scenario
        })
        
        # Agent execution logs
        agents = ["PlannerAgent", "ExecutorAgent", "ReviewerAgent"]
        for agent in agents:
            latency = random.uniform(100, 2000) if agent != "ExecutorAgent" else random.uniform(3000, 8000)  # Slow ExecutorAgent
            write_log_entry({
                "timestamp": generate_timestamp(offset_seconds=-i*10 + 1),
                "level": "INFO",
                "name": "taskpilot.core.middleware",
                "message": f"[AUDIT] {agent} executed",
                "request_id": request_id,
                "agent_name": agent,
                "latency_ms": latency,
                "scenario": scenario
            })
        
        # Workflow completion
        write_log_entry({
            "timestamp": generate_timestamp(offset_seconds=-i*10 + 2),
            "level": "INFO",
            "name": "taskpilot.core.middleware",
            "message": "[WORKFLOW] Completed successfully",
            "request_id": request_id,
            "workflow_success": True,
            "scenario": scenario
        })
    
    return request_ids


def generate_error_logs(scenario: str, count: int = 5) -> List[str]:
    """Generate error logs."""
    request_ids = []
    
    error_types = [
        ("TOOL_TIMEOUT", "ToolTimeoutError", "Tool execution exceeded 30s timeout"),
        ("TOOL_EXECUTION_ERROR", "ToolExecutionError", "Tool execution failed"),
        ("POLICY_VIOLATION", "PolicyViolationError", "Policy check failed"),
    ]
    
    for i in range(count):
        request_id = generate_request_id()
        request_ids.append(request_id)
        error_code, error_type, error_message = random.choice(error_types)
        
        write_log_entry({
            "timestamp": generate_timestamp(offset_seconds=-i*5),
            "level": "ERROR",
            "name": "taskpilot.core.middleware",
            "message": f"[ERROR] {error_message}",
            "request_id": request_id,
            "agent_name": "ExecutorAgent",
            "tool_name": "update_task",
            "error_code": error_code,
            "error_type": error_type,
            "error_message": error_message,
            "scenario": scenario
        })
    
    return request_ids


def generate_policy_decisions(scenario: str, count: int = 15) -> None:
    """Generate policy decision logs."""
    decision_types = ["tool_call", "opa", "guardrails"]
    results = ["allow", "deny", "require_approval"]
    
    for i in range(count):
        decision_type = random.choice(decision_types)
        result = random.choice(results) if decision_type != "opa" else random.choice(["allow", "deny"])
        
        decision = {
            "decision_id": str(uuid.uuid4()),
            "timestamp": generate_timestamp(offset_seconds=-i*3),
            "decision_type": decision_type,
            "result": result,
            "tool_name": random.choice(["create_task", "update_task", "delete_task"]),
            "agent_id": random.choice(["PlannerAgent", "ExecutorAgent", "ReviewerAgent"]),
            "reason": f"Policy check {'passed' if result == 'allow' else 'failed'}",
            "context": {
                "parameters": {"title": "Test task"},
                "user_role": random.choice(["admin", "viewer", "editor"])
            },
            "scenario": scenario
        }
        
        if decision_type == "opa":
            decision["policy_name"] = "tool_access_policy"
        
        write_decision_entry(decision)
        
        # Also write to logs for Filebeat
        write_log_entry({
            "timestamp": decision["timestamp"],
            "level": "INFO",
            "name": "agent_observable_policy.decision_logger",
            "message": f"[POLICY] {decision_type} decision: {result}",
            "log_type": "policy_decision",
            "decision_id": decision["decision_id"],
            "decision_type": decision_type,
            "result": result,
            "tool_name": decision["tool_name"],
            "agent_id": decision["agent_id"],
            "scenario": scenario
        })


def generate_traces(scenario: str, request_ids: List[str], slow_agent: bool = False) -> None:
    """Generate traces via OpenTelemetry."""
    if not OTEL_AVAILABLE:
        print(f"⚠️  Skipping traces for scenario '{scenario}' (OpenTelemetry not available)")
        return
    
    try:
        # Setup tracer
        resource = Resource.create({"service.name": "taskpilot", "service.version": "1.0.0"})
        provider = TracerProvider(resource=resource)
        
        exporter = OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        
        tracer = trace.get_tracer(__name__)
        
        for i, request_id in enumerate(request_ids):
            # Workflow span
            with tracer.start_as_current_span("taskpilot.workflow.run") as workflow_span:
                workflow_span.set_attribute("request.id", request_id)
                workflow_span.set_attribute("workflow.type", "task_creation")
                workflow_span.set_attribute("scenario", scenario)
                
                # Agent spans
                agents = ["PlannerAgent", "ExecutorAgent", "ReviewerAgent"]
                for agent in agents:
                    with tracer.start_as_current_span(f"taskpilot.agent.{agent}.run") as agent_span:
                        agent_span.set_attribute("request.id", request_id)
                        agent_span.set_attribute("agent_name", agent)
                        agent_span.set_attribute("scenario", scenario)
                        
                        # Make ExecutorAgent slow if requested
                        if slow_agent and agent == "ExecutorAgent":
                            agent_span.set_attribute("latency_ms", "5000.0")
                            agent_span.set_attribute("slow", "true")
                        else:
                            agent_span.set_attribute("latency_ms", str(random.uniform(100, 500)))
                        
                        # Tool span
                        with tracer.start_as_current_span(f"taskpilot.tool.create_task.call") as tool_span:
                            tool_span.set_attribute("request.id", request_id)
                            tool_span.set_attribute("tool_name", "create_task")
                            tool_span.set_attribute("scenario", scenario)
                            tool_span.set_attribute("latency_ms", str(random.uniform(50, 200)))
                
                workflow_span.set_attribute("workflow.success", "true")
                workflow_span.set_attribute("workflow.latency.ms", str(random.uniform(1000, 2000)))
        
        # Force flush
        provider.force_flush(timeout_millis=5000)
        print(f"✅ Generated {len(request_ids)} traces for scenario '{scenario}'")
        
    except Exception as e:
        print(f"⚠️  Error generating traces: {e}")


def generate_metrics(scenario: str) -> None:
    """Generate metrics via MetricsCollector."""
    if not METRICS_AVAILABLE:
        print(f"⚠️  Skipping metrics for scenario '{scenario}' (MetricsCollector not available)")
        return
    
    try:
        metrics = MetricsCollector()
        
        if scenario == "cost_optimization":
            # Model cost comparison
            metrics.increment_counter("llm.cost.total", 5.0)  # gpt-4o
            metrics.increment_counter("llm.cost.total", 1.0)  # gpt-4o-mini
            metrics.increment_counter("llm.cost.model.gpt_4o", 5.0)
            metrics.increment_counter("llm.cost.model.gpt_4o_mini", 1.0)
            metrics.increment_counter("llm.tokens.total", 50000)
            metrics.increment_counter("llm.tokens.model.gpt_4o", 25000)
            metrics.increment_counter("llm.tokens.model.gpt_4o_mini", 25000)
            
        elif scenario == "performance_bottleneck":
            # Agent latency
            for _ in range(20):
                metrics.record_histogram("agent.PlannerAgent.latency_ms", random.uniform(100, 500))
                metrics.record_histogram("agent.ExecutorAgent.latency_ms", random.uniform(3000, 8000))
            
        elif scenario == "policy_violations":
            # Policy violations
            metrics.increment_counter("policy.violations.total", 15)
            metrics.increment_counter("policy.violations.tool_call", 10)
            metrics.increment_counter("policy.violations.opa", 5)
            
        elif scenario == "error_patterns":
            # Error metrics
            metrics.increment_counter("tool.create_task.errors", 20)
            metrics.increment_counter("tool.update_task.errors", 10)
            metrics.increment_counter("agent.ExecutorAgent.errors", 30)
        
        # Common metrics
        metrics.increment_counter("workflow.runs", 10)
        metrics.increment_counter("workflow.success", 8)
        metrics.increment_counter("workflow.errors", 2)
        
        print(f"✅ Generated metrics for scenario '{scenario}'")
        
    except Exception as e:
        print(f"⚠️  Error generating metrics: {e}")


def generate_scenario_data(scenario: str) -> None:
    """Generate all data for a scenario."""
    print(f"\n📊 Generating data for scenario: {scenario}")
    print("=" * 60)
    
    if scenario == "cost_optimization":
        # Scenario 1: Cost Optimization
        request_ids = generate_workflow_logs(scenario, count=20)
        generate_policy_decisions(scenario, count=10)
        generate_traces(scenario, request_ids[:10])
        generate_metrics(scenario)
        
    elif scenario == "performance_bottleneck":
        # Scenario 2: Performance Bottleneck
        request_ids = generate_workflow_logs(scenario, count=20)
        generate_error_logs(scenario, count=5)
        generate_traces(scenario, request_ids, slow_agent=True)
        generate_metrics(scenario)
        
    elif scenario == "policy_violations":
        # Scenario 3: Policy Violations
        request_ids = generate_workflow_logs(scenario, count=10)
        generate_policy_decisions(scenario, count=15)  # Mix of allow/deny
        generate_traces(scenario, request_ids)
        generate_metrics(scenario)
        
    elif scenario == "error_patterns":
        # Scenario 4: Error Patterns
        request_ids = generate_workflow_logs(scenario, count=10)
        generate_error_logs(scenario, count=15)
        generate_policy_decisions(scenario, count=5)
        generate_traces(scenario, request_ids)
        generate_metrics(scenario)
    
    print(f"✅ Completed scenario: {scenario}")


def main():
    """Main function to generate all demo data."""
    print("🚀 Demo Data Generator")
    print("=" * 60)
    print(f"Logs file: {LOGS_FILE}")
    print(f"Decisions file: {DECISIONS_FILE}")
    print(f"OTLP endpoint: {OTLP_ENDPOINT}")
    print()
    
    # Clear existing files (optional - comment out to append)
    if LOGS_FILE.exists():
        LOGS_FILE.unlink()
        print(f"🗑️  Cleared existing logs file")
    
    if DECISIONS_FILE.exists():
        DECISIONS_FILE.unlink()
        print(f"🗑️  Cleared existing decisions file")
    
    # Generate data for all scenarios
    scenarios = [
        "cost_optimization",
        "performance_bottleneck",
        "policy_violations",
        "error_patterns"
    ]
    
    for scenario in scenarios:
        generate_scenario_data(scenario)
        time.sleep(1)  # Small delay between scenarios
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ Demo Data Generation Complete!")
    print("=" * 60)
    
    if LOGS_FILE.exists():
        log_count = sum(1 for _ in LOGS_FILE.open())
        print(f"📝 Logs: {log_count} entries in {LOGS_FILE}")
    
    if DECISIONS_FILE.exists():
        decision_count = sum(1 for _ in DECISIONS_FILE.open())
        print(f"📋 Decisions: {decision_count} entries in {DECISIONS_FILE}")
    
    print("\n📊 Next Steps:")
    print("1. Ensure Docker observability stack is running:")
    print("   docker-compose -f docker-compose.observability.yml up -d")
    print("2. Wait 30-60 seconds for Filebeat to ship logs to Elasticsearch")
    print("3. View data in:")
    print("   - Grafana: http://localhost:3000 (admin/admin)")
    print("   - Prometheus: http://localhost:9090")
    print("   - Jaeger: http://localhost:16686")
    print("   - Kibana: http://localhost:5601")
    print("\n4. Run verification script:")
    print("   python scripts/verify_demo_data.py")


if __name__ == "__main__":
    main()
