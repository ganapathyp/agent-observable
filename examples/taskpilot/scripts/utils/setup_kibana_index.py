#!/usr/bin/env python3
"""Setup Kibana index pattern for taskpilot logs via API."""
import requests
import json
import sys
from datetime import datetime

KIBANA_URL = "http://localhost:5601"
ELASTICSEARCH_URL = "http://localhost:9200"

def check_elasticsearch():
    """Check if Elasticsearch has data."""
    try:
        response = requests.get(f"{ELASTICSEARCH_URL}/taskpilot-logs-*/_count", timeout=5)
        if response.status_code == 200:
            data = response.json()
            total = data.get('count', 0)
            print(f"✓ Elasticsearch: Found {total} total log entries")
            
            # Check for policy decisions
            response = requests.get(
                f"{ELASTICSEARCH_URL}/taskpilot-logs-*/_count",
                params={"q": "log_type:policy_decision"},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                policy_count = data.get('count', 0)
                print(f"✓ Elasticsearch: Found {policy_count} policy decision entries")
                return True, total, policy_count
        return False, 0, 0
    except Exception as e:
        print(f"✗ Elasticsearch check failed: {e}")
        return False, 0, 0

def create_index_pattern(pattern_name="taskpilot-logs-*"):
    """Create Kibana index pattern."""
    try:
        # Check if pattern already exists
        response = requests.get(
            f"{KIBANA_URL}/api/saved_objects/_find",
            params={"type": "index-pattern", "search": pattern_name},
            headers={"kbn-xsrf": "true"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            existing = [p for p in data.get('saved_objects', []) 
                       if p.get('attributes', {}).get('title') == pattern_name]
            if existing:
                print(f"✓ Index pattern '{pattern_name}' already exists")
                return True
        
        # Create new index pattern
        pattern_id = pattern_name.replace('*', 'star').replace('-', '_')
        payload = {
            "attributes": {
                "title": pattern_name,
                "timeFieldName": "@timestamp"
            }
        }
        
        response = requests.post(
            f"{KIBANA_URL}/api/saved_objects/index-pattern/{pattern_id}",
            json=payload,
            headers={
                "kbn-xsrf": "true",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            print(f"✓ Created index pattern '{pattern_name}'")
            return True
        else:
            print(f"⚠ Could not create via API (status {response.status_code})")
            print("  You may need to create it manually in Kibana UI")
            return False
    except Exception as e:
        print(f"✗ Failed to create index pattern: {e}")
        return False

def main():
    """Main setup function."""
    print("=" * 80)
    print("Kibana Index Pattern Setup")
    print("=" * 80)
    print()
    
    # Check Elasticsearch
    print("[1] Checking Elasticsearch...")
    es_ok, total_logs, policy_logs = check_elasticsearch()
    if not es_ok:
        print("✗ Elasticsearch is not accessible")
        return 1
    print()
    
    # Check Kibana
    print("[2] Checking Kibana...")
    try:
        response = requests.get(f"{KIBANA_URL}/api/status", timeout=5)
        if response.status_code == 200:
            print("✓ Kibana is accessible")
        else:
            print("⚠ Kibana may have issues")
    except Exception as e:
        print(f"✗ Kibana check failed: {e}")
        return 1
    print()
    
    # Create pattern
    print("[3] Setting up index pattern 'taskpilot-logs-*'...")
    if create_index_pattern():
        print()
        print("=" * 80)
        print("SETUP COMPLETE")
        print("=" * 80)
        print()
        print(f"Data available in Elasticsearch:")
        print(f"  - Total logs: {total_logs}")
        print(f"  - Policy decisions: {policy_logs}")
        print()
        print("Next steps:")
        print(f"1. Open Kibana: {KIBANA_URL}")
        print("2. Go to: Discover")
        print("3. Select index pattern: 'taskpilot-logs-*'")
        print("4. Filter by: log_type: \"policy_decision\"")
        return 0
    else:
        print()
        print("Manual setup:")
        print(f"1. Open Kibana: {KIBANA_URL}")
        print("2. Stack Management → Index Patterns → Create")
        print("3. Pattern: taskpilot-logs-*")
        print("4. Time field: @timestamp")
        return 1

if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        print("ERROR: 'requests' required. Install: pip install requests")
        sys.exit(1)
    
    sys.exit(main())
