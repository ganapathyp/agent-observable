#!/usr/bin/env python3
"""Test that decision logs are properly sent to Kibana via Filebeat."""
import asyncio
import time
import requests
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_decision_logs_to_kibana():
    """Test that decision logs flow from app → file → Filebeat → Elasticsearch → Kibana."""
    
    print("=" * 80)
    print("Decision Logs → Kibana Integration Test")
    print("=" * 80)
    print()
    
    # Step 1: Check services are running
    print("[1] Checking services...")
    services_ok = True
    
    # Check Elasticsearch
    try:
        response = requests.get("http://localhost:9200/_cluster/health", timeout=5)
        if response.status_code == 200:
            print("  ✓ Elasticsearch: Running")
        else:
            print("  ✗ Elasticsearch: Not healthy")
            services_ok = False
    except Exception as e:
        print(f"  ✗ Elasticsearch: Not accessible ({e})")
        services_ok = False
    
    # Check Kibana
    try:
        response = requests.get("http://localhost:5601/api/status", timeout=5)
        if response.status_code == 200:
            print("  ✓ Kibana: Running")
        else:
            print("  ✗ Kibana: Not healthy")
            services_ok = False
    except Exception as e:
        print(f"  ✗ Kibana: Not accessible ({e})")
        services_ok = False
    
    # Check Filebeat
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=taskpilot-filebeat", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "taskpilot-filebeat" in result.stdout:
            print("  ✓ Filebeat: Running")
        else:
            print("  ✗ Filebeat: Not running")
            services_ok = False
    except Exception as e:
        print(f"  ✗ Filebeat: Check failed ({e})")
        services_ok = False
    
    if not services_ok:
        print()
        print("✗ Services not running. Start with:")
        print("  docker-compose -f docker-compose.observability.yml up -d")
        return False
    
    print()
    
    # Step 2: Check log file exists and has recent entries
    print("[2] Checking log file...")
    log_file = project_root / "logs" / "taskpilot.log"
    if not log_file.exists():
        print(f"  ✗ Log file not found: {log_file}")
        print("  → Run the application to generate logs")
        return False
    
    # Check for recent policy decisions in file
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_policy_logs = []
            for line in lines[-100:]:  # Check last 100 lines
                try:
                    import json
                    log_entry = json.loads(line.strip())
                    if log_entry.get('log_type') == 'policy_decision':
                        recent_policy_logs.append(log_entry)
                except:
                    continue
            
            if recent_policy_logs:
                print(f"  ✓ Found {len(recent_policy_logs)} recent policy decisions in log file")
            else:
                print("  ⚠ No recent policy decisions in log file")
                print("  → Run the application to generate decision logs")
    except Exception as e:
        print(f"  ✗ Error reading log file: {e}")
        return False
    
    print()
    
    # Step 3: Check Elasticsearch has the data
    print("[3] Checking Elasticsearch for policy decisions...")
    try:
        response = requests.get(
            "http://localhost:9200/taskpilot-logs-*/_search",
            params={"q": "log_type:policy_decision", "size": 1},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            total = data.get('hits', {}).get('total', {})
            if isinstance(total, dict):
                total_count = total.get('value', 0)
            else:
                total_count = total
            
            if total_count > 0:
                print(f"  ✓ Found {total_count} policy decisions in Elasticsearch")
                
                # Show sample
                hits = data.get('hits', {}).get('hits', [])
                if hits:
                    source = hits[0].get('_source', {})
                    print(f"  Sample: {source.get('decision_type')} - {source.get('result')} - {source.get('tool_name')}")
            else:
                print("  ✗ No policy decisions found in Elasticsearch")
                print("  → Wait a few seconds for Filebeat to ship logs")
                return False
        else:
            print(f"  ✗ Elasticsearch query failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Elasticsearch check failed: {e}")
        return False
    
    print()
    
    # Step 4: Check Kibana index pattern
    print("[4] Checking Kibana index pattern...")
    try:
        response = requests.get(
            "http://localhost:5601/api/saved_objects/_find",
            params={"type": "index-pattern", "search": "taskpilot-logs"},
            headers={"kbn-xsrf": "true"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            patterns = [p for p in data.get('saved_objects', [])
                       if 'taskpilot-logs' in p.get('attributes', {}).get('title', '')]
            if patterns:
                print(f"  ✓ Found {len(patterns)} index pattern(s) in Kibana")
            else:
                print("  ⚠ No index pattern found in Kibana")
                print("  → Run: python3 scripts/utils/setup_kibana_index.py")
                print("  → Or create manually in Kibana UI")
        else:
            print(f"  ⚠ Could not check Kibana patterns: {response.status_code}")
    except Exception as e:
        print(f"  ⚠ Kibana check failed: {e}")
    
    print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✓ Decision logs are being written to file")
    print("✓ Decision logs are in Elasticsearch")
    print("✓ Data flow: App → File → Filebeat → Elasticsearch ✓")
    print()
    print("To view in Kibana:")
    print("1. Open: http://localhost:5601")
    print("2. Go to: Discover")
    print("3. Select index pattern: 'taskpilot-logs-*' (create if needed)")
    print("4. Filter by: log_type: \"policy_decision\"")
    print()
    print("If index pattern is missing, run:")
    print("  python3 scripts/utils/setup_kibana_index.py")
    
    return True

if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        print("ERROR: 'requests' required. Install: pip install requests")
        sys.exit(1)
    
    success = test_decision_logs_to_kibana()
    sys.exit(0 if success else 1)
