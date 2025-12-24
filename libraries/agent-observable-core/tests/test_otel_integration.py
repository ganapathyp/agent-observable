"""Unit tests for OpenTelemetry integration."""
import pytest
from unittest.mock import MagicMock, patch

try:
    from agent_observable_core.otel_integration import OpenTelemetryIntegration
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    OpenTelemetryIntegration = None  # type: ignore


@pytest.mark.skipif(not OTEL_AVAILABLE, reason="OpenTelemetry not available")
class TestOpenTelemetryIntegration:
    """Test OpenTelemetry integration."""

    def test_initialization_disabled(self):
        """Can initialize with OpenTelemetry disabled."""
        integration = OpenTelemetryIntegration(enabled=False)
        assert integration._enabled is False
        assert integration.get_tracer() is None

    @patch('agent_observable_core.otel_integration.trace')
    @patch('agent_observable_core.otel_integration.TracerProvider')
    @patch('agent_observable_core.otel_integration.OTLPSpanExporter')
    @patch('agent_observable_core.otel_integration.BatchSpanProcessor')
    @patch('agent_observable_core.otel_integration.Resource')
    def test_initialization_success(self, mock_resource, mock_processor, mock_exporter, mock_provider, mock_trace):
        """Can initialize OpenTelemetry successfully."""
        mock_trace.set_tracer_provider = MagicMock()
        mock_trace.get_tracer.return_value = MagicMock()
        mock_provider.return_value = MagicMock()

        integration = OpenTelemetryIntegration(
            service_name="test-service",
            otlp_endpoint="http://localhost:4317",
            enabled=True,
        )

        assert integration._enabled is True
        assert integration.service_name == "test-service"
        assert integration.otlp_endpoint == "http://localhost:4317"

    def test_metrics_callback(self):
        """Metrics callback is invoked when provided."""
        callback_calls = []

        def metrics_callback(name: str, value: float) -> None:
            callback_calls.append((name, value))

        integration = OpenTelemetryIntegration(
            enabled=False,  # Disable to avoid actual OTEL init
            metrics_callback=metrics_callback,
        )

        # Simulate metric tracking
        if integration._metrics_callback:
            integration._metrics_callback("test_metric", 42.0)

        assert len(callback_calls) == 1
        assert callback_calls[0] == ("test_metric", 42.0)

    def test_export_span_when_disabled(self):
        """Export does nothing when disabled."""
        integration = OpenTelemetryIntegration(enabled=False)
        # Should not raise
        integration.export_span_to_otel(
            span_name="test",
            start_time=1000.0,
            end_time=1001.0,
        )
