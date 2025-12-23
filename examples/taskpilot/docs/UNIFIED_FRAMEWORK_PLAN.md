# Unified Agent Framework with Built-in Observability & Safety

## Vision

Create a **single, drop-in framework** that developers can use to build agentic applications **with ANY agent/workflow system**. Developers focus **only** on:
- **Workflow definition** (agent chains, conditions, edges, role-routing tables, custom workflows)
- **Agent creation** (instructions, tools, models)

**Framework-Agnostic**: Works with Microsoft Agent Framework, LangGraph, custom role-routing tables, table-based workflows, or any agent system.

Everything else is **automatic**:
- ✅ Metrics collection
- ✅ Distributed tracing
- ✅ Structured logging
- ✅ Policy decisions (unified):
  - OPA tool call validation decisions
  - NeMo Guardrails input/output validation decisions
  - Human review/reject/accept decisions
- ✅ Error tracking
- ✅ Health checks
- ✅ Cost tracking

**Zero configuration required** - works out of the box with sensible defaults.

---

## Developer Experience (Target State)

### Before (Current State)

```python
# main.py - 500+ lines of setup
from taskpilot.core.otel_integration import initialize_opentelemetry
from taskpilot.core.observability import get_metrics_collector, get_tracer
from taskpilot.core.guardrails.decision_logger import get_decision_logger
# ... 20+ imports

# Initialize OpenTelemetry
otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
initialize_opentelemetry(service_name="taskpilot", otlp_endpoint=otlp_endpoint, enabled=True)

# Configure logging
log_dir = paths.logs_dir
log_dir.mkdir(parents=True, exist_ok=True)
# ... 50+ lines of logging setup

# Create agents
planner = create_planner()
reviewer = create_reviewer()
executor = create_executor()

# Set middleware (must do for each agent)
planner.middleware = create_audit_and_policy_middleware(planner.name)
reviewer.middleware = create_audit_and_policy_middleware(reviewer.name)
executor.middleware = create_audit_and_policy_middleware(executor.name)

# Build workflow
workflow = build_workflow(planner, reviewer, executor)

# Run with manual observability
with RequestContext() as req_ctx:
    with TraceContext(name="workflow.run", request_id=req_ctx.request_id):
        metrics.increment_counter("workflow.runs")
        # ... run workflow
```

**Problems**:
- ❌ 50+ lines of setup code
- ❌ Must manually configure observability
- ❌ Must manually attach middleware to each agent
- ❌ Must manually track metrics/traces
- ❌ Tightly coupled to taskpilot structure

---

### After (Target State)

```python
# main.py - 20 lines total
from agent_framework_observable import AgentFramework

# Create framework (auto-configures everything)
framework = AgentFramework(
    service_name="my_agent_app",
    # Optional: customize if needed
    observability_enabled=True,
    guardrails_enabled=True,
    policy_enabled=True
)

# Example 1: Microsoft Agent Framework (auto-detected)
from agent_framework import OpenAIChatClient

ms_agent = OpenAIChatClient(...).create_agent(...)
planner = framework.wrap_agent(
    agent=ms_agent,
    name="PlannerAgent",
    prompt="planner"  # Loads from prompts/planner.yaml (versioned, validated)
)

# Example 2: Custom Role-Routing Table
routing_table = {
    "planner": {"handler": planner_handler, "prompt": "planner"},
    "reviewer": {"handler": reviewer_handler, "prompt": "reviewer"}
}

# Framework automatically wraps all handlers
for role, config in routing_table.items():
    config["handler"] = framework.wrap_handler(
        handler=config["handler"],
        name=role,
        prompt=config["prompt"]
    )

# Example 3: Table-Based Workflow
workflow_table = [
    {"step": 1, "agent": "planner", "prompt": "planner"},
    {"step": 2, "agent": "reviewer", "prompt": "reviewer", "condition": "if_approved"},
    {"step": 3, "agent": "executor", "prompt": "executor", "condition": "if_approved"}
]

workflow = framework.build_table_workflow(
    workflow_table=workflow_table,
    handlers={"planner": planner_handler, "reviewer": reviewer_handler, "executor": executor_handler}
)

# Run workflow (everything tracked automatically)
result = await workflow(user_input="Create high priority task")

# That's it! Metrics, traces, logs, policy decisions (OPA + Guardrails + Human Review) all automatic
# Works with ANY agent/workflow system - no MS Agent Framework or LangGraph required!
```

**Benefits**:
- ✅ **20 lines** instead of 500+
- ✅ **Zero manual observability code**
- ✅ **Automatic middleware** on all agents
- ✅ **Automatic metrics/traces** for all operations
- ✅ **Framework handles everything**

---

## Framework-Agnostic Architecture

### Key Design: Adapter Pattern

The unified framework uses an **adapter pattern** to work with any agent/workflow system:

1. **Abstract Interfaces**: Define framework-agnostic interfaces
2. **Adapters**: Bridge to specific frameworks (MS Agent Framework, LangGraph, custom)
3. **Auto-Detection**: Automatically detects which framework is being used
4. **Non-Invasive**: Wraps existing agents/workflows without modification

**See [FRAMEWORK_AGNOSTIC_DESIGN.md](FRAMEWORK_AGNOSTIC_DESIGN.md) for complete design details.**

### Supported Frameworks

- ✅ **Microsoft Agent Framework** (current implementation)
- ✅ **LangGraph** (via adapter)
- ✅ **Custom Role-Routing Tables** (via adapter)
- ✅ **Table-Based Workflows** (via adapter)
- ✅ **Any Custom Agent System** (via generic adapter)

---

## Architecture Overview

### Framework Structure

```
agent_framework_observable/
├── __init__.py
├── framework.py              # Main AgentFramework class
├── config/
│   ├── __init__.py
│   ├── defaults.py           # Sensible defaults (zero config)
│   └── config.py            # Configuration dataclasses
├── observability/
│   ├── __init__.py
│   ├── auto_instrument.py   # Automatic instrumentation
│   ├── metrics.py           # Metrics collector (no app deps)
│   ├── tracing.py           # Tracer (no app deps)
│   ├── logging.py           # Structured logger (no app deps)
│   └── decorators.py        # @observable decorator
├── guardrails/
│   ├── __init__.py
│   ├── auto_guard.py        # Automatic guardrails
│   ├── nemo_wrapper.py      # NeMo Guardrails (no app deps)
│   └── opa_validator.py     # OPA validator (no app deps)
├── prompts/
│   ├── __init__.py
│   ├── manager.py           # Prompt manager (load, version, validate)
│   ├── loader.py            # Prompt file loader (YAML/JSON)
│   ├── validator.py         # Prompt validator (NeMo Guardrails)
│   └── versioning.py        # Prompt versioning system
├── policy/
│   ├── __init__.py
│   ├── auto_policy.py       # Automatic policy decisions (unified)
│   ├── decision_logger.py   # Unified decision logger (OPA + Guardrails + Human Review)
│   ├── opa_embedded.py      # Embedded OPA (tool call validation)
│   ├── guardrails_policy.py # NeMo Guardrails as policy decisions
│   └── human_review.py      # Human review/reject/accept decisions
└── middleware/
    ├── __init__.py
    └── unified_middleware.py # Single middleware for all concerns
```

---

## Core Design Principles

### 1. **Zero Configuration by Default**

Framework works out-of-the-box with sensible defaults:

```python
# Minimal usage - everything automatic
framework = AgentFramework()
agent = framework.create_agent(name="MyAgent", instructions="...")
workflow = framework.build_workflow(...)
await framework.run(workflow, input="...")
```

**Defaults**:
- Metrics: In-memory (can export to Prometheus if endpoint configured)
- Traces: OpenTelemetry (auto-detects OTLP endpoint or uses file)
- Logs: Structured JSON to stdout (can configure file path)
- Guardrails: Enabled if NeMo Guardrails installed, graceful degradation
- Policy: Enabled if OPA policies found, graceful degradation

### 2. **Automatic Instrumentation**

Framework automatically:
- ✅ Loads prompts from external files (versioned)
- ✅ Validates prompts with NeMo Guardrails (before use)
- ✅ Instruments all agent executions (metrics, traces, logs)
- ✅ Validates tool calls (OPA policy decisions, metrics)
- ✅ Validates input/output (NeMo Guardrails policy decisions)
- ✅ Handles human reviews (review/reject/accept policy decisions)
- ✅ Tracks workflow runs (traces, metrics)
- ✅ Tracks errors (error tracking, logs)

**No manual code required** - happens transparently.

### 3. **Dependency Injection (Not Globals)**

Framework uses dependency injection, not global singletons:

```python
# Framework creates and manages all instances
framework = AgentFramework()
# Internally:
# - Creates MetricsCollector instance
# - Creates Tracer instance
# - Creates DecisionLogger instance
# - Injects into middleware
# - No globals, no module-level state
```

### 4. **Aspect-Oriented by Default**

All cross-cutting concerns handled via aspects:

```python
# Framework automatically wraps agent execution
@framework.observable  # Applied automatically
async def agent_execute(context):
    # Only business logic here
    return await agent.run(context)
```

### 5. **Composable & Extensible**

Framework allows customization without breaking defaults:

```python
# Customize specific aspects
framework = AgentFramework(
    observability=ObservabilityConfig(
        metrics_enabled=True,
        tracing_enabled=True,
        logging_enabled=True
    ),
    prompts=PromptConfig(
        enabled=True,
        prompts_dir="./prompts",
        validate_with_guardrails=True,
        version_strategy="latest"
    ),
    policy=PolicyConfig(
        enabled=True,
        opa_enabled=True,
        opa_policies_path="./policies",
        nemo_enabled=True,
        nemo_config_path="./guardrails",
        human_review_enabled=True
    )
)
```

---

## Policy Decision Unification

### Unified Decision Types

All policy decisions use the same structure and are logged to the same system:

```python
@dataclass
class PolicyDecision:
    decision_id: str
    timestamp: datetime
    decision_type: DecisionType  # tool_call, guardrails_input, guardrails_output, human_approval
    result: DecisionResult  # allow, deny, require_approval
    reason: str
    context: Dict[str, Any]
    # ... other fields
```

**Decision Types**:
- `tool_call`: OPA tool call validation
- `guardrails_input`: NeMo Guardrails input validation
- `guardrails_output`: NeMo Guardrails output validation
- `guardrails_prompt`: NeMo Guardrails prompt validation (NEW)
- `human_approval`: Human review/reject/accept decisions

**Benefits**:
- ✅ Single query interface: `log_type: "policy_decision"`
- ✅ Consistent structure across all decision types
- ✅ Easy filtering: `decision_type: "tool_call"` or `decision_type: "human_approval"`
- ✅ Unified audit trail

---

## Detailed Component Design

### 1. AgentFramework (Main Class)

**Purpose**: Single entry point for all framework functionality.

**Responsibilities**:
- Agent creation with automatic instrumentation
- Workflow building with automatic observability
- Configuration management
- Lifecycle management (startup, shutdown)

**API**:
```python
class AgentFramework:
    def __init__(
        self,
        service_name: str = "agent_app",
        config: Optional[FrameworkConfig] = None
    ):
        """Create framework with automatic observability."""
    
    def create_agent(
        self,
        name: str,
        prompt: Union[str, Path],  # Prompt name or path
        tools: Optional[List] = None,
        model: Optional[str] = None,
        prompt_version: Optional[str] = None  # Optional: specific version
    ) -> Agent:
        """Create agent with automatic prompt loading, validation, and middleware.
        
        Args:
            name: Agent name
            prompt: Prompt identifier (e.g., "planner") or path to prompt file
            tools: Optional list of tools
            model: Optional model override
            prompt_version: Optional specific prompt version (defaults to latest)
        
        Returns:
            Agent with prompt loaded, validated, and middleware attached
        """
    
    def wrap_workflow(
        self,
        workflow: Any,  # Framework-specific workflow (any type)
        workflow_type: Optional[str] = None  # "ms_agent", "langgraph", "table", "custom"
    ) -> Any:
        """Wrap framework-specific workflow with observability.
        
        Works with ANY workflow system:
        - Microsoft Agent Framework workflows
        - LangGraph workflows
        - Table-based workflows
        - Custom workflow implementations
        
        Args:
            workflow: Framework-specific workflow (any type)
            workflow_type: Optional workflow type (auto-detected if None)
        
        Returns:
            Wrapped workflow (same type as input, but with observability)
        """
    
    def build_table_workflow(
        self,
        workflow_table: List[Dict],  # Table-based workflow definition
        handlers: Dict[str, Callable]  # Handler functions for each step
    ) -> Callable:
        """Build table-based workflow with automatic observability.
        
        Example workflow_table:
        [
            {"step": 1, "agent": "planner", "prompt": "planner"},
            {"step": 2, "agent": "reviewer", "prompt": "reviewer", "condition": "if_approved"},
            {"step": 3, "agent": "executor", "prompt": "executor", "condition": "if_approved"}
        ]
        
        Returns:
            Workflow function with automatic observability
        """
    
    async def run(
        self,
        workflow: Workflow,
        input: str,
        context: Optional[Dict] = None
    ) -> Any:
        """Run workflow with automatic metrics, traces, logs."""
    
    def configure(
        self,
        observability: Optional[ObservabilityConfig] = None,
        guardrails: Optional[GuardrailsConfig] = None,
        policy: Optional[PolicyConfig] = None
    ):
        """Configure framework components."""
```

**Key Features**:
- Automatically attaches middleware to all agents
- Automatically creates request context for correlation
- Automatically starts/ends traces
- Automatically records metrics
- Automatically logs all operations

---

### 2. Unified Policy Decision System

**Purpose**: Single system that handles all policy decisions uniformly.

**Policy Decision Types**:
1. **OPA Tool Call Validation** (`decision_type: "tool_call"`)
   - Validates tool calls before execution
   - Results: `allow`, `deny`, `require_approval`
   - Logged to unified decision logger

2. **NeMo Guardrails Validation** (`decision_type: "guardrails_input"` / `"guardrails_output"`)
   - Validates LLM input/output for safety
   - Results: `allow`, `deny`
   - Logged to unified decision logger

3. **Human Review Decisions** (`decision_type: "human_approval"`)
   - Review/reject/accept decisions
   - Results: `allow` (accept), `deny` (reject), `require_approval` (review)
   - Logged to unified decision logger

**Benefits**:
- ✅ Single decision logger for all policy types
- ✅ Consistent audit trail
- ✅ Unified querying in Kibana/Elasticsearch
- ✅ Same data structure for all decisions

### 3. Unified Middleware

**Purpose**: Single middleware that handles all cross-cutting concerns.

**Responsibilities**:
- Metrics collection
- Distributed tracing
- Structured logging
- Policy decisions (unified - OPA + Guardrails + Human Review)
- Error tracking
- Cost tracking

**Design**:
```python
class UnifiedMiddleware:
    def __init__(
        self,
        observability: ObservabilityAspect,
        guardrails: GuardrailsAspect,
        policy: PolicyAspect
    ):
        """Create unified middleware with all aspects."""
    
    async def __call__(
        self,
        context: AgentRunContext,
        next: Callable
    ) -> None:
        """Execute middleware chain."""
        # 1. Start trace
        # 2. Record metrics (invocations)
        # 3. Load and validate prompt (if not cached) → Log policy decision if validation fails
        # 4. Validate input (NeMo Guardrails) → Log policy decision
        # 5. Log input
        # 6. Execute agent (next())
        # 7. Validate tool calls (OPA) → Log policy decision
        # 8. Validate output (NeMo Guardrails) → Log policy decision
        # 9. Handle human review (if applicable) → Log policy decision
        # 10. Log output
        # 11. Record metrics (latency, success/error)
        # 12. Track costs
        # 13. End trace
```

**Benefits**:
- Single middleware instead of multiple
- Consistent execution order
- Easy to enable/disable aspects
- Composable design

---

### 4. Automatic Instrumentation

**Purpose**: Automatically instrument agents, tools, and workflows.

**How It Works**:

1. **Agent Creation**:
   ```python
   agent = framework.create_agent(...)
   # Framework automatically:
   # - Wraps agent.run() with middleware
   # - Adds metrics collection
   # - Adds tracing
   # - Adds logging
   ```

2. **Tool Calls**:
   ```python
   @framework.tool  # Decorator auto-instruments
   def create_task(title: str):
       # Framework automatically:
       # - Validates with OPA
       # - Logs OPA policy decision (allow/deny/require_approval)
       # - Records metrics
       # - Traces execution
   ```

3. **Guardrails Validation**:
   ```python
   # Framework automatically validates input/output
   # - NeMo Guardrails input validation → Log policy decision
   # - NeMo Guardrails output validation → Log policy decision
   # All logged to unified decision logger
   ```

4. **Human Review**:
   ```python
   # Framework automatically handles review workflows
   # - Review decision → Log policy decision (human_approval)
   # - Reject decision → Log policy decision (human_approval, deny)
   # - Accept decision → Log policy decision (human_approval, allow)
   ```

5. **Workflow Execution**:
   ```python
   await framework.run(workflow, input="...")
   # Framework automatically:
   # - Creates root trace span
   # - Records workflow metrics
   # - Correlates all operations
   # - Logs workflow execution
   ```

---

### 5. Configuration Abstraction

**Purpose**: Clean configuration without hard-coded paths or names.

**Design**:
```python
@dataclass
class FrameworkConfig:
    """Framework configuration."""
    service_name: str = "agent_app"
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    guardrails: GuardrailsConfig = field(default_factory=GuardrailsConfig)
    policy: PolicyConfig = field(default_factory=PolicyConfig)

@dataclass
class ObservabilityConfig:
    """Observability configuration."""
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    logging_enabled: bool = True
    metrics_file: Optional[Path] = None  # None = in-memory
    otlp_endpoint: Optional[str] = None  # None = auto-detect or file
    log_file: Optional[Path] = None  # None = stdout

@dataclass
class GuardrailsConfig:
    """Guardrails configuration."""
    nemo_enabled: bool = True
    nemo_config_path: Optional[Path] = None
    opa_enabled: bool = True
    opa_policies_path: Optional[Path] = None

@dataclass
class PolicyConfig:
    """Policy configuration."""
    enabled: bool = True
    decision_log_file: Optional[Path] = None  # None = in-memory
    opa_policies_path: Optional[Path] = None
```

**Benefits**:
- No hard-coded paths
- No environment variable access in library code
- Easy to test (inject config)
- Easy to customize

---

### 6. Zero Dependencies on Application

**Key Principle**: Framework has **zero knowledge** of application structure.

**What Framework Does**:
- ✅ Accepts configuration via constructor
- ✅ Uses dependency injection
- ✅ No hard-coded paths
- ✅ No application-specific imports
- ✅ No global state

**What Framework Doesn't Do**:
- ❌ Access environment variables directly
- ❌ Assume directory structure
- ❌ Import application-specific modules
- ❌ Use global singletons

**Example**:
```python
# Framework code (no app dependencies)
class MetricsCollector:
    def __init__(self, config: MetricsConfig):
        self.config = config  # Injected, not from env vars
        # No hard-coded paths
        # No application imports
```

---

## Migration Strategy

### Phase 1: Extract Core Libraries (No Breaking Changes)

1. **Create `agent_framework_observable/` package**
   - Extract observability code (remove app dependencies)
   - Extract guardrails code (remove app dependencies)
   - Extract policy code (remove app dependencies)
   - Keep existing code working (parallel implementation)

2. **Create `AgentFramework` class**
   - Implement automatic instrumentation
   - Implement unified middleware
   - Implement configuration abstraction

3. **Test alongside existing code**
   - Framework works independently
   - Existing code continues to work
   - No breaking changes

### Phase 2: Create Adapter Layer

1. **Create adapter for existing code**
   ```python
   # taskpilot/framework_adapter.py
   from agent_framework_observable import AgentFramework
   
   def create_taskpilot_framework():
       """Create framework configured for taskpilot."""
       return AgentFramework(
           service_name="taskpilot",
           config=load_taskpilot_config()
       )
   ```

2. **Migrate one component at a time**
   - Start with new features using framework
   - Gradually migrate existing code
   - Keep backward compatibility

### Phase 3: Complete Migration

1. **Replace all manual observability code**
   - Use framework for all agents
   - Remove manual middleware setup
   - Remove manual metrics/traces

2. **Remove old implementations**
   - Delete old observability code
   - Delete old middleware code
   - Update all imports

---

## Benefits Summary

### For Developers

✅ **Minimal Code**: 20 lines instead of 500+
✅ **Zero Configuration**: Works out of the box
✅ **Automatic Everything**: Metrics, traces, logs, prompts, policy, guardrails
✅ **Externalized Prompts**: Versioned, validated prompts (no code changes)
✅ **Focus on Business Logic**: Only write agents and workflows

### For Reusability

✅ **Drop-in Library**: Copy `agent_framework_observable/` to any project
✅ **Zero Dependencies**: No application-specific code
✅ **Dependency Injection**: Easy to test and customize
✅ **Composable**: Enable/disable features as needed

### For Maintainability

✅ **Single Source of Truth**: One framework, not scattered code
✅ **Consistent Behavior**: All agents get same observability
✅ **Easy to Update**: Update framework, all apps benefit
✅ **Clear Boundaries**: Framework vs. application code

---

## Comparison: Current vs. Proposed

| Aspect | Current | Proposed |
|--------|---------|----------|
| **Setup Code** | 500+ lines | 20 lines |
| **Configuration** | Scattered, hard-coded | Centralized, injected |
| **Middleware** | Manual per agent | Automatic |
| **Observability** | Manual calls | Automatic |
| **Dependencies** | Tight coupling | Zero coupling |
| **Reusability** | 3/10 | 10/10 |
| **Developer Focus** | Setup + Logic | Logic only |

---

## Implementation Phases

### Phase 1: Foundation (2-3 weeks)
- Extract observability library (no app deps)
- Extract guardrails library (no app deps)
- Extract policy library (no app deps)
- Create configuration abstraction

### Phase 2: Framework Core (2-3 weeks)
- Create `AgentFramework` class
- Implement unified middleware
- Implement automatic instrumentation
- Create decorators for tools

### Phase 3: Integration (1-2 weeks)
- Create adapter for existing code
- Migrate one component
- Test end-to-end
- Document usage

### Phase 4: Complete Migration (2-3 weeks)
- Migrate all components
- Remove old code
- Update documentation
- Create examples

**Total**: 7-11 weeks

---

## Next Steps

1. **Review this plan** - Does this match your vision?
2. **Prioritize phases** - Which phase is most important?
3. **Clarify requirements** - Any missing features?
4. **Start implementation** - Begin with Phase 1 (extract libraries)

---

## Questions to Consider

1. **Framework Agnosticism**: 
   - ✅ **Critical**: Must work without MS Agent Framework or LangGraph
   - ✅ **Solution**: Adapter pattern with abstract interfaces
   - ✅ **Priority**: High - required for enterprise reuse

2. **Configuration**: Should framework auto-detect everything, or require explicit config?
3. **Backward Compatibility**: How long should we maintain old code?
4. **Feature Flags**: Should all features be optional, or some always enabled?
5. **Error Handling**: How should framework handle missing dependencies (NeMo, OPA)?
6. **Performance**: Should framework be async-first, or support sync too?
7. **Prompt Validation**: Should prompt validation failures block agent creation, or just log?
8. **Prompt Versioning**: Should versioning be file-based or database-backed?
9. **Prompt Caching**: How long should prompts be cached? When to invalidate?
10. **Adapter Complexity**: How much framework-specific logic in adapters vs. core?

---

## Conclusion

This unified framework approach provides:
- ✅ **True reusability**: Drop-in library for any project, any framework
- ✅ **Framework-agnostic**: Works with MS Agent Framework, LangGraph, custom systems, role-routing tables
- ✅ **Developer experience**: Focus on business logic only
- ✅ **Automatic observability**: Zero manual code
- ✅ **Clean architecture**: Dependency injection, no globals, adapter pattern
- ✅ **Maintainability**: Single source of truth
- ✅ **Enterprise-ready**: One library for entire company, regardless of framework choice

**The framework becomes the "batteries included" solution for agentic applications - framework-agnostic and truly reusable.**

**See [FRAMEWORK_AGNOSTIC_DESIGN.md](FRAMEWORK_AGNOSTIC_DESIGN.md) for detailed design of adapter pattern and framework-agnostic architecture.**
