"""Unit tests for OpenTelemetry integration."""
import pytest
from unittest.mock import patch, MagicMock
from taskpilot.core.otel_integration import (
    initialize_opentelemetry,
    get_otel_tracer,
    export_span_to_otel
)


class TestInitializeOpenTelemetry:
    """Test OpenTelemetry initialization."""
    
    def test_initialize_opentelemetry_disabled(self):
        """Test initialization when disabled."""
        result = initialize_opentelemetry(enabled=False)
        
        assert result is False
        assert get_otel_tracer() is None
    
    @patch('taskpilot.core.otel_integration.TracerProvider')
    @patch('taskpilot.core.otel_integration.OTLPSpanExporter')
    @patch('taskpilot.core.otel_integration.BatchSpanProcessor')
    @patch('taskpilot.core.otel_integration.Resource')
    @patch('taskpilot.core.otel_integration.trace')
    def test_initialize_opentelemetry_success(self, mock_trace, mock_resource, 
                                               mock_span_processor, mock_exporter, 
                                               mock_tracer_provider):
        """Test successful initialization."""
        # Mock the OpenTelemetry components
        mock_provider = MagicMock()
        mock_tracer_provider.return_value = mock_provider
        mock_trace.get_tracer.return_value = MagicMock()
        mock_trace.set_tracer_provider = MagicMock()
        
        result = initialize_opentelemetry(
            service_name="test-service",
            otlp_endpoint="http://localhost:4317",
            enabled=True
        )
        
        assert result is True
        mock_tracer_provider.assert_called_once()
        mock_trace.set_tracer_provider.assert_called_once()
    
    @patch('taskpilot.core.otel_integration.TracerProvider')
    def test_initialize_opentelemetry_failure(self, mock_tracer_provider):
        """Test initialization failure handling."""
        # Make initialization fail
        mock_tracer_provider.side_effect = Exception("Connection failed")
        
        result = initialize_opentelemetry(enabled=True)
        
        # Should return False but not raise exception
        assert result is False
    
    def test_initialize_opentelemetry_defaults(self):
        """Test initialization with default parameters."""
        with patch('taskpilot.core.otel_integration.TracerProvider') as mock_provider:
            mock_provider.return_value = MagicMock()
            with patch('taskpilot.core.otel_integration.trace') as mock_trace:
                mock_trace.get_tracer.return_value = MagicMock()
                mock_trace.set_tracer_provider = MagicMock()
                
                result = initialize_opentelemetry()
                
                # Should use defaults
                assert result is True


class TestGetOtelTracer:
    """Test getting OpenTelemetry tracer."""
    
    def test_get_otel_tracer_not_initialized(self):
        """Test getting tracer when not initialized."""
        # Reset global state
        import taskpilot.core.otel_integration
        taskpilot.core.otel_integration._otel_tracer = None
        
        tracer = get_otel_tracer()
        
        assert tracer is None
    
    @patch('taskpilot.core.otel_integration._otel_tracer')
    def test_get_otel_tracer_initialized(self, mock_tracer):
        """Test getting tracer when initialized."""
        mock_tracer_instance = MagicMock()
        mock_tracer = mock_tracer_instance
        
        # Set the global tracer
        import taskpilot.core.otel_integration
        taskpilot.core.otel_integration._otel_tracer = mock_tracer_instance
        
        tracer = get_otel_tracer()
        
        assert tracer is not None
        assert tracer == mock_tracer_instance


class TestExportSpanToOtel:
    """Test exporting spans to OpenTelemetry."""
    
    def test_export_span_to_otel_no_tracer(self):
        """Test export when tracer is not available."""
        # Ensure tracer is None
        import taskpilot.core.otel_integration
        taskpilot.core.otel_integration._otel_tracer = None
        
        # Should not raise exception
        export_span_to_otel(
            span_name="test_span",
            start_time=1000.0,
            end_time=1001.0
        )
    
    @patch('taskpilot.core.otel_integration.get_otel_tracer')
    def test_export_span_to_otel_with_tracer(self, mock_get_tracer):
        """Test export with tracer available."""
        # Mock tracer
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_span.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer
        
        # Export span
        export_span_to_otel(
            span_name="test_span",
            start_time=1000.0,
            end_time=1001.0,
            request_id="req-123",
            parent_span_id="parent-456",
            tags={"key": "value"},
            logs=[{"message": "test log", "timestamp": 1000.5}]
        )
        
        # Verify span was created and configured
        mock_tracer.start_span.assert_called_once_with("test_span")
        assert mock_span.set_attribute.called
        assert mock_span.add_event.called
        assert mock_span.end.called
    
    @patch('taskpilot.core.otel_integration.get_otel_tracer')
    def test_export_span_to_otel_minimal(self, mock_get_tracer):
        """Test export with minimal parameters."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_span.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer
        
        export_span_to_otel(
            span_name="minimal_span",
            start_time=1000.0,
            end_time=1001.0
        )
        
        mock_tracer.start_span.assert_called_once_with("minimal_span")
        mock_span.end.assert_called_once()
    
    @patch('taskpilot.core.otel_integration.get_otel_tracer')
    def test_export_span_to_otel_no_end_time(self, mock_get_tracer):
        """Test export without end time."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_span.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer
        
        export_span_to_otel(
            span_name="no_end_span",
            start_time=1000.0,
            end_time=None
        )
        
        mock_span.end.assert_called_once()
    
    @patch('taskpilot.core.otel_integration.get_otel_tracer')
    def test_export_span_to_otel_long_values(self, mock_get_tracer):
        """Test export with long values (should be truncated)."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_span.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer
        
        long_value = "x" * 1000
        export_span_to_otel(
            span_name="long_value_span",
            start_time=1000.0,
            end_time=1001.0,
            tags={"long_key": long_value}
        )
        
        # Verify truncation happened
        calls = mock_span.set_attribute.call_args_list
        for call in calls:
            args, kwargs = call
            if len(args) >= 2:
                value = args[1]
                if isinstance(value, str) and len(value) > 500:
                    assert value.endswith("...")
    
    @patch('taskpilot.core.otel_integration.get_otel_tracer')
    def test_export_span_to_otel_with_logs_fields(self, mock_get_tracer):
        """Test export with logs in fields format."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_span.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer
        
        logs = [{
            "fields": {
                "message": "test message",
                "output": "test output",
                "other": "value"
            },
            "timestamp": 1000.5
        }]
        
        export_span_to_otel(
            span_name="fields_span",
            start_time=1000.0,
            end_time=1001.0,
            logs=logs
        )
        
        # Verify event was added
        assert mock_span.add_event.called
    
    @patch('taskpilot.core.otel_integration.get_otel_tracer')
    def test_export_span_to_otel_exception_handling(self, mock_get_tracer):
        """Test that exceptions during export are handled gracefully."""
        mock_tracer = MagicMock()
        mock_tracer.start_span.side_effect = Exception("Export failed")
        mock_get_tracer.return_value = mock_tracer
        
        # Should not raise exception
        export_span_to_otel(
            span_name="error_span",
            start_time=1000.0,
            end_time=1001.0
        )
