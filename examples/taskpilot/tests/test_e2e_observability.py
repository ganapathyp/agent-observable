"""End-to-end test for observability stack."""
import asyncio
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("⚠️  Warning: 'requests' not installed. Some tests will be skipped.")
    print("   Install with: pip install requests")
    print("")

# Test results
PASSED = 0
FAILED = 0
WARNINGS = 0

def test_check(name: str, condition: bool, warning: bool = False) -> bool:
    """Run a test check."""
    global PASSED, FAILED, WARNINGS
    
    if condition:
        print(f"  ✅ {name}")
        PASSED += 1
        return True
    else:
        if warning:
            print(f"  ⚠️  {name} (warning)")
            WARNINGS += 1
            return True
        else:
            print(f"  ❌ {name}")
            FAILED += 1
            return False

def check_service_endpoint(name: str, url: str, timeout: int = 5) -> bool:
    """Check if a service endpoint is accessible."""
    if not HAS_REQUESTS:
        # Fallback to curl
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout.strip() == "200"
        except Exception:
            return False
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False

def check_docker_service(name: str) -> bool:
    """Check if a Docker service is running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return name in result.stdout
    except Exception:
        return False

async def test_metrics_server():
    """Test metrics server."""
    print("\n📊 Testing Metrics Server")
    print("-" * 40)
    
    # Check if running
    running = check_service_endpoint("Metrics server", "http://localhost:8000/health")
    test_check("Metrics server running", running, warning=True)
    
    if running:
        # Check metrics endpoint
        try:
            if HAS_REQUESTS:
                response = requests.get("http://localhost:8000/metrics", timeout=5)
                has_metrics = "TYPE" in response.text or len(response.text) > 0
            else:
                result = subprocess.run(
                    ["curl", "-s", "http://localhost:8000/metrics"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                has_metrics = "TYPE" in result.stdout or len(result.stdout) > 0
            test_check("Metrics endpoint returns data", has_metrics)
            
            # Check health endpoint
            if HAS_REQUESTS:
                response = requests.get("http://localhost:8000/health", timeout=5)
                has_status = "status" in response.json()
            else:
                result = subprocess.run(
                    ["curl", "-s", "http://localhost:8000/health"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                has_status = "status" in result.stdout
            test_check("Health endpoint returns status", has_status)
        except Exception as e:
            test_check(f"Metrics endpoint accessible: {e}", False)
    else:
        print("  ⚠️  Metrics server not running. Start with: python metrics_server.py")

async def test_docker_services():
    """Test Docker services."""
    print("\n🐳 Testing Docker Services")
    print("-" * 40)
    
    services = [
        "taskpilot-prometheus",
        "taskpilot-grafana",
        "taskpilot-jaeger",
        "taskpilot-elasticsearch",
        "taskpilot-kibana",
        "taskpilot-otel-collector",
    ]
    
    for service in services:
        running = check_docker_service(service)
        test_check(f"{service} running", running)

async def test_service_endpoints():
    """Test service endpoints."""
    print("\n🌐 Testing Service Endpoints")
    print("-" * 40)
    
    endpoints = [
        ("Prometheus", "http://localhost:9090/-/healthy"),
        ("Grafana", "http://localhost:3000/api/health"),
        ("Jaeger", "http://localhost:16686"),
        ("Kibana", "http://localhost:5601/api/status"),
        ("Elasticsearch", "http://localhost:9200"),
    ]
    
    for name, url in endpoints:
        accessible = check_service_endpoint(name, url)
        test_check(f"{name} endpoint accessible", accessible)

async def test_prometheus_integration():
    """Test Prometheus integration."""
    print("\n📈 Testing Prometheus Integration")
    print("-" * 40)
    
    # Check if Prometheus can scrape
    try:
        if HAS_REQUESTS:
            response = requests.get("http://localhost:9090/api/v1/targets", timeout=5)
            if response.status_code == 200:
                data = response.json()
                targets = data.get("data", {}).get("activeTargets", [])
                if targets:
                    up_targets = [t for t in targets if t.get("health") == "up"]
                    test_check(f"Prometheus targets: {len(up_targets)}/{len(targets)} up", len(up_targets) > 0)
                else:
                    test_check("Prometheus has targets configured", False, warning=True)
        else:
            # Fallback: just check if Prometheus is accessible
            result = subprocess.run(
                ["curl", "-s", "http://localhost:9090/api/v1/targets"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                test_check("Prometheus API accessible", True, warning=True)
            else:
                test_check("Prometheus API accessible", False, warning=True)
    except Exception as e:
        test_check(f"Prometheus API accessible: {e}", False, warning=True)

async def test_file_system():
    """Test file system setup."""
    print("\n📁 Testing File System")
    print("-" * 40)
    
    required_files = [
        "docker-compose.observability.yml",
        "main.py",  # Metrics server is integrated in main.py
        "scripts/observability/start-observability.sh",
        "observability/prometheus/prometheus.yml",
        "observability/otel/collector-config.yml",
        "observability/filebeat/filebeat.yml",
        "observability/grafana/provisioning/datasources/prometheus.yml",
        "observability/grafana/provisioning/dashboards/dashboard.yml",
    ]
    
    for file_path in required_files:
        exists = Path(file_path).exists()
        test_check(f"{file_path} exists", exists)

async def test_data_files():
    """Test data files."""
    print("\n🔍 Testing Data Files")
    print("-" * 40)
    
    # Check traces
    traces_file = Path("traces.jsonl")
    if traces_file.exists():
        try:
            count = sum(1 for _ in traces_file.open())
            test_check(f"traces.jsonl exists ({count} entries)", count > 0, warning=True)
        except Exception:
            test_check("traces.jsonl readable", False, warning=True)
    else:
        print("  ⚠️  traces.jsonl not found (run application to generate)")
        WARNINGS += 1
    
    # Check decision logs
    decision_logs_file = Path("decision_logs.jsonl")
    if decision_logs_file.exists():
        try:
            count = sum(1 for _ in decision_logs_file.open())
            test_check(f"decision_logs.jsonl exists ({count} entries)", count > 0, warning=True)
        except Exception:
            test_check("decision_logs.jsonl readable", False, warning=True)
    else:
        print("  ⚠️  decision_logs.jsonl not found (run application to generate)")
        WARNINGS += 1

async def test_application_integration():
    """Test application can generate observability data."""
    print("\n🔄 Testing Application Integration")
    print("-" * 40)
    
    # Check if we can import observability modules
    try:
        from taskpilot.core.observability import (
            get_metrics_collector,
            get_health_checker,
            get_tracer
        )
        test_check("Observability modules importable", True)
        
        # Test metrics collector
        import time
        metrics = get_metrics_collector()
        unique_counter = f"test.counter.{int(time.time() * 1000)}"
        metrics.increment_counter(unique_counter)
        value = metrics.get_counter(unique_counter)
        test_check("Metrics collector functional", value == 1.0)
        
        # Test health checker
        health_checker = get_health_checker()
        status = health_checker.check_health()
        test_check("Health checker functional", status is not None)
        
        # Test tracer
        tracer = get_tracer()
        test_check("Tracer accessible", tracer is not None)
        
    except Exception as e:
        test_check(f"Observability integration: {e}", False)

async def main():
    """Run all E2E tests."""
    print("🧪 End-to-End Observability Test")
    print("=" * 50)
    print("")
    
    # Run all tests
    await test_file_system()
    await test_docker_services()
    await test_service_endpoints()
    await test_metrics_server()
    await test_prometheus_integration()
    await test_data_files()
    await test_application_integration()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    print(f"  ✅ Passed: {PASSED}")
    print(f"  ❌ Failed: {FAILED}")
    print(f"  ⚠️  Warnings: {WARNINGS}")
    print("")
    
    if FAILED == 0:
        print("🎉 All critical tests passed!")
        print("")
        print("✅ Your observability stack is ready!")
        print("")
        print("Next steps:")
        print("  1. Start metrics server: python metrics_server.py")
        print("  2. Run application: python main.py")
        print("  3. View dashboards:")
        print("     • Grafana: http://localhost:3000")
        print("     • Prometheus: http://localhost:9090")
        print("     • Jaeger: http://localhost:16686")
        print("     • Kibana: http://localhost:5601")
        return 0
    else:
        print("❌ Some tests failed")
        print("")
        print("Troubleshooting:")
        print("  1. Start observability stack: ./start-observability.sh")
        print("  2. Install dependencies: pip install -r requirements.txt")
        print("  3. Check Docker is running: docker ps")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
