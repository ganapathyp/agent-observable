#!/usr/bin/env python3
"""
Setup Kibana index pattern for taskpilot logs.

This script uses Kibana API to:
1. Create index pattern: taskpilot-logs-* (or .ds-taskpilot-logs-*)
2. Set time field: @timestamp
3. Verify the pattern works
"""

import json
import requests
import sys
from typing import Dict, Any, Optional

KIBANA_URL = "http://localhost:5601"
ELASTICSEARCH_URL = "http://localhost:9200"
KIBANA_USER = "elastic"  # Default, but may not be needed if security disabled
KIBANA_PASSWORD = ""  # Not needed if security disabled

# Try both patterns
INDEX_PATTERNS = [
    "taskpilot-logs-*",  # Standard pattern
    ".ds-taskpilot-logs-*",  # Data stream pattern (what Elasticsearch actually uses)
    "taskpilot-logs-*,.ds-taskpilot-logs-*",  # Combined
]


def get_kibana_session() -> requests.Session:
    """Get Kibana session (may need auth if security enabled)."""
    session = requests.Session()
    # Try to authenticate if needed
    try:
        response = session.get(f"{KIBANA_URL}/api/status", timeout=5)
        if response.status_code == 401:
            # Try with basic auth
            session.auth = (KIBANA_USER, KIBANA_PASSWORD) if KIBANA_PASSWORD else None
    except Exception:
        pass
    return session


def check_kibana_accessible() -> bool:
    """Check if Kibana is accessible."""
    try:
        response = requests.get(f"{KIBANA_URL}/api/status", timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Kibana not accessible: {e}")
        return False


def list_existing_patterns(session: requests.Session) -> list:
    """List existing index patterns."""
    try:
        response = session.get(f"{KIBANA_URL}/api/saved_objects/_find", params={
            "type": "index-pattern",
            "per_page": 100
        }, timeout=10)
        if response.status_code == 200:
            data = response.json()
            patterns = [obj["attributes"]["title"] for obj in data.get("saved_objects", [])]
            return patterns
        else:
            print(f"⚠️  Could not list patterns: HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"⚠️  Error listing patterns: {e}")
        return []


def create_index_pattern(session: requests.Session, pattern: str) -> Optional[Dict[str, Any]]:
    """Create an index pattern in Kibana."""
    try:
        # Check if pattern already exists
        existing = list_existing_patterns(session)
        if pattern in existing:
            print(f"✅ Index pattern '{pattern}' already exists")
            return {"exists": True, "pattern": pattern}
        
        # Create new pattern
        payload = {
            "attributes": {
                "title": pattern,
                "timeFieldName": "@timestamp"
            }
        }
        
        response = session.post(
            f"{KIBANA_URL}/api/saved_objects/index-pattern/{pattern.replace('*', 'star').replace('.', '_')}",
            json=payload,
            headers={"Content-Type": "application/json", "kbn-xsrf": "true"},
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            print(f"✅ Created index pattern: {pattern}")
            return {"created": True, "pattern": pattern, "data": response.json()}
        elif response.status_code == 409:
            print(f"⚠️  Pattern '{pattern}' already exists (409)")
            return {"exists": True, "pattern": pattern}
        else:
            print(f"❌ Failed to create pattern '{pattern}': HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating pattern '{pattern}': {e}")
        return None


def verify_pattern(session: requests.Session, pattern: str) -> bool:
    """Verify index pattern works by checking if it matches indices."""
    try:
        # Check what indices match the pattern
        response = session.get(
            f"{KIBANA_URL}/api/index_patterns/_fields_for_wildcard",
            params={"pattern": pattern},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            fields = data.get("fields", [])
            print(f"✅ Pattern '{pattern}' matches {len(fields)} fields")
            return True
        else:
            print(f"⚠️  Pattern verification failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"⚠️  Error verifying pattern: {e}")
        return False


def check_elasticsearch_indices() -> list:
    """Check what indices exist in Elasticsearch."""
    try:
        response = requests.get(f"{ELASTICSEARCH_URL}/_cat/indices/taskpilot-logs-*?format=json", timeout=5)
        if response.status_code == 200:
            indices = response.json()
            index_names = [idx["index"] for idx in indices]
            return index_names
        else:
            # Try data stream pattern
            response = requests.get(f"{ELASTICSEARCH_URL}/_cat/indices/.ds-taskpilot-logs-*?format=json", timeout=5)
            if response.status_code == 200:
                indices = response.json()
                index_names = [idx["index"] for idx in indices]
                return index_names
    except Exception as e:
        print(f"⚠️  Error checking indices: {e}")
    return []


def main():
    """Main function."""
    print("🔧 Kibana Index Pattern Setup")
    print("=" * 60)
    
    # Check Kibana
    if not check_kibana_accessible():
        print("\n❌ Kibana is not accessible at http://localhost:5601")
        print("   Make sure Docker stack is running:")
        print("   docker-compose -f docker-compose.observability.yml up -d")
        return 1
    
    print("✅ Kibana is accessible")
    
    # Check Elasticsearch indices
    print("\n📊 Checking Elasticsearch indices...")
    indices = check_elasticsearch_indices()
    if indices:
        print(f"✅ Found {len(indices)} indices:")
        for idx in indices[:5]:
            print(f"   - {idx}")
        if len(indices) > 5:
            print(f"   ... and {len(indices) - 5} more")
    else:
        print("⚠️  No taskpilot log indices found")
        print("   Make sure Filebeat has shipped logs")
    
    # Get session
    session = get_kibana_session()
    
    # List existing patterns
    print("\n📋 Checking existing index patterns...")
    existing = list_existing_patterns(session)
    if existing:
        print(f"✅ Found {len(existing)} existing patterns:")
        for pattern in existing:
            print(f"   - {pattern}")
    else:
        print("   No existing patterns found")
    
    # Try to create patterns
    print("\n🔨 Creating index patterns...")
    created_patterns = []
    
    for pattern in INDEX_PATTERNS:
        result = create_index_pattern(session, pattern)
        if result and result.get("created"):
            created_patterns.append(pattern)
            # Verify it works
            verify_pattern(session, pattern)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    if created_patterns:
        print(f"✅ Created {len(created_patterns)} index pattern(s)")
        print("\n📖 Next Steps:")
        print("1. Go to Kibana: http://localhost:5601")
        print("2. Go to Discover")
        print("3. Select index pattern: taskpilot-logs-* (or .ds-taskpilot-logs-*)")
        print("4. Set time range to 'Last 24 hours' or 'Last 7 days'")
        print("5. Try filters:")
        print("   - scenario:cost_optimization")
        print("   - level:ERROR")
        print("   - log_type:policy_decision")
    else:
        print("⚠️  No new patterns created (may already exist)")
        print("\n📖 If you still don't see data:")
        print("1. Go to Stack Management → Index Patterns")
        print("2. Check if 'taskpilot-logs-*' or '.ds-taskpilot-logs-*' exists")
        print("3. If it exists, click it and verify time field is '@timestamp'")
        print("4. Go to Discover and select the pattern")
        print("5. Set time range to 'Last 24 hours'")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
