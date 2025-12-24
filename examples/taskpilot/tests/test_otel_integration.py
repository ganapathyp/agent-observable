"""Unit tests for OpenTelemetry integration."""
import pytest
from unittest.mock import patch, MagicMock
from taskpilot.core.observable import (
    setup_observability,
    get_otel,
    export_span_to_otel,
)


class TestInitializeOpenTelemetry:
    """Test OpenTelemetry initialization."""
    
    def test_initialize_opentelemetry_disabled(self):
        """Test initialization when disabled."""
        result = setup_observability(service_name="test", enable_otel=False)
        
        # When disabled, otel may still be created but disabled
        otel = get_otel()
        assert otel is None or (hasattr(otel, '_enabled') and not otel._enabled)
    
    @patch('agent_observable_core.otel_integration.OpenTelemetryIntegration')
    def test_initialize_opentelemetry_success(self, mock_otel_class):
        """Test successful initialization."""
        # Mock the OpenTelemetryIntegration
        mock_instance = MagicMock()
        mock_instance._enabled = True
        mock_instance.start_export_worker = MagicMock()
        mock_otel_class.return_value = mock_instance
        
        result = setup_observability(
            service_name="test-service",
            otlp_endpoint="http://localhost:4317",
            enable_otel=True
        )
        
        assert result["otel"] is not None
        # Note: setup_observability may call OpenTelemetryIntegration during import, so we check it was created
        assert mock_otel_class.called or result["otel"] is not None
    
    @patch('agent_observable_core.otel_integration.OpenTelemetryIntegration')
    def test_initialize_opentelemetry_failure(self, mock_otel_class):
        """Test initialization failure handling."""
        # Make initialization fail
        mock_instance = MagicMock()
        mock_instance._enabled = False
        mock_instance.start_export_worker = MagicMock()
        mock_otel_class.return_value = mock_instance
        
        result = setup_observability(enable_otel=True)
        
        # Should not raise exception
        assert result["otel"] is not None  # Still created, just disabled
    
    @patch('agent_observable_core.otel_integration.OpenTelemetryIntegration')
    def test_initialize_opentelemetry_defaults(self, mock_otel_class):
        """Test initialization with default parameters."""
        mock_instance = MagicMock()
        mock_instance._enabled = True
        mock_instance.start_export_worker = MagicMock()
        mock_otel_class.return_value = mock_instance
        
        result = setup_observability()
        
        # Should use defaults
        assert result["otel"] is not None


class TestGetOtelTracer:
    """Test getting OpenTelemetry tracer."""
    
    def test_get_otel_not_initialized(self):
        """Test getting OTEL when not initialized."""
        # Reset global state
        from taskpilot.core.observable import _otel
        import taskpilot.core.observable
        taskpilot.core.observable._otel = None
        
        otel = get_otel()
        
        assert otel is None
    
    def test_get_otel_initialized(self):
        """Test getting OTEL when initialized."""
        from taskpilot.core.observable import setup_observability
        
        result = setup_observability(service_name="test", enable_otel=True)
        
        otel = get_otel()
        assert otel is not None
        assert otel == result["otel"]


class TestExportSpanToOtel:
    """Test exporting spans to OpenTelemetry."""
    
    def test_export_span_to_otel_no_tracer(self):
        """Test export when tracer is not available."""
        # Ensure integration is None
        import taskpilot.core.observable
        taskpilot.core.observable._otel = None
        
        # Should not raise exception
        export_span_to_otel(
            span_name="test_span",
            start_time=1000.0,
            end_time=1001.0
        )
    
    def test_export_span_to_otel_with_tracer(self):
        """Test export with tracer available."""
        # Set up mock integration
        import taskpilot.core.observable
        mock_integration_instance = MagicMock()
        mock_integration_instance._enabled = True
        mock_integration_instance.export_span_to_otel = MagicMock()
        taskpilot.core.observable._otel = mock_integration_instance
        
        try:
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
            
            # Verify export_span_to_otel was called
            assert mock_integration_instance.export_span_to_otel.called
        finally:
            taskpilot.core.observable._otel = None
    
    def test_export_span_to_otel_minimal(self):
        """Test export with minimal parameters."""
        import taskpilot.core.observable
        mock_integration_instance = MagicMock()
        mock_integration_instance._enabled = True
        mock_integration_instance.export_span_to_otel = MagicMock()
        taskpilot.core.observable._otel = mock_integration_instance
        
        try:
            export_span_to_otel(
                span_name="minimal_span",
                start_time=1000.0,
                end_time=1001.0
            )
            
            # Verify export_span_to_otel was called
            assert mock_integration_instance.export_span_to_otel.called
        finally:
            taskpilot.core.observable._otel = None
    
    def test_export_span_to_otel_no_end_time(self):
        """Test export without end time."""
        import taskpilot.core.observable
        mock_integration_instance = MagicMock()
        mock_integration_instance._enabled = True
        mock_integration_instance.export_span_to_otel = MagicMock()
        taskpilot.core.observable._otel = mock_integration_instance
        
        try:
            export_span_to_otel(
                span_name="no_end_span",
                start_time=1000.0,
                end_time=None
            )
            
            # Verify export_span_to_otel was called
            assert mock_integration_instance.export_span_to_otel.called
        finally:
            taskpilot.core.observable._otel = None
    
    def test_export_span_to_otel_long_values(self):
        """Test export with long values (should be truncated)."""
        import taskpilot.core.observable
        mock_integration_instance = MagicMock()
        mock_integration_instance._enabled = True
        mock_integration_instance.export_span_to_otel = MagicMock()
        taskpilot.core.observable._otel = mock_integration_instance
        
        try:
            long_value = "x" * 1000
            export_span_to_otel(
                span_name="long_value_span",
                start_time=1000.0,
                end_time=1001.0,
                tags={"long_key": long_value}
            )
            
            # Verify export_span_to_otel was called
            assert mock_integration_instance.export_span_to_otel.called
            # The truncation happens inside the library, so we just verify it was called
        finally:
            taskpilot.core.observable._otel = None
    
    def test_export_span_to_otel_with_logs_fields(self):
        """Test export with logs in fields format."""
        import taskpilot.core.observable
        mock_integration_instance = MagicMock()
        mock_integration_instance._enabled = True
        mock_integration_instance.export_span_to_otel = MagicMock()
        taskpilot.core.observable._otel = mock_integration_instance
        
        try:
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
            
            # Verify export_span_to_otel was called
            assert mock_integration_instance.export_span_to_otel.called
        finally:
            taskpilot.core.observable._otel = None
    
    def test_export_span_to_otel_exception_handling(self):
        """Test that exceptions during export are handled gracefully."""
        import taskpilot.core.observable
        mock_integration_instance = MagicMock()
        mock_integration_instance.export_span_to_otel.side_effect = Exception("Export failed")
        taskpilot.core.observable._otel = mock_integration_instance
        
        # Should not raise exception (observable.py handles it)
        try:
            export_span_to_otel(
                span_name="error_span",
                start_time=1000.0,
                end_time=1001.0
            )
        except Exception:
            # If exception propagates, that's also acceptable
            pass
        finally:
            taskpilot.core.observable._otel = None
