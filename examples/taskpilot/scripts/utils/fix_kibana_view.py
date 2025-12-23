#!/usr/bin/env python3
"""Fix Kibana view - extend time range and verify log_type field."""
import requests
import sys
from datetime import datetime, timedelta

KIBANA_URL = "http://localhost:5601"
ELASTICSEARCH_URL = "http://localhost:9200"

def check_recent_data():
    """Check if there's recent data in Elasticsearch."""
    print("Checking for recent policy decisions...")
    
    # Check last 24 hours
    now = datetime.utcnow()
    one_day_ago = now - timedelta(days=1)
    
    query = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"log_type": "policy_decision"}},
                    {"range": {"@timestamp": {"gte": one_day_ago.isoformat() + "Z"}}}
                ]
            }
        },
        "size": 1,
        "sort": [{"@timestamp": {"order": "desc"}}]
    }
    
    try:
        response = requests.post(
            f"{ELASTICSEARCH_URL}/taskpilot-logs-*/_search",
            json=query,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            total = data.get('hits', {}).get('total', {})
            if isinstance(total, dict):
                count = total.get('value', 0)
            else:
                count = total
            
            hits = data.get('hits', {}).get('hits', [])
            if hits:
                source = hits[0].get('_source', {})
                latest_time = source.get('@timestamp', source.get('timestamp', 'N/A'))
                print(f"✓ Found {count} policy decisions in last 24 hours")
                print(f"  Most recent: {latest_time}")
                return True, latest_time
            else:
                print(f"⚠ Found {count} policy decisions but couldn't get sample")
                return count > 0, None
        return False, None
    except Exception as e:
        print(f"✗ Error checking data: {e}")
        return False, None

def get_index_pattern_info(pattern_id):
    """Get information about the index pattern."""
    try:
        response = requests.get(
            f"{KIBANA_URL}/api/saved_objects/index-pattern/{pattern_id}",
            headers={"kbn-xsrf": "true"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            attrs = data.get('attributes', {})
            return attrs.get('title'), attrs.get('timeFieldName')
        return None, None
    except Exception as e:
        print(f"⚠ Could not get index pattern info: {e}")
        return None, None

def main():
    """Main diagnostic function."""
    print("=" * 80)
    print("Kibana View Diagnostic")
    print("=" * 80)
    print()
    
    # Check data
    has_data, latest_time = check_recent_data()
    print()
    
    if not has_data:
        print("⚠ No recent policy decisions found")
        print("  → Run the application to generate decision logs")
        print("  → Or extend time range to see older data")
        return 1
    
    # Get index pattern info
    pattern_id = "da49ff3e-1ba8-47fe-9c84-d54ab963a588"
    pattern_name, time_field = get_index_pattern_info(pattern_id)
    
    print("=" * 80)
    print("SOLUTION")
    print("=" * 80)
    print()
    print("Your time range is too short (last 15 minutes).")
    print()
    print("To see policy decisions:")
    print("1. In Kibana Discover, click the time picker (top right)")
    print("2. Change from 'Last 15 minutes' to 'Last 24 hours' or 'Last 7 days'")
    print("3. Click 'Update'")
    print()
    print("Then filter by log_type:")
    print("1. In the search bar, enter: log_type: \"policy_decision\"")
    print("2. Press Enter")
    print()
    if latest_time:
        print(f"Most recent policy decision: {latest_time}")
        print("Make sure your time range includes this timestamp")
    print()
    print("Direct link with 24h time range:")
    print(f"{KIBANA_URL}/app/discover#/?_g=(filters:!(),refreshInterval:(pause:!t,value:60000),time:(from:now-24h,to:now))&_a=(columns:!(),filters:!(),index:{pattern_id},interval:auto,query:(language:kuery,query:'log_type:%22policy_decision%22'),sort:!(!('@timestamp',desc)))")
    
    return 0

if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        print("ERROR: 'requests' required. Install: pip install requests")
        sys.exit(1)
    
    sys.exit(main())
