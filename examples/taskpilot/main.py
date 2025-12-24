"""TaskPilot main entry point."""
import asyncio
import sys
import logging
import time
import os
import argparse
from pathlib import Path
from taskpilot.agents import create_planner, create_reviewer, create_executor  # type: ignore
from taskpilot.core import build_workflow, create_audit_and_policy_middleware  # type: ignore
from taskpilot.core.observable import (  # type: ignore
    RequestContext,
    get_metrics,
    get_health,
    get_errors,
    get_tracer,
    setup_observability,
)
from taskpilot.core.metric_names import (  # type: ignore
    HEALTH_CHECK_TASK_STORE,
    HEALTH_CHECK_GUARDRAILS
)
from agent_observable_core import get_metric_standardizer  # type: ignore
# Initialize observability (one-line setup)
# This replaces all the adapter initialization code
try:
    from pathlib import Path
    base_dir = Path(__file__).parent
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    otel_enabled = os.environ.get("OTEL_ENABLED", "true").lower() == "true"
    otel_service_name = os.environ.get("OTEL_SERVICE_NAME", "taskpilot")
    
    from agent_observable_core import get_trace_standardizer  # type: ignore
    trace_standardizer = get_trace_standardizer(service_name=otel_service_name)
    TRACE_WORKFLOW_RUN = trace_standardizer.workflow_run()
    
    setup_observability(
        service_name=otel_service_name,
        base_dir=base_dir,
        enable_otel=otel_enabled,
        enable_guardrails=True,
        enable_policy=True,
        otlp_endpoint=otlp_endpoint,
        guardrails_config_path=base_dir / "guardrails" / "config.yml",
        policy_dir=base_dir / "policies",
        prompts_dir=base_dir / "prompts",
        decision_logs_file=base_dir / "decision_logs.jsonl",
    )
except Exception as e:
    # Observability setup failed, continue without it
    print(f"Warning: Observability setup failed: {e}")

# Load configuration early (before logging setup)
# Wrap in try-except to handle validation errors gracefully
try:
    from taskpilot.core.config import get_config, get_paths, get_app_config  # type: ignore
    config = get_config()
    paths = get_paths()
    app_config = get_app_config()
except Exception as e:
    # If config loading fails, print error and exit
    print(f"Error loading configuration: {e}")
    print("Make sure OPENAI_API_KEY is set in .env file or environment variable")
    sys.exit(1)

# Configure JSON logging
try:
    from pythonjsonlogger import jsonlogger
    
    # Use configured logs directory
    log_dir = paths.logs_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler (for development)
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (for Filebeat)
    log_file = log_dir / "taskpilot.log"
    file_handler = logging.FileHandler(log_file)
    json_formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        timestamp=True
    )
    file_handler.setFormatter(json_formatter)
    root_logger.addHandler(file_handler)
    
except ImportError:
    # python-json-logger not installed, use standard logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
except Exception as e:
    # JSON logging setup failed, use standard logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    print(f"Warning: JSON logging setup failed: {e}")

logger = logging.getLogger(__name__)

# FastAPI app for production (integrated metrics server)
app = None

def create_app():
    """Create FastAPI app with metrics endpoints."""
    try:
        from fastapi import FastAPI
        from fastapi.responses import Response
        
        app = FastAPI(title="TaskPilot")
        
        @app.get("/metrics")
        def metrics():
            """Prometheus metrics endpoint."""
            try:
                metrics = get_metrics()
                all_metrics = metrics.get_all_metrics()
                
                lines = []
                seen_types = {}  # Track TYPE declarations to avoid duplicates
                
                # Counters
                for name, value in all_metrics.get("counters", {}).items():
                    sanitized_name = name.replace(".", "_").replace("-", "_").lower()
                    if sanitized_name not in seen_types:
                        lines.append(f"# TYPE {sanitized_name} counter")
                        seen_types[sanitized_name] = "counter"
                    lines.append(f"{sanitized_name} {value}")
                
                # Gauges
                for name, value in all_metrics.get("gauges", {}).items():
                    sanitized_name = name.replace(".", "_").replace("-", "_").lower()
                    if sanitized_name not in seen_types:
                        lines.append(f"# TYPE {sanitized_name} gauge")
                        seen_types[sanitized_name] = "gauge"
                    lines.append(f"{sanitized_name} {value}")
                
                # Histograms
                for name, stats in all_metrics.get("histograms", {}).items():
                    sanitized_name = name.replace(".", "_").replace("-", "_").lower()
                    if sanitized_name not in seen_types:
                        lines.append(f"# TYPE {sanitized_name} histogram")
                        seen_types[sanitized_name] = "histogram"
                    lines.append(f"{sanitized_name}_count {stats['count']}")
                    lines.append(f"{sanitized_name}_sum {stats['avg'] * stats['count']}")
                    lines.append(f"{sanitized_name}_bucket{{le=\"+Inf\"}} {stats['count']}")
                    # Also expose p95 as a gauge for easier querying
                    if stats.get('p95', 0) > 0:
                        p95_name = f"{sanitized_name}_p95"
                        if p95_name not in seen_types:
                            lines.append(f"# TYPE {p95_name} gauge")
                            seen_types[p95_name] = "gauge"
                        lines.append(f"{p95_name} {stats['p95']}")
                
                # Ensure key metrics are always present (even if zero) for Prometheus discovery
                # This helps with Grafana dashboards that expect these metrics to exist
                key_metrics = {
                    "llm_cost_total": ("counter", "llm.cost.total"),
                    "policy_violations_total": ("counter", "policy.violations.total"),
                    "workflow_runs": ("counter", "workflow.runs"),
                    "workflow_success": ("counter", "workflow.success"),
                    "workflow_errors": ("counter", "workflow.errors"),
                }
                
                for prom_name, (metric_type, internal_name) in key_metrics.items():
                    if prom_name not in seen_types:
                        # Metric doesn't exist yet, initialize with 0
                        lines.append(f"# TYPE {prom_name} {metric_type}")
                        lines.append(f"{prom_name} 0")
                        seen_types[prom_name] = metric_type
                
                return Response("\n".join(lines), media_type="text/plain")
            except Exception as e:
                logger.error(f"Error generating metrics: {e}", exc_info=True)
                return Response("# Error generating metrics\n", media_type="text/plain", status_code=500)
        
        @app.get("/health")
        def health():
            """Health check endpoint."""
            try:
                health_checker = get_health()
                status = health_checker.check_health()
                
                # Also record health metrics for Prometheus (use standardized metric names)
                metrics = get_metrics()
                # Health status: 1 = healthy, 0.5 = degraded, 0 = unhealthy
                health_value = 1.0 if status.status == "healthy" else (0.5 if status.status == "degraded" else 0.0)
                # Use standardized health status metric
                metric_std = get_metric_standardizer(service_name=otel_service_name)
                metrics.set_gauge(metric_std.health_status(), health_value)
                
                # Record individual check statuses
                for check_name, check_result in status.checks.items():
                    check_value = 1.0 if check_result.get("status") == "pass" else 0.0
                    from taskpilot.core.metric_names import health_check
                    metrics.set_gauge(health_check(check_name), check_value)
                
                return {
                    "status": status.status,
                    "checks": status.checks,
                    "timestamp": time.time()
                }
            except Exception as e:
                logger.error(f"Error checking health: {e}", exc_info=True)
                # Record error in metrics
                try:
                    metrics = get_metrics()
                    metric_std = get_metric_standardizer(service_name=otel_service_name)
                    metrics.set_gauge(metric_std.health_status(), 0.0)
                except:
                    pass
                return {"status": "error", "error": str(e)}, 500
        
        @app.get("/cost-report")
        def cost_report(format: str = "text"):
            """Cost tracking report endpoint.
            
            Args:
                format: Output format ('text', 'json', 'csv')
            """
            try:
                from taskpilot.core.cost_viewer import create_cost_viewer
                viewer = create_cost_viewer()
                report = viewer.get_cost_report(format=format)
                
                if format == "json":
                    return Response(report, media_type="application/json")
                elif format == "csv":
                    return Response(report, media_type="text/csv")
                else:
                    return Response(report, media_type="text/plain")
            except Exception as e:
                logger.error(f"Error generating cost report: {e}", exc_info=True)
                return {"error": str(e)}, 500
        
        @app.get("/golden-signals")
        def golden_signals():
            """Golden Signals endpoint for LLM production monitoring."""
            try:
                metrics = get_metrics()
                signals = metrics.get_golden_signals()
                
                # Add status indicators
                signals["status"] = {
                    "success_rate": (
                        "healthy" if signals["success_rate"] >= 95 else
                        "warning" if signals["success_rate"] >= 90 else
                        "critical"
                    ),
                    "p95_latency": (
                        "healthy" if signals["p95_latency"] < 2000 else
                        "warning" if signals["p95_latency"] < 5000 else
                        "critical"
                    ),
                    "cost_per_task": (
                        "healthy" if signals["cost_per_successful_task"] < 0.10 else
                        "warning" if signals["cost_per_successful_task"] < 0.50 else
                        "critical"
                    ),
                    "policy_violations": (
                        "healthy" if signals["policy_violation_rate"] < 1 else
                        "warning" if signals["policy_violation_rate"] < 2 else
                        "critical"
                    )
                }
                
                return signals
            except Exception as e:
                logger.error(f"Error calculating golden signals: {e}", exc_info=True)
                return {"error": str(e)}, 500
        
        @app.get("/")
        def root():
            """Root endpoint with links."""
            return {
                "service": "TaskPilot",
                "endpoints": {
                    "metrics": "/metrics",
                    "health": "/health",
                    "golden_signals": "/golden-signals"
                },
                "observability": {
                    "grafana": app_config.grafana_url,
                    "prometheus": app_config.prometheus_url,
                    "jaeger": app_config.jaeger_url,
                    "kibana": app_config.kibana_url
                }
            }
        
        return app
    except ImportError:
        logger.warning("FastAPI not available. Install with: pip install fastapi uvicorn")
        return None

async def run_workflow_once():
    """Run a single workflow execution."""
    try:
        # Initialize health checks
        health_checker = get_health()
        
        # Register health checks
        def check_task_store():
            """Check task store health."""
            try:
                from taskpilot.core.task_store import get_task_store
                store = get_task_store()
                stats = store.get_stats()
                return True, "Task store operational", {"stats": stats}
            except Exception as e:
                return False, f"Task store error: {str(e)}", {}
        
        def check_guardrails():
            """Check guardrails health."""
            try:
                from taskpilot.core.observable import get_guardrails
                guardrails = get_guardrails()
                if guardrails:
                    return guardrails._enabled, "Guardrails available" if guardrails._enabled else "Guardrails disabled", {}
                return False, "Guardrails not configured", {}
            except Exception as e:
                return False, f"Guardrails error: {str(e)}", {}
        
        health_checker.register_check("task_store", check_task_store)
        health_checker.register_check("guardrails", check_guardrails)
        
        # Use request context for correlation
        with RequestContext() as req_ctx:
            request_id = req_ctx.request_id
            logger.info(f"Starting workflow (request_id={request_id})")
            
            # Create agents with error handling
            try:
                logger.info("Creating agents...")
                planner = create_planner()
                reviewer = create_reviewer()
                executor = create_executor()
                logger.info("Agents created successfully")
            except Exception as e:
                from taskpilot.core.observable import record_error
                record_error(e, operation="create_agents")
                logger.error(f"Error creating agents: {e}")
                logger.error("Make sure OPENAI_API_KEY is set in .env file")
                raise

            # Set middleware with agent name tracking
            logger.info("Setting up middleware...")
            planner.middleware = create_audit_and_policy_middleware(planner.name)
            reviewer.middleware = create_audit_and_policy_middleware(reviewer.name)
            executor.middleware = create_audit_and_policy_middleware(executor.name)

            # Build workflow
            try:
                logger.info("Building workflow...")
                workflow = build_workflow(planner, reviewer, executor)
                logger.info("Workflow built successfully")
            except Exception as e:
                from taskpilot.core.observable import record_error
                record_error(e, operation="build_workflow", request_id=request_id)
                logger.error(f"Error building workflow: {e}")
                raise

            # Run workflow with root span for hierarchy
            try:
                logger.info(f"Running workflow... (request_id={request_id})")
                metrics = get_metrics()
                # Use standardized metric names
                metric_std = get_metric_standardizer(service_name=otel_service_name)
                metrics.increment_counter(metric_std.workflow_runs())
                
                # Create workflow-level root span (use standardized trace name)
                from taskpilot.core.observable import TraceContext
                with TraceContext(
                    name=TRACE_WORKFLOW_RUN,  # "taskpilot.workflow.run"
                    request_id=request_id,
                    tags={"workflow_type": "task_creation"}
                ) as workflow_span:
                    workflow_start = time.time()
                    result = await workflow.run(
                        "Create a high priority task to prepare the board deck"
                    )
                    workflow_latency = (time.time() - workflow_start) * 1000
                    
                    # Add workflow metrics to span
                    workflow_span.tags["workflow_latency_ms"] = str(workflow_latency)
                    workflow_span.tags["workflow_success"] = "true"
                    
                    # Record workflow metrics (use standardized names)
                    metrics.record_histogram(metric_std.workflow_latency_ms(), workflow_latency)
                    metrics.increment_counter(metric_std.workflow_success())
                
                logger.info(f"Workflow completed successfully (request_id={request_id}, latency={workflow_latency:.2f}ms)")
                
                # Extract reviewer decision from workflow events and update task if needed
                # The workflow returns a list of events, and we can find the ReviewerAgent's response
                if isinstance(result, list):
                    for event in result:
                        # Look for AgentRunEvent from ReviewerAgent
                        if hasattr(event, 'executor_id') and event.executor_id == 'ReviewerAgent':
                            if hasattr(event, 'data') and event.data:
                                reviewer_output = str(event.data).upper()
                                # Get the most recent PENDING task and update it
                                from taskpilot.core.task_store import get_task_store, TaskStatus
                                store = get_task_store()
                                pending_tasks = store.list_tasks(status=TaskStatus.PENDING, limit=1)
                                if pending_tasks:
                                    task = pending_tasks[0]
                                    if "APPROVE" in reviewer_output:
                                        store.update_task_status(
                                            task.id,
                                            TaskStatus.APPROVED,
                                            reviewer_response=str(event.data)
                                        )
                                        logger.info(f"[TASK] Task {task.id} approved (from workflow events, request_id={request_id})")
                                    elif "REVIEW" in reviewer_output:
                                        store.update_task_status(
                                            task.id,
                                            TaskStatus.REVIEW,
                                            reviewer_response=str(event.data)
                                        )
                                        logger.info(f"[TASK] Task {task.id} requires human review (from workflow events, request_id={request_id})")
                                    else:
                                        store.update_task_status(
                                            task.id,
                                            TaskStatus.REJECTED,
                                            reviewer_response=str(event.data)
                                        )
                                        logger.info(f"[TASK] Task {task.id} rejected (from workflow events, request_id={request_id})")
                
                print("\nFINAL RESULT")
                print(result)
                return result
            except Exception as e:
                from taskpilot.core.observable import record_error
                record_error(e, operation="run_workflow", request_id=request_id)
                metrics = get_metrics()
                metrics.increment_counter(metric_std.workflow_errors())
                logger.error(f"Error running workflow: {e} (request_id={request_id})", exc_info=True)
                raise
    
    except KeyboardInterrupt:
        logger.warning("Workflow interrupted by user")
        raise
    except Exception as e:
        from taskpilot.core.observable import record_error
        record_error(e, operation="run_workflow_once")
        logger.exception(f"Unexpected error in workflow: {e}")
        raise

async def main(server_mode: bool = False, port: int = 8000):
    """Main entry point.
    
    Args:
        server_mode: If True, run only HTTP server with metrics endpoints (no workflow). If False, run workflow once and exit.
        port: Port for HTTP server (only used in server_mode)
    """
    try:
        if server_mode:
            # Server mode: Run HTTP server ONLY (metrics/health endpoints, no workflow)
            app = create_app()
            if app is None:
                logger.error("FastAPI not available. Install with: pip install fastapi uvicorn")
                logger.error("Cannot run in server mode without FastAPI")
                sys.exit(1)
            
            logger.info(f"Starting TaskPilot metrics server on port {port}")
            logger.info(f"  Metrics: http://localhost:{port}/metrics")
            logger.info(f"  Health: http://localhost:{port}/health")
            logger.info(f"  Golden Signals: http://localhost:{port}/golden-signals")
            logger.info(f"  Cost Report: http://localhost:{port}/cost-report")
            logger.info("")
            logger.info("Note: Server mode only exposes metrics endpoints.")
            logger.info("      Run workflows separately: python main.py <task_description>")
            
            # Start HTTP server (no workflow loop)
            import uvicorn
            uvicorn_config = uvicorn.Config(app, host=app_config.host, port=port, log_level="info")
            server = uvicorn.Server(uvicorn_config)
            await server.serve()
            return
        
        # Workflow mode: Run workflow once and exit
        try:
            await run_workflow_once()
            
            # Cleanup background tasks before exiting
            logger.info("Cleaning up background tasks...")
            
            # Stop decision logger background flush task
            try:
                from taskpilot.core.guardrails.decision_logger import get_decision_logger
                decision_logger = get_decision_logger()
                # Only stop if it was started (has a flush task)
                if decision_logger._flush_task is not None:
                    await decision_logger.stop()
                    logger.debug("Decision logger stopped")
            except Exception as e:
                logger.debug(f"Error stopping decision logger: {e}")
            
            # Stop OpenTelemetry trace export worker
            try:
                from taskpilot.core.observable import get_otel
                otel = get_otel()
                if otel:
                    await otel.shutdown()
                await shutdown_opentelemetry()
                logger.debug("OpenTelemetry shutdown complete")
            except Exception as e:
                logger.debug(f"Error shutting down OpenTelemetry: {e}")
            
            # Give background tasks a moment to finish
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        from taskpilot.core.observable import record_error
        record_error(e, operation="main")
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TaskPilot - Agent Framework Reference App")
    parser.add_argument(
        "--server",
        action="store_true",
        help="Run as HTTP server with metrics endpoints only (no workflow execution). Keep this running for Prometheus scraping."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=f"Port for HTTP server (default: {app_config.port}, or PORT env var)"
    )
    args = parser.parse_args()
    
    # Use CLI port if provided, otherwise use config
    port = args.port if args.port is not None else app_config.port
    
    asyncio.run(main(server_mode=args.server, port=port))
