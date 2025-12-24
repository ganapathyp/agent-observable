# TaskPilot Documentation

TaskPilot is an **example implementation** demonstrating how to use the `agent-observable-core` library.

## Library Documentation

**For library documentation (metrics, traces, policy decisions, etc.), see:**
- **[agent-observable-core README](../../../libraries/agent-observable-core/README.md)** - Library overview
- **[Auto-Enabled Observability](../../../libraries/agent-observable-core/docs/AUTO_ENABLED_OBSERVABILITY.md)** - What's automatically tracked
- **[Metrics Reference](../../../libraries/agent-observable-core/docs/METRICS.md)** - All metrics
- **[Traces Reference](../../../libraries/agent-observable-core/docs/TRACES.md)** - Distributed tracing
- **[Policy Decisions](../../../libraries/agent-observable-core/docs/POLICY_DECISIONS.md)** - Policy decision logging
- **[Docker Tools Integration](../../../libraries/agent-observable-core/docs/DOCKER_TOOLS.md)** - Viewing data in tools

## TaskPilot-Specific Documentation

### Core Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and design
- **[USING_THE_LIBRARY.md](USING_THE_LIBRARY.md)** - How to use agent-observable-core library
- **[RUN_INSTRUCTIONS.md](RUN_INSTRUCTIONS.md)** - How to run TaskPilot
- **[OBSERVABILITY_TOOLS_WALKTHROUGH.md](OBSERVABILITY_TOOLS_WALKTHROUGH.md)** - Using observability tools with TaskPilot

### Configuration & Operations

- **[CONFIGURATION.md](CONFIGURATION.md)** - TaskPilot configuration
- **[COST_TRACKING_GUIDE.md](COST_TRACKING_GUIDE.md)** - LLM cost tracking guide
- **[TESTING.md](TESTING.md)** - Testing instructions
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and fixes

### Deep Dives

See `details/` subdirectory for detailed documentation:
- **[details/LLM_PRODUCTION_GUIDE.md](details/LLM_PRODUCTION_GUIDE.md)** - LLM production best practices
- **[details/CAPABILITIES_MATRIX.md](details/CAPABILITIES_MATRIX.md)** - Capabilities analysis
- **[details/DESIGN.md](details/DESIGN.md)** - Detailed design document

## Quick Links

- **Run TaskPilot:** `python main.py`
- **View Metrics:** http://localhost:9090 (Prometheus)
- **View Traces:** http://localhost:16686 (Jaeger)
- **View Logs:** http://localhost:5601 (Kibana)
- **View Dashboards:** http://localhost:3000 (Grafana)

## Archived Documentation

Historical, tactical, and redundant documentation has been moved to the `archive/` directory. See `archive/ARCHIVE_README.md` for details.
