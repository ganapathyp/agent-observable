"""Tests for cost report endpoint."""
import pytest
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from fastapi.testclient import TestClient
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestCostReportEndpoint:
    """Test /cost-report endpoint."""
    
    def test_cost_report_text_format(self):
        """Test cost report in text format."""
        import main
        from taskpilot.core.observable import get_metrics
        
        app = main.create_app()
        if app is None:
            pytest.skip("FastAPI not available")
        
        client = TestClient(app)
        response = client.get("/cost-report?format=text")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "LLM Cost Report" in response.text
        assert "Total Cost" in response.text
    
    def test_cost_report_json_format(self):
        """Test cost report in JSON format."""
        import main
        
        app = main.create_app()
        if app is None:
            pytest.skip("FastAPI not available")
        
        client = TestClient(app)
        response = client.get("/cost-report?format=json")
        
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        data = response.json()
        assert "total_cost_usd" in data
        assert "cost_by_agent" in data
        assert "cost_by_model" in data
        assert "tokens" in data
    
    def test_cost_report_csv_format(self):
        """Test cost report in CSV format."""
        import main
        
        app = main.create_app()
        if app is None:
            pytest.skip("FastAPI not available")
        
        client = TestClient(app)
        response = client.get("/cost-report?format=csv")
        
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "Metric,Value" in response.text
    
    def test_cost_report_default_format(self):
        """Test cost report with default format (text)."""
        import main
        
        app = main.create_app()
        if app is None:
            pytest.skip("FastAPI not available")
        
        client = TestClient(app)
        response = client.get("/cost-report")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "LLM Cost Report" in response.text
