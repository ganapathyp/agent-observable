"""Health check endpoint/CLI."""
import json
import sys
from taskpilot.core.observability import get_health_checker, get_metrics_collector, get_error_tracker  # type: ignore
from taskpilot.core.task_store import get_task_store  # type: ignore

def main():
    """Run health checks and output results."""
    import argparse
    
    parser = argparse.ArgumentParser(description="TaskPilot health check")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--metrics", action="store_true", help="Show metrics")
    parser.add_argument("--errors", action="store_true", help="Show error summary")
    
    args = parser.parse_args()
    
    # Initialize health checks (same as main.py)
    health_checker = get_health_checker()
    
    def check_task_store():
        """Check task store health."""
        try:
            store = get_task_store()
            stats = store.get_stats()
            return True, "Task store operational", {"stats": stats}
        except Exception as e:
            return False, f"Task store error: {str(e)}", {}
    
    def check_guardrails():
        """Check guardrails health."""
        try:
            from taskpilot.core.guardrails.nemo_rails import NeMoGuardrailsWrapper
            from pathlib import Path
            # Try to get guardrails instance
            taskpilot_dir = Path(__file__).parent.parent
            config_path = taskpilot_dir / "guardrails" / "config.yml"
            guardrails = NeMoGuardrailsWrapper(config_path=config_path if config_path.exists() else None)
            # Disabled guardrails is degraded but not unhealthy (graceful degradation)
            if guardrails._enabled:
                return True, "Guardrails available", {}
            else:
                return True, "Guardrails disabled (graceful degradation)", {"status": "degraded"}
        except Exception as e:
            return False, f"Guardrails error: {str(e)}", {}
    
    health_checker.register_check("task_store", check_task_store)
    health_checker.register_check("guardrails", check_guardrails)
    
    # Run health checks
    health_status = health_checker.check_health()
    
    if args.json:
        output = health_status.to_dict()
        if args.metrics:
            output["metrics"] = get_metrics_collector().get_all_metrics()
        if args.errors:
            output["errors"] = get_error_tracker().get_error_summary()
        print(json.dumps(output, indent=2))
        sys.exit(0 if health_status.status == "healthy" else 1)
    else:
        # Human-readable output
        print(f"\n🏥 Health Check: {health_status.status.upper()}")
        print("=" * 60)
        
        for name, check in health_status.checks.items():
            status_emoji = "✅" if check["status"] == "healthy" else "❌"
            print(f"{status_emoji} {name}: {check['status']}")
            if check.get("message"):
                print(f"   {check['message']}")
        
        if args.metrics:
            print("\n📊 Metrics:")
            print("=" * 60)
            metrics = get_metrics_collector().get_all_metrics()
            if metrics["counters"]:
                print("\nCounters:")
                for name, value in metrics["counters"].items():
                    print(f"  {name}: {value}")
            if metrics["gauges"]:
                print("\nGauges:")
                for name, value in metrics["gauges"].items():
                    print(f"  {name}: {value}")
            if metrics["histograms"]:
                print("\nHistograms:")
                for name, stats in metrics["histograms"].items():
                    print(f"  {name}:")
                    print(f"    count: {stats['count']}")
                    print(f"    avg: {stats['avg']:.2f}ms")
                    print(f"    p95: {stats['p95']:.2f}ms")
        
        if args.errors:
            print("\n⚠️  Error Summary:")
            print("=" * 60)
            error_summary = get_error_tracker().get_error_summary()
            print(f"Total errors: {error_summary['total_errors']}")
            if error_summary["error_counts"]:
                print("\nError counts:")
                for error_key, count in list(error_summary["error_counts"].items())[:10]:
                    print(f"  {error_key}: {count}")
        
        sys.exit(0 if health_status.status == "healthy" else 1)

if __name__ == "__main__":
    main()
