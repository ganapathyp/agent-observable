#!/usr/bin/env python3
"""
Verify that demo data is present in Docker observability tools.

This script checks:
- Prometheus metrics
- Jaeger traces
- Elasticsearch/Kibana logs
- Grafana dashboards
"""

import json
import requests
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configuration
PROMETHEUS_URL = "http://localhost:9090"
GRAFANA_URL = "http://localhost:3000"
JAEGER_URL = "http://localhost:16686"
ELASTICSEARCH_URL = "http://localhost:9200"
KIBANA_URL = "http://localhost:5601"

GRAFANA_USER = "admin"
GRAFANA_PASSWORD = "admin"

BASE_DIR = Path(__file__).parent.parent
LOGS_FILE = BASE_DIR / "logs" / "taskpilot.log"
DECISIONS_FILE = BASE_DIR / "decision_logs.jsonl"


def check_service(name: str, url: str, endpoint: str = "") -> bool:
    """Check if a service is accessible."""
    try:
        response = requests.get(f"{url}{endpoint}", timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        return False


def check_prometheus_metrics() -> Dict[str, Any]:
    """Check Prometheus for metrics."""
    print("\n📊 Checking Prometheus Metrics...")
    print("-" * 60)
    
    if not check_service("Prometheus", PROMETHEUS_URL, "/-/healthy"):
        return {"status": "error", "message": "Prometheus not accessible"}
    
    metrics_to_check = [
        "workflow_runs",
        "workflow_success",
        "workflow_errors",
        "llm_cost_total",
        "llm_tokens_total",
        "policy_violations_total",
    ]
    
    results = {}
    for metric in metrics_to_check:
        try:
            response = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": metric},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    result = data.get("data", {}).get("result", [])
                    if result:
                        value = result[0].get("value", [None, "0"])[1]
                        results[metric] = {"found": True, "value": value}
                        print(f"  ✅ {metric}: {value}")
                    else:
                        results[metric] = {"found": False, "value": None}
                        print(f"  ⚠️  {metric}: Not found (may need time to scrape)")
                else:
                    results[metric] = {"found": False, "error": data.get("error")}
                    print(f"  ❌ {metric}: Query error")
            else:
                results[metric] = {"found": False, "error": f"HTTP {response.status_code}"}
                print(f"  ❌ {metric}: HTTP {response.status_code}")
        except Exception as e:
            results[metric] = {"found": False, "error": str(e)}
            print(f"  ❌ {metric}: {e}")
    
    return {"status": "ok", "results": results}


def check_jaeger_traces() -> Dict[str, Any]:
    """Check Jaeger for traces."""
    print("\n🔍 Checking Jaeger Traces...")
    print("-" * 60)
    
    if not check_service("Jaeger", JAEGER_URL):
        return {"status": "error", "message": "Jaeger not accessible"}
    
    try:
        # Query traces for taskpilot service
        response = requests.get(
            f"{JAEGER_URL}/api/traces",
            params={"service": "taskpilot", "limit": 10},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            traces = data.get("data", [])
            trace_count = len(traces)
            
            if trace_count > 0:
                print(f"  ✅ Found {trace_count} traces for service 'taskpilot'")
                
                # Check for hierarchy (spans with children)
                spans_with_children = 0
                for trace in traces:
                    for span in trace.get("spans", []):
                        if span.get("childSpanIds"):
                            spans_with_children += 1
                
                if spans_with_children > 0:
                    print(f"  ✅ Found {spans_with_children} spans with child spans (hierarchy present)")
                else:
                    print(f"  ⚠️  No spans with children found (hierarchy may be missing)")
                
                return {"status": "ok", "trace_count": trace_count, "hierarchy": spans_with_children > 0}
            else:
                print(f"  ⚠️  No traces found (may need time to export)")
                return {"status": "warning", "trace_count": 0}
        else:
            print(f"  ❌ HTTP {response.status_code}")
            return {"status": "error", "message": f"HTTP {response.status_code}"}
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"status": "error", "message": str(e)}


def check_elasticsearch_logs() -> Dict[str, Any]:
    """Check Elasticsearch for logs."""
    print("\n📝 Checking Elasticsearch Logs...")
    print("-" * 60)
    
    if not check_service("Elasticsearch", ELASTICSEARCH_URL):
        return {"status": "error", "message": "Elasticsearch not accessible"}
    
    try:
        # List indices
        response = requests.get(f"{ELASTICSEARCH_URL}/_cat/indices/taskpilot-logs-*?format=json", timeout=5)
        if response.status_code == 200:
            indices = response.json()
            if indices:
                print(f"  ✅ Found {len(indices)} log indices")
                
                # Get document count from first index
                index_name = indices[0].get("index")
                if index_name:
                    count_response = requests.get(
                        f"{ELASTICSEARCH_URL}/{index_name}/_count",
                        timeout=5
                    )
                    if count_response.status_code == 200:
                        count_data = count_response.json()
                        doc_count = count_data.get("count", 0)
                        print(f"  ✅ Index '{index_name}': {doc_count} documents")
                        
                        # Sample a document
                        sample_response = requests.get(
                            f"{ELASTICSEARCH_URL}/{index_name}/_search",
                            params={"size": 1},
                            timeout=5
                        )
                        if sample_response.status_code == 200:
                            sample_data = sample_response.json()
                            hits = sample_data.get("hits", {}).get("hits", [])
                            if hits:
                                print(f"  ✅ Sample document found")
                                return {"status": "ok", "index_count": len(indices), "doc_count": doc_count}
                        
                        return {"status": "ok", "index_count": len(indices), "doc_count": doc_count}
            else:
                print(f"  ⚠️  No log indices found (Filebeat may not have shipped logs yet)")
                return {"status": "warning", "index_count": 0}
        else:
            print(f"  ❌ HTTP {response.status_code}")
            return {"status": "error", "message": f"HTTP {response.status_code}"}
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"status": "error", "message": str(e)}


def check_local_files() -> Dict[str, Any]:
    """Check local files for generated data."""
    print("\n📁 Checking Local Files...")
    print("-" * 60)
    
    results = {}
    
    # Check logs file
    if LOGS_FILE.exists():
        log_count = sum(1 for _ in LOGS_FILE.open())
        results["logs"] = {"exists": True, "count": log_count}
        print(f"  ✅ {LOGS_FILE.name}: {log_count} entries")
    else:
        results["logs"] = {"exists": False, "count": 0}
        print(f"  ❌ {LOGS_FILE.name}: Not found")
    
    # Check decisions file
    if DECISIONS_FILE.exists():
        decision_count = sum(1 for _ in DECISIONS_FILE.open())
        results["decisions"] = {"exists": True, "count": decision_count}
        print(f"  ✅ {DECISIONS_FILE.name}: {decision_count} entries")
    else:
        results["decisions"] = {"exists": False, "count": 0}
        print(f"  ❌ {DECISIONS_FILE.name}: Not found")
    
    return {"status": "ok", "results": results}


def check_grafana_dashboard() -> Dict[str, Any]:
    """Check if Grafana dashboard exists."""
    print("\n📈 Checking Grafana Dashboard...")
    print("-" * 60)
    
    if not check_service("Grafana", GRAFANA_URL, "/api/health"):
        return {"status": "error", "message": "Grafana not accessible"}
    
    try:
        # Get API key or use basic auth
        auth = (GRAFANA_USER, GRAFANA_PASSWORD)
        
        # Check dashboards
        response = requests.get(
            f"{GRAFANA_URL}/api/search",
            params={"query": "golden-signals"},
            auth=auth,
            timeout=5
        )
        
        if response.status_code == 200:
            dashboards = response.json()
            if dashboards:
                print(f"  ✅ Found {len(dashboards)} dashboard(s) matching 'golden-signals'")
                for dash in dashboards:
                    print(f"     - {dash.get('title')} (UID: {dash.get('uid')})")
                return {"status": "ok", "dashboard_count": len(dashboards)}
            else:
                print(f"  ⚠️  No dashboards found (may need to import)")
                return {"status": "warning", "dashboard_count": 0}
        else:
            print(f"  ❌ HTTP {response.status_code}")
            return {"status": "error", "message": f"HTTP {response.status_code}"}
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"status": "error", "message": str(e)}


def print_viewing_instructions():
    """Print instructions for viewing data in tools."""
    print("\n" + "=" * 60)
    print("📖 VIEWING INSTRUCTIONS")
    print("=" * 60)
    
    print("\n1️⃣  GRAFANA (Metrics & Dashboards)")
    print("-" * 60)
    print("   URL: http://localhost:3000")
    print("   Login: admin / admin")
    print("   Dashboard: Golden Signals LLM Production")
    print("   Direct Link: http://localhost:3000/d/02b9018d-c9b7-4b7d-8b09-1bc4fdfccba8/golden-signals-llm-production")
    print("   What to check:")
    print("     - Cost per Successful Task")
    print("     - Workflow Success Rate")
    print("     - Policy Violations")
    print("     - Agent Latency (P95)")
    
    print("\n2️⃣  PROMETHEUS (Metrics Query)")
    print("-" * 60)
    print("   URL: http://localhost:9090")
    print("   Try queries:")
    print("     - workflow_runs")
    print("     - llm_cost_total")
    print("     - policy_violations_total")
    print("     - rate(workflow_runs[5m])")
    
    print("\n3️⃣  JAEGER (Traces)")
    print("-" * 60)
    print("   URL: http://localhost:16686")
    print("   Search:")
    print("     - Service: taskpilot")
    print("     - Look for traces with hierarchy (workflow → agent → tool)")
    print("   What to check:")
    print("     - Trace timeline shows parent-child relationships")
    print("     - Spans have proper tags (request_id, agent_name, etc.)")
    print("     - Slow ExecutorAgent spans (5000ms+) in performance_bottleneck scenario")
    
    print("\n4️⃣  KIBANA (Logs)")
    print("-" * 60)
    print("   URL: http://localhost:5601")
    print("   Setup:")
    print("     1. Go to Stack Management → Index Patterns")
    print("     2. Create pattern: taskpilot-logs-*")
    print("     3. Time field: @timestamp")
    print("   Discover:")
    print("     - Filter by scenario: scenario:cost_optimization")
    print("     - Filter by level: level:ERROR")
    print("     - Filter by log_type: log_type:policy_decision")
    print("   What to check:")
    print("     - Log entries from all scenarios")
    print("     - Policy decisions (log_type:policy_decision)")
    print("     - Error logs (level:ERROR)")
    
    print("\n5️⃣  ELASTICSEARCH (Direct API)")
    print("-" * 60)
    print("   URL: http://localhost:9200")
    print("   Check indices:")
    print("     curl http://localhost:9200/_cat/indices/taskpilot-logs-*")
    print("   Count documents:")
    print("     curl http://localhost:9200/taskpilot-logs-*/_count")
    print("   Sample document:")
    print("     curl http://localhost:9200/taskpilot-logs-*/_search?size=1")


def main():
    """Main verification function."""
    print("🔍 Demo Data Verification")
    print("=" * 60)
    
    # Check local files first
    file_results = check_local_files()
    
    # Check services
    print("\n🌐 Checking Services...")
    print("-" * 60)
    
    services = {
        "Prometheus": (PROMETHEUS_URL, "/-/healthy"),
        "Grafana": (GRAFANA_URL, "/api/health"),
        "Jaeger": (JAEGER_URL, ""),
        "Elasticsearch": (ELASTICSEARCH_URL, ""),
        "Kibana": (KIBANA_URL, "/api/status"),
    }
    
    all_services_up = True
    for name, (url, endpoint) in services.items():
        if check_service(name, url, endpoint):
            print(f"  ✅ {name}: Running")
        else:
            print(f"  ❌ {name}: Not accessible")
            all_services_up = False
    
    if not all_services_up:
        print("\n⚠️  Some services are not running. Start with:")
        print("   docker-compose -f docker-compose.observability.yml up -d")
        print("   Wait 30-60 seconds for services to start")
        return
    
    # Check data in services
    prometheus_results = check_prometheus_metrics()
    jaeger_results = check_jaeger_traces()
    elasticsearch_results = check_elasticsearch_logs()
    grafana_results = check_grafana_dashboard()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    print(f"\nLocal Files:")
    if file_results.get("results", {}).get("logs", {}).get("exists"):
        print(f"  ✅ Logs: {file_results['results']['logs']['count']} entries")
    else:
        print(f"  ❌ Logs: Not found")
    
    if file_results.get("results", {}).get("decisions", {}).get("exists"):
        print(f"  ✅ Decisions: {file_results['results']['decisions']['count']} entries")
    else:
        print(f"  ❌ Decisions: Not found")
    
    print(f"\nServices:")
    print(f"  Prometheus: {prometheus_results.get('status', 'unknown')}")
    print(f"  Jaeger: {jaeger_results.get('status', 'unknown')} ({jaeger_results.get('trace_count', 0)} traces)")
    print(f"  Elasticsearch: {elasticsearch_results.get('status', 'unknown')} ({elasticsearch_results.get('doc_count', 0)} docs)")
    print(f"  Grafana: {grafana_results.get('status', 'unknown')}")
    
    # Print viewing instructions
    print_viewing_instructions()
    
    print("\n✅ Verification complete!")


if __name__ == "__main__":
    main()
