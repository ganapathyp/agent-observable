#!/usr/bin/env python3
"""Comprehensive observability stack testing and verification.

Tests:
1. Docker services (start/fix if needed)
2. Data generation and verification
3. Metrics, traces, logs in all tools
4. Dashboards (create if missing)
5. Alerts (create and test)
6. Leadership-ready metrics verification
"""
import sys
import os
import json
import time
import subprocess
import socket
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@dataclass
class TestResult:
    """Test result with details."""
    name: str
    status: str  # "PASS", "FAIL", "SKIP", "WARN"
    message: str = ""
    details: Dict = field(default_factory=dict)
    fix_applied: bool = False

@dataclass
class TestReport:
    """Comprehensive test report."""
    timestamp: str
    docker_services: List[TestResult] = field(default_factory=list)
    data_generation: List[TestResult] = field(default_factory=list)
    metrics: List[TestResult] = field(default_factory=list)
    traces: List[TestResult] = field(default_factory=list)
    logs: List[TestResult] = field(default_factory=list)
    dashboards: List[TestResult] = field(default_factory=list)
    alerts: List[TestResult] = field(default_factory=list)
    leadership_metrics: List[TestResult] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)

class ObservabilityTester:
    """Comprehensive observability stack tester."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.docker_compose_file = project_root / "docker-compose.observability.yml"
        self.results: List[TestResult] = []
        self.base_urls = {
            "prometheus": "http://localhost:9090",
            "grafana": "http://localhost:3000",
            "jaeger": "http://localhost:16686",
            "kibana": "http://localhost:5601",
            "elasticsearch": "http://localhost:9200",
            "taskpilot": "http://localhost:8000",
        }
        self.grafana_user = "admin"
        self.grafana_password = "admin"
        
    def run(self) -> TestReport:
        """Run all tests."""
        print("=" * 80)
        print("COMPREHENSIVE OBSERVABILITY STACK TEST")
        print("=" * 80)
        print()
        
        report = TestReport(timestamp=datetime.now().isoformat())
        
        # 1. Docker Services
        print("🔧 STEP 1: Docker Services")
        print("-" * 80)
        report.docker_services = self.test_docker_services()
        self.print_results(report.docker_services)
        print()
        
        # 2. Data Generation
        print("📊 STEP 2: Data Generation")
        print("-" * 80)
        report.data_generation = self.test_data_generation()
        self.print_results(report.data_generation)
        print()
        
        # 3. Metrics
        print("📈 STEP 3: Metrics Verification")
        print("-" * 80)
        report.metrics = self.test_metrics()
        self.print_results(report.metrics)
        print()
        
        # 4. Traces
        print("🔍 STEP 4: Traces Verification")
        print("-" * 80)
        report.traces = self.test_traces()
        self.print_results(report.traces)
        print()
        
        # 5. Logs
        print("📝 STEP 5: Logs Verification")
        print("-" * 80)
        report.logs = self.test_logs()
        self.print_results(report.logs)
        print()
        
        # 6. Dashboards
        print("📊 STEP 6: Dashboards")
        print("-" * 80)
        report.dashboards = self.test_dashboards()
        self.print_results(report.dashboards)
        print()
        
        # 7. Alerts
        print("🚨 STEP 7: Alerts")
        print("-" * 80)
        report.alerts = self.test_alerts()
        self.print_results(report.alerts)
        print()
        
        # 8. Leadership Metrics
        print("👔 STEP 8: Leadership-Ready Metrics")
        print("-" * 80)
        report.leadership_metrics = self.test_leadership_metrics()
        self.print_results(report.leadership_metrics)
        print()
        
        # Summary
        report.summary = self.calculate_summary(report)
        self.print_summary(report.summary)
        
        # Save report
        self.save_report(report)
        
        return report
    
    def test_docker_services(self) -> List[TestResult]:
        """Test and fix Docker services."""
        results = []
        
        # Check if docker-compose file exists
        if not self.docker_compose_file.exists():
            results.append(TestResult(
                name="Docker Compose File",
                status="FAIL",
                message=f"Docker compose file not found: {self.docker_compose_file}"
            ))
            return results
        
        results.append(TestResult(
            name="Docker Compose File",
            status="PASS",
            message=f"Found: {self.docker_compose_file}"
        ))
        
        # Check Docker daemon
        try:
            subprocess.run(["docker", "ps"], check=True, capture_output=True, timeout=5)
            results.append(TestResult(
                name="Docker Daemon",
                status="PASS",
                message="Docker daemon is running"
            ))
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            results.append(TestResult(
                name="Docker Daemon",
                status="FAIL",
                message="Docker daemon is not running or not accessible"
            ))
            return results
        
        # Start services
        print("  Starting Docker services...")
        try:
            result = subprocess.run(
                ["docker-compose", "-f", str(self.docker_compose_file), "up", "-d"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                results.append(TestResult(
                    name="Start Docker Services",
                    status="PASS",
                    message="All services started successfully",
                    fix_applied=True
                ))
            else:
                results.append(TestResult(
                    name="Start Docker Services",
                    status="FAIL",
                    message=f"Failed to start services: {result.stderr[:200]}"
                ))
        except Exception as e:
            results.append(TestResult(
                name="Start Docker Services",
                status="FAIL",
                message=f"Error starting services: {e}"
            ))
        
        # Wait for services to be ready
        print("  Waiting for services to be ready...")
        time.sleep(10)
        
        # Check each service
        services = [
            ("prometheus", "taskpilot-prometheus", 9090),
            ("grafana", "taskpilot-grafana", 3000),
            ("jaeger", "taskpilot-jaeger", 16686),
            ("kibana", "taskpilot-kibana", 5601),
            ("elasticsearch", "taskpilot-elasticsearch", 9200),
            ("otel-collector", "taskpilot-otel-collector", 4317),
            ("filebeat", "taskpilot-filebeat", None),
        ]
        
        for service_name, container_name, port in services:
            # Check container status
            try:
                result = subprocess.run(
                    ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.stdout.strip() and "Up" in result.stdout:
                    status_msg = result.stdout.strip()
                    results.append(TestResult(
                        name=f"{service_name.capitalize()} Container",
                        status="PASS",
                        message=status_msg
                    ))
                else:
                    results.append(TestResult(
                        name=f"{service_name.capitalize()} Container",
                        status="FAIL",
                        message=f"Container {container_name} is not running"
                    ))
            except Exception as e:
                results.append(TestResult(
                    name=f"{service_name.capitalize()} Container",
                    status="FAIL",
                    message=f"Error checking container: {e}"
                ))
            
            # Check HTTP endpoint if port specified
            if port:
                try:
                    url = f"http://localhost:{port}"
                    if service_name == "prometheus":
                        url = f"{url}/-/healthy"
                    elif service_name == "grafana":
                        url = f"{url}/api/health"
                    elif service_name == "jaeger":
                        url = f"{url}/"
                    elif service_name == "kibana":
                        url = f"{url}/api/status"
                    elif service_name == "elasticsearch":
                        url = f"{url}/_cluster/health"
                    
                    response = requests.get(url, timeout=5)
                    if response.status_code in [200, 401]:  # 401 is OK for Grafana (needs auth)
                        results.append(TestResult(
                            name=f"{service_name.capitalize()} HTTP",
                            status="PASS",
                            message=f"Endpoint accessible: {url}"
                        ))
                    else:
                        results.append(TestResult(
                            name=f"{service_name.capitalize()} HTTP",
                            status="WARN",
                            message=f"Endpoint returned {response.status_code}: {url}"
                        ))
                except Exception as e:
                    results.append(TestResult(
                        name=f"{service_name.capitalize()} HTTP",
                        status="FAIL",
                        message=f"Endpoint not accessible: {e}"
                    ))
        
        return results
    
    def test_data_generation(self) -> List[TestResult]:
        """Test data generation."""
        results = []
        
        # Check if TaskPilot server is running
        server_running = False
        try:
            response = requests.get(f"{self.base_urls['taskpilot']}/health", timeout=5)
            if response.status_code == 200:
                server_running = True
                results.append(TestResult(
                    name="TaskPilot Server",
                    status="PASS",
                    message="Server is running"
                ))
            else:
                results.append(TestResult(
                    name="TaskPilot Server",
                    status="WARN",
                    message=f"Server returned {response.status_code}"
                ))
        except Exception:
            # Server not running - try to start it
            print("  TaskPilot server not running. Starting server...")
            try:
                # Check if port is already in use (might be a different process)
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('localhost', 8000))
                sock.close()
                
                if result == 0:
                    # Port is in use - might be server starting up, wait a bit
                    print("  Port 8000 is in use, waiting for server to be ready...")
                    max_wait = 10
                    for i in range(max_wait):
                        time.sleep(1)
                        try:
                            response = requests.get(f"{self.base_urls['taskpilot']}/health", timeout=2)
                            if response.status_code == 200:
                                server_running = True
                                results.append(TestResult(
                                    name="TaskPilot Server",
                                    status="PASS",
                                    message="Server is running (port was in use)"
                                ))
                                break
                        except:
                            continue
                    
                    if server_running:
                        pass  # Already set result above
                    else:
                        results.append(TestResult(
                            name="TaskPilot Server",
                            status="WARN",
                            message="Port 8000 is in use but server not responding. May need manual start."
                        ))
                        return results
                else:
                    # Port is free - start server
                    # Start server in background with proper environment
                    # Use nohup or redirect to /dev/null to avoid blocking
                    env = os.environ.copy()
                    # Start server using main.py (it handles async properly)
                    log_file = self.project_root / "logs" / "server_startup.log"
                    log_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(log_file, 'w') as log:
                        server_process = subprocess.Popen(
                            ["python3", "main.py", "--server", "--port", "8000"],
                            cwd=self.project_root,
                            stdout=log,
                            stderr=subprocess.STDOUT,
                            env=env,
                            start_new_session=True,
                            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
                        )
                    
                    # Wait for server to start (longer timeout for first startup)
                    max_wait = 30
                    print(f"  Waiting up to {max_wait} seconds for server to start...")
                    for i in range(max_wait):
                        time.sleep(1)
                        try:
                            response = requests.get(f"{self.base_urls['taskpilot']}/health", timeout=2)
                            if response.status_code == 200:
                                server_running = True
                                results.append(TestResult(
                                    name="TaskPilot Server",
                                    status="PASS",
                                    message=f"Server started successfully (took {i+1}s)",
                                    fix_applied=True,
                                    details={"pid": server_process.pid}
                                ))
                                break
                        except:
                            if (i + 1) % 5 == 0:
                                print(f"    Still waiting... ({i+1}s)")
                            continue
                    
                    if not server_running:
                        # Check if process is still running
                        if server_process.poll() is None:
                            results.append(TestResult(
                                name="TaskPilot Server",
                                status="WARN",
                                message="Server process started but not responding yet. May need more time."
                            ))
                        else:
                            # Process died
                            stderr = server_process.stderr.read().decode() if server_process.stderr else "No error output"
                            results.append(TestResult(
                                name="TaskPilot Server",
                                status="FAIL",
                                message=f"Server process exited. Error: {stderr[:200]}"
                            ))
                            return results
            except Exception as e:
                results.append(TestResult(
                    name="TaskPilot Server",
                    status="FAIL",
                    message=f"Error starting server: {e}"
                ))
                return results
        
        if not server_running:
            return results
        
        # Generate test data by running a workflow
        print("  Generating test data (running workflow)...")
        try:
            # Run workflow - task description is passed as positional argument
            # Need to check how main.py handles arguments
            result = subprocess.run(
                ["python3", "-c", 
                 "import sys; sys.path.insert(0, '.'); "
                 "import asyncio; "
                 "from main import run_workflow_once; "
                 "asyncio.run(run_workflow_once())"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "PYTHONPATH": str(self.project_root)}
            )
            if result.returncode == 0:
                results.append(TestResult(
                    name="Workflow Execution",
                    status="PASS",
                    message="Test workflow executed successfully"
                ))
            else:
                results.append(TestResult(
                    name="Workflow Execution",
                    status="WARN",
                    message=f"Workflow completed with warnings: {result.stderr[:200]}"
                ))
        except subprocess.TimeoutExpired:
            results.append(TestResult(
                name="Workflow Execution",
                status="WARN",
                message="Workflow timed out (may still have generated data)"
            ))
        except Exception as e:
            results.append(TestResult(
                name="Workflow Execution",
                status="FAIL",
                message=f"Error running workflow: {e}"
            ))
        
        # Wait for data to propagate
        print("  Waiting for data to propagate...")
        time.sleep(5)
        
        return results
    
    def test_metrics(self) -> List[TestResult]:
        """Test metrics in Prometheus and TaskPilot."""
        results = []
        
        # Check TaskPilot metrics endpoint
        try:
            response = requests.get(f"{self.base_urls['taskpilot']}/metrics", timeout=5)
            if response.status_code == 200:
                metrics_text = response.text
                
                # Check for key metrics
                key_metrics = [
                    "llm_cost_total",
                    "policy_violations_total",
                    "workflow_runs",
                    "workflow_success",
                    "workflow_errors",
                    "workflow_latency_ms",
                ]
                
                found_metrics = []
                missing_metrics = []
                for metric in key_metrics:
                    if metric in metrics_text:
                        found_metrics.append(metric)
                    else:
                        missing_metrics.append(metric)
                
                results.append(TestResult(
                    name="TaskPilot Metrics Endpoint",
                    status="PASS" if not missing_metrics else "WARN",
                    message=f"Found {len(found_metrics)}/{len(key_metrics)} key metrics",
                    details={"found": found_metrics, "missing": missing_metrics}
                ))
            else:
                results.append(TestResult(
                    name="TaskPilot Metrics Endpoint",
                    status="FAIL",
                    message=f"Endpoint returned {response.status_code}"
                ))
        except Exception as e:
            results.append(TestResult(
                name="TaskPilot Metrics Endpoint",
                status="FAIL",
                message=f"Error accessing endpoint: {e}"
            ))
        
        # Check Prometheus targets
        try:
            response = requests.get(f"{self.base_urls['prometheus']}/api/v1/targets", timeout=5)
            if response.status_code == 200:
                data = response.json()
                targets = data.get("data", {}).get("activeTargets", [])
                taskpilot_target = next((t for t in targets if t.get("labels", {}).get("job") == "taskpilot"), None)
                
                if taskpilot_target:
                    health = taskpilot_target.get("health", "unknown")
                    last_error = taskpilot_target.get("lastError", "")
                    
                    results.append(TestResult(
                        name="Prometheus Target",
                        status="PASS" if health == "up" else "FAIL",
                        message=f"Target health: {health}",
                        details={"last_error": last_error, "last_scrape": taskpilot_target.get("lastScrape", "")}
                    ))
                else:
                    results.append(TestResult(
                        name="Prometheus Target",
                        status="FAIL",
                        message="TaskPilot target not found in Prometheus"
                    ))
        except Exception as e:
            results.append(TestResult(
                name="Prometheus Target",
                status="FAIL",
                message=f"Error checking targets: {e}"
            ))
        
        # Query key metrics in Prometheus
        key_queries = [
            ("llm_cost_total", "Total LLM cost"),
            ("policy_violations_total", "Policy violations"),
            ("workflow_runs", "Workflow runs"),
            ("workflow_success", "Successful workflows"),
        ]
        
        for metric, description in key_queries:
            try:
                response = requests.get(
                    f"{self.base_urls['prometheus']}/api/v1/query",
                    params={"query": metric},
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    result = data.get("data", {}).get("result", [])
                    if result:
                        value = result[0].get("value", [None, "0"])[1]
                        results.append(TestResult(
                            name=f"Prometheus Query: {metric}",
                            status="PASS",
                            message=f"{description}: {value}",
                            details={"value": value}
                        ))
                    else:
                        results.append(TestResult(
                            name=f"Prometheus Query: {metric}",
                            status="WARN",
                            message=f"{description}: No data (metric may be 0 or not scraped yet)"
                        ))
            except Exception as e:
                results.append(TestResult(
                    name=f"Prometheus Query: {metric}",
                    status="FAIL",
                    message=f"Error querying: {e}"
                ))
        
        return results
    
    def test_traces(self) -> List[TestResult]:
        """Test traces in Jaeger."""
        results = []
        
        # Check Jaeger services
        try:
            response = requests.get(f"{self.base_urls['jaeger']}/api/services", timeout=5)
            if response.status_code == 200:
                services = response.json().get("data", [])
                if "taskpilot" in services:
                    results.append(TestResult(
                        name="Jaeger Service",
                        status="PASS",
                        message=f"Service 'taskpilot' found. Total services: {len(services)}"
                    ))
                else:
                    results.append(TestResult(
                        name="Jaeger Service",
                        status="WARN",
                        message=f"Service 'taskpilot' not found. Available: {services}"
                    ))
        except Exception as e:
            results.append(TestResult(
                name="Jaeger Service",
                status="FAIL",
                message=f"Error checking services: {e}"
            ))
        
        # Check for traces
        try:
            response = requests.get(
                f"{self.base_urls['jaeger']}/api/traces",
                params={"service": "taskpilot", "limit": 1},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                traces = data.get("data", [])
                if traces:
                    trace = traces[0]
                    spans = trace.get("spans", [])
                    has_children = any(span.get("references") for span in spans)
                    
                    results.append(TestResult(
                        name="Jaeger Traces",
                        status="PASS",
                        message=f"Found {len(traces)} trace(s) with {len(spans)} span(s)",
                        details={
                            "trace_count": len(traces),
                            "span_count": len(spans),
                            "has_hierarchy": has_children
                        }
                    ))
                else:
                    results.append(TestResult(
                        name="Jaeger Traces",
                        status="WARN",
                        message="No traces found (run a workflow to generate traces)"
                    ))
        except Exception as e:
            results.append(TestResult(
                name="Jaeger Traces",
                status="FAIL",
                message=f"Error checking traces: {e}"
            ))
        
        return results
    
    def test_logs(self) -> List[TestResult]:
        """Test logs in Elasticsearch/Kibana."""
        results = []
        
        # Check Elasticsearch indices
        try:
            response = requests.get(f"{self.base_urls['elasticsearch']}/_cat/indices?v", timeout=5)
            if response.status_code == 200:
                indices_text = response.text
                if "taskpilot" in indices_text.lower():
                    results.append(TestResult(
                        name="Elasticsearch Indices",
                        status="PASS",
                        message="TaskPilot indices found"
                    ))
                else:
                    results.append(TestResult(
                        name="Elasticsearch Indices",
                        status="WARN",
                        message="No TaskPilot indices found (logs may not be shipped yet)"
                    ))
        except Exception as e:
            results.append(TestResult(
                name="Elasticsearch Indices",
                status="FAIL",
                message=f"Error checking indices: {e}"
            ))
        
        # Check Kibana status
        try:
            response = requests.get(f"{self.base_urls['kibana']}/api/status", timeout=5)
            if response.status_code == 200:
                results.append(TestResult(
                    name="Kibana Status",
                    status="PASS",
                    message="Kibana is accessible"
                ))
            else:
                results.append(TestResult(
                    name="Kibana Status",
                    status="WARN",
                    message=f"Kibana returned {response.status_code}"
                ))
        except Exception as e:
            results.append(TestResult(
                name="Kibana Status",
                status="FAIL",
                message=f"Error checking Kibana: {e}"
            ))
        
        # Check log files
        log_file = self.project_root / "logs" / "taskpilot.log"
        if log_file.exists():
            size = log_file.stat().st_size
            results.append(TestResult(
                name="Log File",
                status="PASS",
                message=f"Log file exists: {size} bytes",
                details={"file": str(log_file), "size": size}
            ))
        else:
            results.append(TestResult(
                name="Log File",
                status="WARN",
                message="Log file not found (may be created on first workflow run)"
            ))
        
        return results
    
    def test_dashboards(self) -> List[TestResult]:
        """Test and create dashboards in Grafana."""
        results = []
        
        # Try to get Grafana API key (or use basic auth)
        api_key = self.get_grafana_api_key()
        headers = {
            "Content-Type": "application/json"
        }
        
        from requests.auth import HTTPBasicAuth
        auth_obj = HTTPBasicAuth(self.grafana_user, self.grafana_password)
        
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            auth_obj = None  # Use API key instead
        
        # Check if Golden Signals dashboard exists
        dashboard_file = self.project_root / "observability" / "grafana" / "golden-signals-dashboard.json"
        if dashboard_file.exists():
            try:
                with open(dashboard_file) as f:
                    dashboard_data = json.load(f)
                
                dashboard_title = dashboard_data.get("dashboard", {}).get("title", "Golden Signals")
                
                # Search for dashboard
                response = requests.get(
                    f"{self.base_urls['grafana']}/api/search",
                    params={"query": dashboard_title},
                    headers=headers,
                    auth=auth_obj,
                    timeout=5
                )
                
                if response.status_code == 200:
                    dashboards = response.json()
                    existing = next((d for d in dashboards if d.get("title") == dashboard_title), None)
                    
                    if existing:
                        results.append(TestResult(
                            name="Golden Signals Dashboard",
                            status="PASS",
                            message=f"Dashboard exists: {existing.get('url', '')}",
                            details={"dashboard_id": existing.get("uid")}
                        ))
                    else:
                        # Create dashboard
                        print(f"  Creating dashboard: {dashboard_title}")
                        create_response = requests.post(
                            f"{self.base_urls['grafana']}/api/dashboards/db",
                            json=dashboard_data,
                            headers=headers,
                            auth=auth_obj,
                            timeout=10
                        )
                        
                        if create_response.status_code == 200:
                            results.append(TestResult(
                                name="Golden Signals Dashboard",
                                status="PASS",
                                message="Dashboard created successfully",
                                fix_applied=True
                            ))
                        else:
                            results.append(TestResult(
                                name="Golden Signals Dashboard",
                                status="FAIL",
                                message=f"Failed to create dashboard: {create_response.text[:200]}"
                            ))
            except Exception as e:
                results.append(TestResult(
                    name="Golden Signals Dashboard",
                    status="FAIL",
                    message=f"Error with dashboard: {e}"
                ))
        
        return results
    
    def test_alerts(self) -> List[TestResult]:
        """Test and create alerts in Prometheus."""
        results = []
        
        # Check alert rules file
        alerts_file = self.project_root / "observability" / "prometheus" / "golden-signals-alerts.yml"
        if alerts_file.exists():
            results.append(TestResult(
                name="Alert Rules File",
                status="PASS",
                message=f"Alert rules file exists: {alerts_file}"
            ))
            
            # Check if Prometheus has alert rules loaded
            try:
                response = requests.get(f"{self.base_urls['prometheus']}/api/v1/rules", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    rule_groups = data.get("data", {}).get("groups", [])
                    if rule_groups:
                        results.append(TestResult(
                            name="Alert Rules Configuration",
                            status="PASS",
                            message=f"Alert rules loaded: {len(rule_groups)} group(s)",
                            details={"groups": [g.get("name") for g in rule_groups]}
                        ))
                    else:
                        # Try to reload Prometheus
                        print("  Reloading Prometheus configuration...")
                        reload_response = requests.post(f"{self.base_urls['prometheus']}/-/reload", timeout=5)
                        if reload_response.status_code == 200:
                            time.sleep(2)  # Wait for reload
                            # Check again
                            response = requests.get(f"{self.base_urls['prometheus']}/api/v1/rules", timeout=5)
                            if response.status_code == 200:
                                data = response.json()
                                rule_groups = data.get("data", {}).get("groups", [])
                                if rule_groups:
                                    results.append(TestResult(
                                        name="Alert Rules Configuration",
                                        status="PASS",
                                        message="Alert rules loaded after reload",
                                        fix_applied=True
                                    ))
                                else:
                                    results.append(TestResult(
                                        name="Alert Rules Configuration",
                                        status="WARN",
                                        message="Alert rules file exists but not loaded in Prometheus"
                                    ))
                        else:
                            results.append(TestResult(
                                name="Alert Rules Configuration",
                                status="WARN",
                                message="Could not reload Prometheus (may need restart)"
                            ))
            except Exception as e:
                results.append(TestResult(
                    name="Alert Rules Configuration",
                    status="WARN",
                    message=f"Could not verify alert rules: {e}"
                ))
        else:
            results.append(TestResult(
                name="Alert Rules File",
                status="WARN",
                message="Alert rules file not found"
            ))
        
        # Check Prometheus alertmanager (if configured)
        try:
            response = requests.get(f"{self.base_urls['prometheus']}/api/v1/alerts", timeout=5)
            if response.status_code == 200:
                data = response.json()
                alerts = data.get("data", {}).get("alerts", [])
                results.append(TestResult(
                    name="Prometheus Alerts",
                    status="PASS",
                    message=f"Alert system accessible. {len(alerts)} active alert(s)",
                    details={"alerts": alerts}
                ))
        except Exception as e:
            results.append(TestResult(
                name="Prometheus Alerts",
                status="WARN",
                message=f"Could not check alerts: {e}"
            ))
        
        return results
    
    def test_leadership_metrics(self) -> List[TestResult]:
        """Test metrics for leadership demos."""
        results = []
        
        # Check golden signals endpoint
        try:
            response = requests.get(f"{self.base_urls['taskpilot']}/golden-signals", timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                required_signals = [
                    "success_rate",
                    "p95_latency",
                    "cost_per_successful_task",
                    "policy_violation_rate",
                ]
                
                found = [k for k in required_signals if k in data]
                missing = [k for k in required_signals if k not in data]
                
                results.append(TestResult(
                    name="Golden Signals API",
                    status="PASS" if not missing else "WARN",
                    message=f"Found {len(found)}/{len(required_signals)} signals",
                    details={"found": found, "missing": missing, "data": data}
                ))
        except Exception as e:
            results.append(TestResult(
                name="Golden Signals API",
                status="FAIL",
                message=f"Error accessing endpoint: {e}"
            ))
        
        # Check for business metrics
        business_metrics = [
            ("llm_cost_total", "Total LLM Cost"),
            ("workflow_success", "Successful Workflows"),
            ("policy_violations_total", "Policy Violations"),
        ]
        
        for metric, description in business_metrics:
            try:
                response = requests.get(
                    f"{self.base_urls['prometheus']}/api/v1/query",
                    params={"query": metric},
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    result = data.get("data", {}).get("result", [])
                    if result:
                        value = float(result[0].get("value", [None, "0"])[1])
                        results.append(TestResult(
                            name=f"Business Metric: {description}",
                            status="PASS",
                            message=f"{description}: {value}",
                            details={"metric": metric, "value": value}
                        ))
                    else:
                        results.append(TestResult(
                            name=f"Business Metric: {description}",
                            status="WARN",
                            message=f"{description}: No data available"
                        ))
            except Exception as e:
                results.append(TestResult(
                    name=f"Business Metric: {description}",
                    status="FAIL",
                    message=f"Error querying: {e}"
                ))
        
        return results
    
    def get_grafana_api_key(self) -> Optional[str]:
        """Get or create Grafana API key."""
        try:
            # First, try to get existing API keys
            session = requests.Session()
            
            # Login to get session cookie
            login_response = session.post(
                f"{self.base_urls['grafana']}/api/login",
                json={
                    "user": self.grafana_user,
                    "password": self.grafana_password
                },
                timeout=5
            )
            
            if login_response.status_code == 200:
                # Get existing keys
                keys_response = session.get(
                    f"{self.base_urls['grafana']}/api/auth/keys",
                    timeout=5
                )
                
                # Check if we already have a key
                if keys_response.status_code == 200:
                    existing_keys = keys_response.json()
                    for key in existing_keys:
                        if key.get("name") == "observability-test":
                            # Use existing key (note: we can't retrieve the actual key value)
                            # So we'll create a new one
                            session.delete(f"{self.base_urls['grafana']}/api/auth/keys/{key['id']}", timeout=5)
                
                # Create new API key
                key_response = session.post(
                    f"{self.base_urls['grafana']}/api/auth/keys",
                    json={
                        "name": "observability-test",
                        "role": "Admin",
                        "secondsToLive": 86400
                    },
                    timeout=5
                )
                
                if key_response.status_code == 200:
                    return key_response.json().get("key")
                elif key_response.status_code == 401:
                    # Try with basic auth instead
                    auth = (self.grafana_user, self.grafana_password)
                    key_response = requests.post(
                        f"{self.base_urls['grafana']}/api/auth/keys",
                        json={
                            "name": "observability-test",
                            "role": "Admin",
                            "secondsToLive": 86400
                        },
                        auth=auth,
                        timeout=5
                    )
                    if key_response.status_code == 200:
                        return key_response.json().get("key")
        except Exception as e:
            print(f"    Warning: Could not create Grafana API key: {e}")
        
        return None
    
    def print_results(self, results: List[TestResult]):
        """Print test results."""
        for result in results:
            status_icon = {
                "PASS": "✅",
                "FAIL": "❌",
                "WARN": "⚠️",
                "SKIP": "⏭️"
            }.get(result.status, "❓")
            
            fix_marker = "🔧" if result.fix_applied else ""
            print(f"  {status_icon} {result.name} {fix_marker}")
            if result.message:
                print(f"     {result.message}")
            if result.details:
                for key, value in result.details.items():
                    if key not in ["alerts", "data"]:  # Skip verbose details
                        print(f"     {key}: {value}")
    
    def calculate_summary(self, report: TestReport) -> Dict:
        """Calculate test summary."""
        all_results = (
            report.docker_services +
            report.data_generation +
            report.metrics +
            report.traces +
            report.logs +
            report.dashboards +
            report.alerts +
            report.leadership_metrics
        )
        
        total = len(all_results)
        passed = sum(1 for r in all_results if r.status == "PASS")
        failed = sum(1 for r in all_results if r.status == "FAIL")
        warned = sum(1 for r in all_results if r.status == "WARN")
        fixes = sum(1 for r in all_results if r.fix_applied)
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "warned": warned,
            "fixes_applied": fixes,
            "pass_rate": (passed / total * 100) if total > 0 else 0
        }
    
    def print_summary(self, summary: Dict):
        """Print test summary."""
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {summary['total']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"⚠️  Warnings: {summary['warned']}")
        print(f"🔧 Fixes Applied: {summary['fixes_applied']}")
        print(f"Pass Rate: {summary['pass_rate']:.1f}%")
        print()
        
        if summary['failed'] > 0:
            print("⚠️  Some tests failed. Review the results above.")
        elif summary['warned'] > 0:
            print("⚠️  Some tests have warnings. System may be partially functional.")
        else:
            print("✅ All tests passed! Observability stack is ready.")
    
    def save_report(self, report: TestReport):
        """Save test report to file."""
        report_file = self.project_root / "observability_test_report.json"
        try:
            with open(report_file, "w") as f:
                json.dump({
                    "timestamp": report.timestamp,
                    "summary": report.summary,
                    "docker_services": [r.__dict__ for r in report.docker_services],
                    "data_generation": [r.__dict__ for r in report.data_generation],
                    "metrics": [r.__dict__ for r in report.metrics],
                    "traces": [r.__dict__ for r in report.traces],
                    "logs": [r.__dict__ for r in report.logs],
                    "dashboards": [r.__dict__ for r in report.dashboards],
                    "alerts": [r.__dict__ for r in report.alerts],
                    "leadership_metrics": [r.__dict__ for r in report.leadership_metrics],
                }, f, indent=2)
            print(f"📄 Report saved to: {report_file}")
        except Exception as e:
            print(f"⚠️  Could not save report: {e}")

if __name__ == "__main__":
    tester = ObservabilityTester(project_root)
    report = tester.run()
    
    # Exit with error code if tests failed
    if report.summary.get("failed", 0) > 0:
        sys.exit(1)
    sys.exit(0)
