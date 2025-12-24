"""OpenTelemetry integration for distributed tracing."""
from __future__ import annotations

import logging
import asyncio
import time
from typing import Optional, Dict, Any, Callable

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None  # type: ignore
    TracerProvider = None  # type: ignore
    OTLPSpanExporter = None  # type: ignore
    BatchSpanProcessor = None  # type: ignore
    Resource = None  # type: ignore

logger = logging.getLogger(__name__)

# Suppress OpenTelemetry context errors during shutdown
_otel_context_logger = logging.getLogger("opentelemetry.context")
_otel_context_logger.setLevel(logging.CRITICAL)


class OpenTelemetryIntegration:
    """OpenTelemetry integration for distributed tracing."""

    def __init__(
        self,
        service_name: str = "agent-service",
        otlp_endpoint: str = "http://localhost:4317",
        enabled: bool = True,
        metrics_callback: Optional[Callable[[str, float], None]] = None,
    ):
        """Initialize OpenTelemetry integration.

        Args:
            service_name: Service name for traces
            otlp_endpoint: OTLP endpoint URL
            enabled: Whether to enable OpenTelemetry
            metrics_callback: Optional callback for tracking metrics (name, value)
        """
        self.service_name = service_name
        self.otlp_endpoint = otlp_endpoint
        self._enabled = enabled
        self._metrics_callback = metrics_callback

        self._otel_tracer_provider: Optional[TracerProvider] = None
        self._otel_tracer: Optional[trace.Tracer] = None
        self._span_contexts: Dict[str, Any] = {}
        self._trace_export_queue: Optional[asyncio.Queue] = None
        self._trace_export_worker: Optional[asyncio.Task] = None
        self._otel_health_check_interval: float = 30.0
        self._last_otel_health_check: float = 0.0
        self._otel_health_status: bool = True

        if enabled and OTEL_AVAILABLE:
            self._initialize()

    def _initialize(self) -> bool:
        """Initialize OpenTelemetry tracer provider."""
        if not OTEL_AVAILABLE:
            logger.warning("OpenTelemetry not available")
            return False

        try:
            # Create resource with service name
            resource = Resource.create({
                "service.name": self.service_name,
                "service.version": "1.0.0",
            })

            # Create tracer provider
            self._otel_tracer_provider = TracerProvider(resource=resource)

            # Create OTLP exporter
            try:
                exporter = OTLPSpanExporter(
                    endpoint=self.otlp_endpoint,
                    insecure=True,  # For local development
                )

                # Add batch processor
                span_processor = BatchSpanProcessor(exporter)
                self._otel_tracer_provider.add_span_processor(span_processor)

            except Exception as e:
                logger.warning(f"Failed to create OTLP exporter: {e}")
                self._enabled = False
                return False

            # Set global tracer provider
            trace.set_tracer_provider(self._otel_tracer_provider)

            # Get tracer
            self._otel_tracer = trace.get_tracer(__name__)

            # Initialize async export queue
            self._trace_export_queue = asyncio.Queue(maxsize=1000)

            logger.info(f"OpenTelemetry initialized (endpoint: {self.otlp_endpoint})")
            return True

        except Exception as e:
            logger.warning(f"Failed to initialize OpenTelemetry: {e}")
            self._enabled = False
            return False

    def get_tracer(self) -> Optional[trace.Tracer]:
        """Get OpenTelemetry tracer.

        Returns:
            OpenTelemetry tracer if initialized, None otherwise
        """
        return self._otel_tracer

    def start_export_worker(self) -> None:
        """Start the background trace export worker."""
        if self._trace_export_worker is None and self._trace_export_queue:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    self._trace_export_worker = asyncio.create_task(self._trace_export_worker_task())
            except RuntimeError:
                # No event loop yet, will start on first export
                pass

    async def shutdown(self) -> None:
        """Shutdown OpenTelemetry and stop background workers."""
        logger.info("Shutting down OpenTelemetry...")

        self._enabled = False

        # Stop trace export worker
        if self._trace_export_worker and not self._trace_export_worker.done():
            self._trace_export_worker.cancel()
            try:
                await self._trace_export_worker
            except asyncio.CancelledError:
                pass
            self._trace_export_worker = None

        # Process remaining items in queue
        if self._trace_export_queue:
            await asyncio.sleep(0.5)
            remaining = []
            while not self._trace_export_queue.empty():
                try:
                    span_data = self._trace_export_queue.get_nowait()
                    remaining.append(span_data)
                    self._trace_export_queue.task_done()
                except asyncio.QueueEmpty:
                    break

            if remaining:
                logger.debug(f"Exporting {len(remaining)} remaining spans before shutdown")
                for span_data in remaining:
                    try:
                        self._export_span_to_otel_sync(**span_data)
                    except Exception as e:
                        logger.debug(f"Failed to export remaining span: {e}")

        # Clean up
        self._span_contexts.clear()

        # Force flush
        if self._otel_tracer_provider:
            try:
                for processor in self._otel_tracer_provider._span_processors:
                    if hasattr(processor, "force_flush"):
                        try:
                            processor.force_flush(timeout_millis=5000)
                        except Exception:
                            pass
            except Exception:
                pass

        # Shutdown tracer provider
        if self._otel_tracer_provider:
            try:
                self._otel_tracer_provider.shutdown()
            except Exception as e:
                logger.debug(f"Error shutting down tracer provider: {e}")

        logger.info("OpenTelemetry shutdown complete")

    def create_otel_span_for_tracking(
        self,
        span_id: str,
        span_name: str,
        request_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Create an OpenTelemetry span immediately when internal span starts.

        Args:
            span_id: Internal span ID
            span_name: Span name
            request_id: Optional request ID
            parent_span_id: Optional parent span ID
            tags: Optional tags
        """
        otel_tracer = self.get_tracer()
        if not otel_tracer:
            return

        try:
            from opentelemetry.trace import set_span_in_context

            # Get parent context - try multiple lookup strategies
            parent_context = None
            if parent_span_id:
                # Strategy 1: Direct lookup by span_id
                if parent_span_id in self._span_contexts:
                    stored_item = self._span_contexts[parent_span_id]
                    if hasattr(stored_item, "_otel_span"):
                        parent_span = stored_item._otel_span
                    else:
                        parent_span = stored_item
                    parent_context = set_span_in_context(parent_span)
                else:
                    # Strategy 2: Lookup by request_id:span_name pattern
                    # This handles cases where parent was stored with a different key
                    if request_id:
                        # Try to find parent by searching for matching request_id
                        for key, stored_item in self._span_contexts.items():
                            if isinstance(key, str) and request_id in key:
                                # Check if this might be the parent span
                                if hasattr(stored_item, "_otel_span"):
                                    parent_span = stored_item._otel_span
                                else:
                                    parent_span = stored_item
                                parent_context = set_span_in_context(parent_span)
                                logger.debug(f"Found parent span via request_id lookup: {key}")
                                break

            # Create span with proper context
            if parent_context:
                span_context_manager = otel_tracer.start_as_current_span(span_name, context=parent_context)
            else:
                span_context_manager = otel_tracer.start_as_current_span(span_name)

            # Enter the context to get the actual span
            otel_span = span_context_manager.__enter__()

            # Store span wrapper
            span_wrapper = type("SpanWrapper", (), {
                "_otel_span": otel_span,
                "_otel_context_manager": span_context_manager,
                "_context_entered": True,
            })()

            # Store for future child spans
            self._span_contexts[span_id] = span_wrapper
            if request_id:
                context_key = f"{request_id}:{span_name}"
                self._span_contexts[context_key] = span_wrapper

            # Set initial attributes
            if request_id:
                otel_span.set_attribute("request.id", request_id)
            if parent_span_id:
                otel_span.set_attribute("parent.span_id", parent_span_id)
            if tags:
                for key, value in tags.items():
                    attr_key = key.replace("_", ".") if "_" in key else key
                    str_value = str(value)
                    if len(str_value) > 500:
                        str_value = str_value[:500] + "..."
                    otel_span.set_attribute(attr_key, str_value)

        except Exception as e:
            logger.debug(f"Failed to create OpenTelemetry span for tracking: {e}")

    def export_span_to_otel(
        self,
        span_name: str,
        start_time: float,
        end_time: Optional[float],
        request_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        span_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        logs: Optional[list] = None,
    ) -> None:
        """Export a span to OpenTelemetry (async, non-blocking).

        Args:
            span_name: Span name
            start_time: Start time (Unix timestamp)
            end_time: End time (Unix timestamp, optional)
            request_id: Request ID for correlation
            parent_span_id: Parent span ID
            span_id: Internal span ID (for context tracking)
            tags: Span tags
            logs: Span logs
        """
        if not self._enabled:
            return

        # If span was already created for tracking, just update and end it
        if span_id and span_id in self._span_contexts:
            try:
                stored_item = self._span_contexts[span_id]
                if hasattr(stored_item, "_otel_span"):
                    otel_span = stored_item._otel_span
                else:
                    otel_span = stored_item

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
                                attributes={k: str(v) for k, v in fields.items() if k != "event"},
                            )

                # End the span
                otel_span.end()
                return
            except Exception as e:
                logger.warning(f"Failed to update existing OpenTelemetry span {span_id}: {e}")
                return

        # Queue for async export
        span_data = {
            "span_name": span_name,
            "start_time": start_time,
            "end_time": end_time,
            "request_id": request_id,
            "parent_span_id": parent_span_id,
            "span_id": span_id,
            "tags": tags,
            "logs": logs,
        }

        # Start worker if needed
        self.start_export_worker()

        if self._trace_export_queue:
            try:
                self._trace_export_queue.put_nowait(span_data)
            except asyncio.QueueFull:
                logger.debug("Trace export queue full, dropping span")
                if self._metrics_callback:
                    try:
                        self._metrics_callback("trace_export_failures", 1.0)
                    except Exception:
                        pass

    async def _trace_export_worker_task(self) -> None:
        """Background worker task for async trace export."""
        logger.info("Trace export worker started")

        while self._enabled:
            try:
                try:
                    span_data = await asyncio.wait_for(self._trace_export_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    await self._check_otel_collector_health()
                    continue

                if not await self._check_otel_collector_health():
                    logger.debug("Skipping trace export - collector unhealthy")
                    self._trace_export_queue.task_done()
                    continue

                export_start = time.time()
                try:
                    self._export_span_to_otel_sync(**span_data)
                    export_latency = (time.time() - export_start) * 1000

                    # Track metrics via callback
                    if self._metrics_callback:
                        try:
                            self._metrics_callback("trace_export_latency_ms", export_latency)
                            if self._trace_export_queue:
                                self._metrics_callback("trace_export_queue_size", float(self._trace_export_queue.qsize()))
                            self._metrics_callback("otel_collector_health", 1.0 if self._otel_health_status else 0.0)
                        except Exception:
                            pass

                except Exception as e:
                    logger.debug(f"Failed to export span to OpenTelemetry: {e}")
                    self._otel_health_status = False
                    if self._metrics_callback:
                        try:
                            self._metrics_callback("trace_export_failures", 1.0)
                            self._metrics_callback("otel_collector_health", 0.0)
                        except Exception:
                            pass

                self._trace_export_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in trace export worker: {e}", exc_info=True)
                await asyncio.sleep(1)

        logger.info("Trace export worker stopped")

    async def _check_otel_collector_health(self) -> bool:
        """Check if OpenTelemetry collector is healthy."""
        current_time = time.time()
        if current_time - self._last_otel_health_check < self._otel_health_check_interval:
            return self._otel_health_status

        self._last_otel_health_check = current_time

        try:
            otel_tracer = self.get_tracer()
            if not otel_tracer:
                self._otel_health_status = False
                return False

            # Check queue size as proxy for health
            if self._trace_export_queue and self._trace_export_queue.qsize() > 500:
                logger.warning("OpenTelemetry export queue backing up (>500 items)")
                self._otel_health_status = False
                return False

            self._otel_health_status = True
            return True
        except Exception:
            self._otel_health_status = False
            return False

    def _export_span_to_otel_sync(
        self,
        span_name: str,
        start_time: float,
        end_time: Optional[float],
        request_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        span_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        logs: Optional[list] = None,
    ) -> None:
        """Synchronously export a span to OpenTelemetry (internal function)."""
        otel_tracer = self.get_tracer()
        if not otel_tracer:
            return

        try:
            from opentelemetry.trace import set_span_in_context

            # Try to get parent span context
            parent_context = None
            if parent_span_id and parent_span_id in self._span_contexts:
                stored_item = self._span_contexts[parent_span_id]
                if hasattr(stored_item, "_otel_span"):
                    parent_span = stored_item._otel_span
                else:
                    parent_span = stored_item
                parent_context = set_span_in_context(parent_span)

            # Create span
            if parent_context:
                span_context_manager = otel_tracer.start_as_current_span(span_name, context=parent_context)
            else:
                span_context_manager = otel_tracer.start_as_current_span(span_name)

            span = span_context_manager.__enter__()

            # Store span context
            if span_id:
                self._span_contexts[span_id] = span
            elif request_id:
                context_key = f"{request_id}:{span_name}"
                self._span_contexts[context_key] = span

            # Set attributes
            if request_id:
                span.set_attribute("request.id", request_id)
            if parent_span_id:
                span.set_attribute("parent.span_id", parent_span_id)
            if tags:
                for key, value in tags.items():
                    attr_key = key.replace("_", ".") if "_" in key else key
                    str_value = str(value)
                    if len(str_value) > 500:
                        str_value = str_value[:500] + "..."
                    span.set_attribute(attr_key, str_value)

            # Add events (logs)
            if logs:
                for log_entry in logs:
                    if isinstance(log_entry, dict):
                        if "fields" in log_entry:
                            fields = log_entry["fields"]
                            event_name = fields.get("event", "log")
                            timestamp = log_entry.get("timestamp", start_time)
                            event_timestamp = int(timestamp * 1e9) if isinstance(timestamp, (int, float)) else None
                            span.add_event(
                                event_name,
                                timestamp=event_timestamp,
                                attributes={k: str(v) for k, v in fields.items() if k != "event"},
                            )

            # Set span status and end
            from opentelemetry.trace import Status, StatusCode
            span.set_status(Status(StatusCode.OK))
            span.end()

            # Exit context manager
            try:
                span_context_manager.__exit__(None, None, None)
            except (ValueError, RuntimeError):
                pass
            except Exception as e:
                logger.debug(f"Error exiting context manager: {e}")

        except Exception as e:
            logger.debug(f"Failed to export span to OpenTelemetry: {e}")
            raise
