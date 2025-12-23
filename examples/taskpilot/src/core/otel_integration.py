"""OpenTelemetry integration for distributed tracing."""
import logging
import asyncio
import time
from typing import Optional, Dict, Any
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

logger = logging.getLogger(__name__)

# Suppress OpenTelemetry context errors during shutdown
# These are harmless errors that occur when context managers are cleaned up
# in a different async context than where they were created
_otel_context_logger = logging.getLogger("opentelemetry.context")
_otel_context_logger.setLevel(logging.CRITICAL)  # Only show critical errors, suppress ERROR level

# Global OpenTelemetry tracer provider
_otel_tracer_provider: Optional[TracerProvider] = None
_otel_tracer: Optional[trace.Tracer] = None

# Store span contexts for parent-child relationships
# Maps our internal span_id -> OpenTelemetry span context
_span_contexts: dict = {}

# Async trace export queue and worker
_trace_export_queue: Optional[asyncio.Queue] = None
_trace_export_worker: Optional[asyncio.Task] = None
_otel_enabled: bool = True
_otel_health_check_interval: float = 30.0  # Check collector health every 30 seconds
_last_otel_health_check: float = 0.0
_otel_health_status: bool = True


def initialize_opentelemetry(
    service_name: str = "taskpilot",
    otlp_endpoint: str = "http://localhost:4317",
    enabled: bool = True
) -> bool:
    """Initialize OpenTelemetry tracing.
    
    Args:
        service_name: Service name for traces
        otlp_endpoint: OTLP endpoint URL
        enabled: Whether to enable OpenTelemetry
        
    Returns:
        True if initialized successfully, False otherwise
    """
    global _otel_tracer_provider, _otel_tracer, _otel_enabled, _trace_export_queue, _trace_export_worker
    
    _otel_enabled = enabled
    
    if not enabled:
        logger.info("OpenTelemetry disabled")
        return False
    
    try:
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        
        # Create resource with service name
        resource = Resource.create({
            "service.name": service_name,
            "service.version": "1.0.0"
        })
        
        # Create tracer provider
        _otel_tracer_provider = TracerProvider(resource=resource)
        
        # Create OTLP exporter
        try:
            exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                insecure=True  # For local development
            )
            
            # Add batch processor
            span_processor = BatchSpanProcessor(exporter)
            _otel_tracer_provider.add_span_processor(span_processor)
            
        except Exception as e:
            logger.warning(f"Failed to create OTLP exporter: {e}")
            logger.warning("Traces will only be saved to file, not sent to Jaeger")
            _otel_enabled = False
            return False
        
        # Set global tracer provider
        trace.set_tracer_provider(_otel_tracer_provider)
        
        # Get tracer
        _otel_tracer = trace.get_tracer(__name__)
        
        # Initialize async export queue
        _trace_export_queue = asyncio.Queue(maxsize=1000)
        
        # Start background worker for async export
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                _trace_export_worker = asyncio.create_task(_trace_export_worker_task())
            else:
                # If no event loop, we'll start worker on first export
                pass
        except RuntimeError:
            # No event loop yet, will start on first export
            pass
        
        logger.info(f"OpenTelemetry initialized (endpoint: {otlp_endpoint}, async export enabled)")
        return True
        
    except Exception as e:
        logger.warning(f"Failed to initialize OpenTelemetry: {e}")
        logger.warning("Traces will only be saved to file, not sent to Jaeger")
        _otel_enabled = False
        return False


def get_otel_tracer() -> Optional[trace.Tracer]:
    """Get OpenTelemetry tracer.
    
    Returns:
        OpenTelemetry tracer if initialized, None otherwise
    """
    return _otel_tracer


async def _check_otel_collector_health() -> bool:
    """Check if OpenTelemetry collector is healthy.
    
    Returns:
        True if collector is healthy, False otherwise
    """
    global _last_otel_health_check, _otel_health_status
    
    current_time = time.time()
    # Only check every 30 seconds to avoid overhead
    if current_time - _last_otel_health_check < _otel_health_check_interval:
        return _otel_health_status
    
    _last_otel_health_check = current_time
    
    # Simple health check: try to create a test span
    # If export fails quickly, collector is likely down
    try:
        otel_tracer = get_otel_tracer()
        if not otel_tracer:
            _otel_health_status = False
            return False
        
        # Try a quick export test (this is lightweight)
        # We'll use the queue size as a proxy for health
        # If queue is backing up, collector might be slow
        if _trace_export_queue and _trace_export_queue.qsize() > 500:
            logger.warning("OpenTelemetry export queue backing up (>500 items), collector may be slow")
            _otel_health_status = False
            return False
        
        _otel_health_status = True
        return True
    except Exception:
        _otel_health_status = False
        return False


async def _trace_export_worker_task():
    """Background worker task for async trace export."""
    global _otel_enabled, _otel_health_status, _trace_export_queue
    
    logger.info("Trace export worker started")
    
    while _otel_enabled:
        try:
            # Get span data from queue (with timeout to allow health checks)
            try:
                span_data = await asyncio.wait_for(_trace_export_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                # Timeout is normal, check health and continue
                await _check_otel_collector_health()
                continue
            
            # Check collector health periodically
            if not await _check_otel_collector_health():
                # Collector is unhealthy, skip export but keep span data
                # (we'll retry later or it will be lost - acceptable for observability)
                logger.debug("Skipping trace export - collector unhealthy")
                _trace_export_queue.task_done()
                continue
            
            # Export span synchronously (this is the actual export)
            export_start = time.time()
            try:
                _export_span_to_otel_sync(**span_data)
                export_latency = (time.time() - export_start) * 1000
                
                # Track export latency metric and update collector health
                try:
                    from .observability import get_metrics_collector
                    from .metric_names import (
                        OBSERVABILITY_TRACE_EXPORT_LATENCY_MS,
                        OBSERVABILITY_TRACE_EXPORT_QUEUE_SIZE,
                        OBSERVABILITY_OTEL_COLLECTOR_HEALTH
                    )
                    metrics = get_metrics_collector()
                    metrics.record_histogram(OBSERVABILITY_TRACE_EXPORT_LATENCY_MS, export_latency)
                    if _trace_export_queue:
                        metrics.set_gauge(OBSERVABILITY_TRACE_EXPORT_QUEUE_SIZE, _trace_export_queue.qsize())
                    # Update collector health (1.0 = healthy, 0.0 = unhealthy)
                    metrics.set_gauge(OBSERVABILITY_OTEL_COLLECTOR_HEALTH, 1.0 if _otel_health_status else 0.0)
                except Exception:
                    pass  # Don't fail on metrics tracking
                
            except Exception as e:
                logger.debug(f"Failed to export span to OpenTelemetry: {e}")
                # Track export failures and mark collector as unhealthy
                _otel_health_status = False
                try:
                    from .observability import get_metrics_collector
                    from .metric_names import (
                        OBSERVABILITY_TRACE_EXPORT_FAILURES,
                        OBSERVABILITY_OTEL_COLLECTOR_HEALTH
                    )
                    metrics = get_metrics_collector()
                    metrics.increment_counter(OBSERVABILITY_TRACE_EXPORT_FAILURES)
                    metrics.set_gauge(OBSERVABILITY_OTEL_COLLECTOR_HEALTH, 0.0)
                except Exception:
                    pass
            
            _trace_export_queue.task_done()
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in trace export worker: {e}", exc_info=True)
            await asyncio.sleep(1)  # Wait before retry
    
    logger.info("Trace export worker stopped")


async def shutdown_opentelemetry():
    """Shutdown OpenTelemetry and stop background workers.
    
    This should be called when the application is shutting down to ensure
    all traces are exported and background tasks are stopped.
    """
    global _otel_enabled, _trace_export_worker, _trace_export_queue, _otel_tracer_provider
    
    logger.info("Shutting down OpenTelemetry...")
    
    # Disable OpenTelemetry to stop worker loop
    _otel_enabled = False
    
    # Stop trace export worker
    if _trace_export_worker and not _trace_export_worker.done():
        _trace_export_worker.cancel()
        try:
            await _trace_export_worker
        except asyncio.CancelledError:
            pass
        _trace_export_worker = None
    
    # Process remaining items in queue (give it a moment)
    if _trace_export_queue:
        # Wait a bit for any in-flight exports
        await asyncio.sleep(0.5)
        
        # Export any remaining spans in queue
        remaining = []
        while not _trace_export_queue.empty():
            try:
                span_data = _trace_export_queue.get_nowait()
                remaining.append(span_data)
                _trace_export_queue.task_done()
            except asyncio.QueueEmpty:
                break
        
        if remaining:
            logger.debug(f"Exporting {len(remaining)} remaining spans before shutdown")
            for span_data in remaining:
                try:
                    _export_span_to_otel_sync(**span_data)
                except Exception as e:
                    logger.debug(f"Failed to export remaining span: {e}")
    
    # Clean up any remaining context managers before shutdown
    # Note: We don't try to exit context managers here because they may have been
    # created in a different async context, which causes ValueError when trying to detach.
    # Instead, we just clear the store and let OpenTelemetry handle cleanup.
    # The context errors that appear are from OpenTelemetry's internal cleanup and are harmless.
    _span_contexts.clear()
    
    # Force flush any pending spans before shutdown
    if _otel_tracer_provider:
        try:
            # Get all span processors and force flush
            for processor in _otel_tracer_provider._span_processors:
                if hasattr(processor, 'force_flush'):
                    try:
                        processor.force_flush(timeout_millis=5000)
                    except Exception:
                        pass
        except Exception:
            pass
    
    # Shutdown tracer provider (this flushes any remaining spans)
    if _otel_tracer_provider:
        try:
            _otel_tracer_provider.shutdown()
        except Exception as e:
            logger.debug(f"Error shutting down tracer provider: {e}")
    
    logger.info("OpenTelemetry shutdown complete")


def create_otel_span_for_tracking(span):
    """Create an OpenTelemetry span immediately when our internal span starts.
    
    This ensures parent-child relationships work correctly even with async export.
    The span is created but not ended until the internal span ends.
    
    Args:
        span: Our internal Span object (from observability.py)
    """
    global _span_contexts
    
    otel_tracer = get_otel_tracer()
    if not otel_tracer:
        return
    
    try:
        from opentelemetry.trace import set_span_in_context
        
        # Get parent context - CRITICAL for ensuring all spans share the same trace ID
        # Strategy: Try parent_span_id first, then fallback to request_id lookup for workflow.run
        parent_context = None
        parent_found_via = None
        from .trace_names import WORKFLOW_RUN
        
        # First, try to find parent by parent_span_id (most direct)
        if span.parent_span_id and span.parent_span_id in _span_contexts:
            stored_item = _span_contexts[span.parent_span_id]
            if hasattr(stored_item, '_otel_span'):
                parent_span = stored_item._otel_span
            else:
                parent_span = stored_item
            parent_context = set_span_in_context(parent_span)
            parent_found_via = "parent_span_id"
        
        # If not found and we have request_id, look for workflow.run span
        # This is critical for agent spans to find their parent workflow
        if not parent_context and span.request_id:
            # Try direct key lookup first (fastest)
            workflow_key = f"{span.request_id}:{WORKFLOW_RUN}"
            if workflow_key in _span_contexts:
                stored_item = _span_contexts[workflow_key]
                if hasattr(stored_item, '_otel_span'):
                    parent_span = stored_item._otel_span
                else:
                    parent_span = stored_item
                parent_context = set_span_in_context(parent_span)
                parent_found_via = "request_id:workflow.run"
            else:
                # Fallback: search all keys (slower but more robust)
                for key, stored_item in list(_span_contexts.items()):
                    if isinstance(key, str) and span.request_id in key and WORKFLOW_RUN in key:
                        if hasattr(stored_item, '_otel_span'):
                            parent_span = stored_item._otel_span
                        else:
                            parent_span = stored_item
                        parent_context = set_span_in_context(parent_span)
                        parent_found_via = f"fallback_search:{key}"
                        break
        
        # Create span with proper context for hierarchy
        # CRITICAL: Use parent_context to ensure all spans share the same trace ID
        # When parent_context is provided, the child span inherits the parent's trace ID
        if parent_context:
            # Create child span with parent context - this ensures same trace ID
            span_context_manager = otel_tracer.start_as_current_span(span.name, context=parent_context)
        else:
            # For root spans (like workflow.run), create without parent
            # This will generate a new trace ID that child spans will inherit
            span_context_manager = otel_tracer.start_as_current_span(span.name)
        
        # Enter the context to get the actual span
        otel_span = span_context_manager.__enter__()
        
        # Store both span and context manager for future use
        span_wrapper = type('SpanWrapper', (), {
            '_otel_span': otel_span,
            '_otel_context_manager': span_context_manager,
            '_context_entered': True
        })()
        
        # Store span wrapper for future child spans (keyed by our internal span_id)
        _span_contexts[span.span_id] = span_wrapper
        
        # Also store by request_id + name for fallback lookup
        # This is CRITICAL for finding parent spans when parent_span_id lookup fails
        # Agent spans use this to find the workflow.run span
        if span.request_id:
            context_key = f"{span.request_id}:{span.name}"
            _span_contexts[context_key] = span_wrapper
            # Also store just by request_id for even broader lookup
            # This helps when the exact span name isn't known
            if span.name == "workflow.run":
                _span_contexts[f"{span.request_id}:workflow"] = span_wrapper
        
        # Store references on our span object for easy access
        span._otel_span = otel_span
        span._otel_context_manager = span_context_manager
        
        # Log trace ID for debugging hierarchy issues
        try:
            trace_id = format(otel_span.get_span_context().trace_id, '032x')
            span_id_otel = format(otel_span.get_span_context().span_id, '016x')
            if span.request_id:
                logger.info(
                    f"OTEL span: name={span.name}, trace_id={trace_id}, "
                    f"request_id={span.request_id[:8]}, "
                    f"parent_found={'yes' if parent_context else 'NO'}, "
                    f"via={parent_found_via or 'none'}, "
                    f"parent_span_id={span.parent_span_id[:8] if span.parent_span_id else 'none'}"
                )
        except Exception:
            pass
        
        # Set initial attributes
        if span.request_id:
            otel_span.set_attribute("request.id", span.request_id)
        if span.parent_span_id:
            otel_span.set_attribute("parent.span_id", span.parent_span_id)
        if span.tags:
            for key, value in span.tags.items():
                attr_key = key.replace("_", ".") if "_" in key else key
                str_value = str(value)
                if len(str_value) > 500:
                    str_value = str_value[:500] + "..."
                otel_span.set_attribute(attr_key, str_value)
        
    except Exception as e:
        logger.debug(f"Failed to create OpenTelemetry span for tracking: {e}")


def export_span_to_otel(
    span_name: str,
    start_time: float,
    end_time: Optional[float],
    request_id: Optional[str] = None,
    parent_span_id: Optional[str] = None,
    span_id: Optional[str] = None,
    tags: Optional[dict] = None,
    logs: Optional[list] = None
):
    """Export a span to OpenTelemetry (async, non-blocking).
    
    This function queues the span for async export by a background worker.
    The actual export happens in a background task.
    
    Args:
        span_name: Span name
        start_time: Start time (Unix timestamp)
        end_time: End time (Unix timestamp, optional)
        request_id: Request ID for correlation
        parent_span_id: Parent span ID (from our internal span system)
        span_id: Our internal span ID (for context tracking)
        tags: Span tags
        logs: Span logs
        
    The actual export happens in a background worker task.
    """
    if not _otel_enabled:
        return
    
    # If span was already created for tracking, just update and end it
    # This is the PRIMARY path - we should ALWAYS find the span here
    if span_id and span_id in _span_contexts:
        try:
            stored_item = _span_contexts[span_id]
            # Handle both wrapped spans and direct spans
            if hasattr(stored_item, '_otel_span'):
                otel_span = stored_item._otel_span
                context_manager = getattr(stored_item, '_otel_context_manager', None)
            else:
                otel_span = stored_item
                context_manager = None
            
            # Update attributes
            if tags:
                for key, value in tags.items():
                    attr_key = key.replace("_", ".") if "_" in key else key
                    str_value = str(value)
                    if len(str_value) > 500:
                        str_value = str_value[:500] + "..."
                    otel_span.set_attribute(attr_key, str_value)
            
            # Add events (logs)
            if logs:
                for log_entry in logs:
                    if isinstance(log_entry, dict) and "fields" in log_entry:
                        fields = log_entry["fields"]
                        event_name = fields.get("event", "log")
                        timestamp = log_entry.get("timestamp", start_time)
                        event_timestamp = int(timestamp * 1e9) if isinstance(timestamp, (int, float)) else None
                        otel_span.add_event(
                            event_name,
                            timestamp=event_timestamp,
                            attributes={
                                k: str(v) for k, v in fields.items() if k != "event"
                            }
                        )
            
            # End the span
            # Note: OpenTelemetry spans don't support end_time_ns parameter
            # The span will use the current time when end() is called
            otel_span.end()
            
            # Log successful export
            if logger.isEnabledFor(logging.DEBUG):
                try:
                    trace_id = format(otel_span.get_span_context().trace_id, '032x')
                    logger.debug(f"Exported span {span_name} (span_id={span_id[:8]}, trace_id={trace_id})")
                except Exception:
                    pass
            
            return
        except Exception as e:
            logger.warning(f"Failed to update existing OpenTelemetry span {span_id}: {e}")
            # Don't fall through - if we can't update existing span, something is wrong
            # Log the error but don't create duplicate spans
            return
    
    # Fallback: Create span synchronously if worker not available
    if _trace_export_worker is None or _trace_export_worker.done():
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                # No event loop, export synchronously
                try:
                    _export_span_to_otel_sync(
                        span_name=span_name,
                        start_time=start_time,
                        end_time=end_time,
                        request_id=request_id,
                        parent_span_id=parent_span_id,
                        span_id=span_id,
                        tags=tags,
                        logs=logs
                    )
                except Exception:
                    pass
                return
        except RuntimeError:
            # No event loop, fall back to sync export
            try:
                _export_span_to_otel_sync(
                    span_name=span_name,
                    start_time=start_time,
                    end_time=end_time,
                    request_id=request_id,
                    parent_span_id=parent_span_id,
                    span_id=span_id,
                    tags=tags,
                    logs=logs
                )
            except Exception:
                pass
            return
    
    # Queue span data for async export
    span_data = {
        "span_name": span_name,
        "start_time": start_time,
        "end_time": end_time,
        "request_id": request_id,
        "parent_span_id": parent_span_id,
        "span_id": span_id,
        "tags": tags,
        "logs": logs
    }
    
    try:
        # Non-blocking put (raises QueueFull if queue is full)
        _trace_export_queue.put_nowait(span_data)
    except asyncio.QueueFull:
        # Queue is full, drop span (better than blocking)
        logger.debug("Trace export queue full, dropping span")
        try:
            from .observability import get_metrics_collector
            from .metric_names import OBSERVABILITY_TRACE_EXPORT_FAILURES
            metrics = get_metrics_collector()
            metrics.increment_counter(OBSERVABILITY_TRACE_EXPORT_FAILURES)
        except Exception:
            pass


def _export_span_to_otel_sync(
    span_name: str,
    start_time: float,
    end_time: Optional[float],
    request_id: Optional[str] = None,
    parent_span_id: Optional[str] = None,
    span_id: Optional[str] = None,
    tags: Optional[dict] = None,
    logs: Optional[list] = None
):
    """Synchronously export a span to OpenTelemetry (internal function).
    
    This is called by the async worker task. Do not call directly.
    """
    otel_tracer = get_otel_tracer()
    if not otel_tracer:
        return
    
    try:
        from opentelemetry import trace
        from opentelemetry.trace import Status, StatusCode
        from opentelemetry.trace import set_span_in_context
        
        global _span_contexts
        
        # Try to get parent span context if parent_span_id is provided
        parent_context = None
        if parent_span_id:
            # Look up parent span in our context store
            if parent_span_id in _span_contexts:
                stored_item = _span_contexts[parent_span_id]
                # Handle both wrapped spans and direct spans
                if hasattr(stored_item, '_otel_span'):
                    parent_span = stored_item._otel_span
                else:
                    parent_span = stored_item
                parent_context = set_span_in_context(parent_span)
            elif request_id:
                # Try alternative lookup: search for workflow.run span with same request_id
                from .trace_names import WORKFLOW_RUN
                for key, stored_item in _span_contexts.items():
                    if isinstance(key, str) and request_id in key and WORKFLOW_RUN in key:
                        # Handle both wrapped spans and direct spans
                        if hasattr(stored_item, '_otel_span'):
                            parent_span = stored_item._otel_span
                        else:
                            parent_span = stored_item
                        parent_context = set_span_in_context(parent_span)
                        break
        
        # Create span with proper context for hierarchy
        # Use start_as_current_span which returns a context manager
        if parent_context:
            span_context_manager = otel_tracer.start_as_current_span(span_name, context=parent_context)
        else:
            span_context_manager = otel_tracer.start_as_current_span(span_name)
        
        # Enter the context to get the actual span
        span = span_context_manager.__enter__()
        
        # Store span context for future child spans (keyed by our internal span_id)
        if span_id:
            _span_contexts[span_id] = span
        elif request_id:
            # Fallback: use request_id + name as key
            context_key = f"{request_id}:{span_name}"
            _span_contexts[context_key] = span
        
        # Set attributes with better naming for Jaeger
        if request_id:
            span.set_attribute("request.id", request_id)
        if parent_span_id:
            # Store parent span ID as attribute for reference (hierarchy is via context)
            span.set_attribute("parent.span_id", parent_span_id)
        if tags:
            for key, value in tags.items():
                # Use dot notation for better organization in Jaeger
                attr_key = key.replace("_", ".") if "_" in key else key
                # Truncate long values (Jaeger has limits)
                str_value = str(value)
                if len(str_value) > 500:
                    str_value = str_value[:500] + "..."
                span.set_attribute(attr_key, str_value)
        
        # Add events (logs) - extract from fields if present
        if logs:
            for log_entry in logs:
                if isinstance(log_entry, dict):
                    # Handle both direct log dicts and log entries with fields
                    if "fields" in log_entry:
                        fields = log_entry["fields"]
                        event_name = fields.get("event", "log")
                        timestamp = log_entry.get("timestamp", start_time)
                        # Convert timestamp to nanoseconds
                        event_timestamp = int(timestamp * 1e9) if isinstance(timestamp, (int, float)) else None
                        span.add_event(
                            event_name,
                            timestamp=event_timestamp,
                            attributes={
                                k: str(v) for k, v in fields.items() if k != "event"
                            }
                        )
                    else:
                        # Direct log entry
                        event_name = log_entry.get("event", "log")
                        timestamp = log_entry.get("timestamp", start_time)
                        event_timestamp = int(timestamp * 1e9) if isinstance(timestamp, (int, float)) else None
                        span.add_event(
                            event_name,
                            timestamp=event_timestamp,
                            attributes={
                                k: str(v) for k, v in log_entry.items() if k not in ("event", "timestamp")
                            }
                        )
        
        # Set span status
        span.set_status(Status(StatusCode.OK))
        
        # End span
        # Note: OpenTelemetry spans don't support end_time_ns parameter
        # The span will use the current time when end() is called
        span.end()
        
        # Exit context manager (suppress errors during shutdown)
        try:
            span_context_manager.__exit__(None, None, None)
        except (ValueError, RuntimeError):
            # Context errors during shutdown are expected and can be ignored
            pass
        except Exception as e:
            logger.debug(f"Error exiting context manager: {e}")
                
    except Exception as e:
        logger.debug(f"Failed to export span to OpenTelemetry: {e}")
        raise  # Re-raise so worker can track failures
