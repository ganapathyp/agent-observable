#!/usr/bin/env python3
"""CLI tool to view LLM cost tracking metrics."""
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from taskpilot.core.cost_viewer import create_cost_viewer
from taskpilot.core.observable import get_metrics


def main():
    parser = argparse.ArgumentParser(description="View LLM cost tracking metrics")
    parser.add_argument(
        "--format",
        choices=["text", "json", "csv"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--endpoint",
        action="store_true",
        help="Fetch from API endpoint instead of local metrics"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for API endpoint (default: 8000)"
    )
    
    args = parser.parse_args()
    
    if args.endpoint:
        # Fetch from API
        import requests
        try:
            url = f"http://localhost:{args.port}/cost-report"
            response = requests.get(url, params={"format": args.format}, timeout=5)
            response.raise_for_status()
            print(response.text)
        except requests.exceptions.ConnectionError:
            print(f"Error: Could not connect to server at http://localhost:{args.port}")
            print("Make sure TaskPilot server is running: python main.py --server --port 8000")
            sys.exit(1)
        except Exception as e:
            print(f"Error fetching cost report: {e}")
            sys.exit(1)
    else:
        # Use local metrics
        try:
            metrics = get_metrics()
            viewer = create_cost_viewer(metrics_collector=metrics)
            report = viewer.get_cost_report(format=args.format)
            print(report)
        except Exception as e:
            print(f"Error generating cost report: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
