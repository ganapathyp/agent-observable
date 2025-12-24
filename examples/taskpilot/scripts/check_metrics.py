#!/usr/bin/env python3
"""Check what metrics are exposed by the /metrics endpoint."""
import sys
import requests
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_metrics_endpoint(port: int = 8000):
    """Check metrics endpoint and list all available metrics."""
    url = f"http://localhost:{port}/metrics"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        print(f"✅ Metrics endpoint accessible: {url}")
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        print()
        
        # Parse metrics
        lines = response.text.strip().split('\n')
        counters = []
        gauges = []
        histograms = []
        current_type = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                if line.startswith('# TYPE'):
                    # Extract type
                    parts = line.split()
                    if len(parts) >= 3:
                        current_type = parts[2]
                        metric_name = parts[1]
                        if current_type == 'counter':
                            counters.append(metric_name)
                        elif current_type == 'gauge':
                            gauges.append(metric_name)
                        elif current_type == 'histogram':
                            histograms.append(metric_name)
                continue
            
            # Metric value line
            parts = line.split()
            if len(parts) >= 2:
                metric_name = parts[0].split('{')[0]  # Remove labels
                value = parts[1]
        
        # Remove duplicates and sort
        counters = sorted(set(counters))
        gauges = sorted(set(gauges))
        histograms = sorted(set(histograms))
        
        print("=" * 60)
        print("METRICS SUMMARY")
        print("=" * 60)
        print(f"\n📊 COUNTERS ({len(counters)}):")
        for metric in counters:
            print(f"   - {metric}")
        
        print(f"\n📈 GAUGES ({len(gauges)}):")
        for metric in gauges:
            print(f"   - {metric}")
        
        print(f"\n📉 HISTOGRAMS ({len(histograms)}):")
        for metric in histograms:
            print(f"   - {metric}")
        
        # Check for specific metrics
        print("\n" + "=" * 60)
        print("CHECKING FOR KEY METRICS")
        print("=" * 60)
        
        key_metrics = {
            'llm_cost_total': 'llm.cost.total',
            'policy_violations_total': 'policy.violations.total',
            'workflow_runs': 'workflow.runs',
            'workflow_success': 'workflow.success',
        }
        
        all_metrics = counters + gauges + histograms
        found = {}
        missing = {}
        
        for prom_name, internal_name in key_metrics.items():
            if prom_name in all_metrics:
                found[prom_name] = internal_name
            else:
                missing[prom_name] = internal_name
        
        if found:
            print("\n✅ FOUND:")
            for prom_name, internal_name in found.items():
                print(f"   {prom_name} (from {internal_name})")
        
        if missing:
            print("\n❌ MISSING:")
            for prom_name, internal_name in missing.items():
                print(f"   {prom_name} (expected from {internal_name})")
            print("\n💡 These metrics will appear after workflows run and record data.")
        
        # Show raw output for debugging
        print("\n" + "=" * 60)
        print("RAW METRICS OUTPUT (first 50 lines)")
        print("=" * 60)
        for i, line in enumerate(lines[:50], 1):
            print(f"{i:3}: {line}")
        
        if len(lines) > 50:
            print(f"\n... ({len(lines) - 50} more lines)")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {url}")
        print("   Make sure TaskPilot is running in server mode:")
        print("   python main.py --server --port 8000")
        return False
    except Exception as e:
        print(f"❌ Error checking metrics: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Check metrics endpoint")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    args = parser.parse_args()
    
    success = check_metrics_endpoint(args.port)
    sys.exit(0 if success else 1)
