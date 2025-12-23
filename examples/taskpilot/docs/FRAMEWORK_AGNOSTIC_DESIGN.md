# Framework-Agnostic Design Analysis

## Current Dependencies Analysis

### Microsoft Agent Framework Dependencies

**Current code depends on**:
```python
from agent_framework import AgentRunContext, TextContent
from agent_framework import WorkflowBuilder, FunctionExecutor
```

**What MS Agent Framework Provides**:
1. `AgentRunContext` - Context object passed to middleware
2. `WorkflowBuilder` - Workflow construction API
3. `FunctionExecutor` - Tool execution wrapper
4. Agent interface (`.run()`, `.middleware` attribute)

### Critical Question

**Can the unified framework work WITHOUT Microsoft Agent Framework?**

**Answer**: **YES**, but requires **abstraction layer**.

---

## Framework-Agnostic Design Requirements

### Goal

Create a **framework-agnostic observability library** that works with:
- ✅ Microsoft Agent Framework
- ✅ LangGraph
- ✅ Custom agent systems
- ✅ Role-routing tables
- ✅ Table-based workflows
- ✅ Any agent/workflow implementation

### Key Principle: **Abstraction Over Implementation**

Framework should define **interfaces**, not depend on specific implementations.

---

## Abstraction Layer Design

### 1. Agent Execution Interface

**Problem**: Different frameworks have different agent interfaces.

**Solution**: Define abstract interface that all frameworks implement.

```python
# Framework-agnostic interface
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, Awaitable

class AgentExecutionContext(ABC):
    """Abstract context for agent execution."""
    
    @property
    @abstractmethod
    def request_id(self) -> Optional[str]:
        """Get request ID for correlation."""
        pass
    
    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Get agent name."""
        pass
    
    @property
    @abstractmethod
    def input_text(self) -> Optional[str]:
        """Get input text."""
        pass
    
    @property
    @abstractmethod
    def result(self) -> Any:
        """Get execution result."""
        pass
    
    @result.setter
    @abstractmethod
    def result(self, value: Any) -> None:
        """Set execution result."""
        pass
    
    @property
    @abstractmethod
    def messages(self) -> list:
        """Get messages (if available)."""
        pass
    
    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Get additional metadata."""
        pass

class AgentInterface(ABC):
    """Abstract agent interface."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name."""
        pass
    
    @abstractmethod
    async def run(
        self,
        context: AgentExecutionContext,
        **kwargs
    ) -> Any:
        """Execute agent."""
        pass

class MiddlewareInterface(ABC):
    """Abstract middleware interface."""
    
    @abstractmethod
    async def __call__(
        self,
        context: AgentExecutionContext,
        next: Callable[[AgentExecutionContext], Awaitable[Any]]
    ) -> Any:
        """Execute middleware."""
        pass
```

### 2. Adapter Pattern for Different Frameworks

**Solution**: Create adapters that bridge framework-specific code to our interfaces.

#### Microsoft Agent Framework Adapter

```python
# adapters/ms_agent_framework.py
from agent_framework import AgentRunContext as MSContext
from agent_framework_observable import AgentExecutionContext, AgentInterface

class MSAgentFrameworkAdapter:
    """Adapter for Microsoft Agent Framework."""
    
    @staticmethod
    def adapt_context(ms_context: MSContext) -> AgentExecutionContext:
        """Convert MS Agent Framework context to our interface."""
        return AdaptedContext(ms_context)

class AdaptedContext(AgentExecutionContext):
    """Adapter that wraps MS Agent Framework context."""
    
    def __init__(self, ms_context: MSContext):
        self._ms_context = ms_context
    
    @property
    def request_id(self) -> Optional[str]:
        # Extract from MS context
        return getattr(self._ms_context, 'request_id', None)
    
    @property
    def agent_name(self) -> str:
        # Extract from MS context
        return getattr(self._ms_context, 'agent_name', 'unknown')
    
    @property
    def input_text(self) -> Optional[str]:
        # Extract from MS context messages
        if hasattr(self._ms_context, 'messages'):
            # Extract user message
            pass
        return None
    
    # ... implement all interface methods
```

#### LangGraph Adapter

```python
# adapters/langgraph.py
from langgraph import StateGraph
from agent_framework_observable import AgentExecutionContext

class LangGraphAdapter:
    """Adapter for LangGraph."""
    
    @staticmethod
    def adapt_state(langgraph_state: dict) -> AgentExecutionContext:
        """Convert LangGraph state to our interface."""
        return LangGraphContext(langgraph_state)

class LangGraphContext(AgentExecutionContext):
    """Adapter that wraps LangGraph state."""
    
    def __init__(self, state: dict):
        self._state = state
    
    @property
    def agent_name(self) -> str:
        # Extract from LangGraph state
        return self._state.get('agent_name', 'unknown')
    
    # ... implement all interface methods
```

#### Custom Role-Routing Table Adapter

```python
# adapters/role_routing.py
from agent_framework_observable import AgentExecutionContext

class RoleRoutingAdapter:
    """Adapter for role-routing table system."""
    
    @staticmethod
    def adapt_routing_context(
        role: str,
        input_data: dict,
        routing_table: dict
    ) -> AgentExecutionContext:
        """Convert role-routing context to our interface."""
        return RoleRoutingContext(role, input_data, routing_table)

class RoleRoutingContext(AgentExecutionContext):
    """Adapter for role-routing systems."""
    
    def __init__(self, role: str, input_data: dict, routing_table: dict):
        self._role = role
        self._input_data = input_data
        self._routing_table = routing_table
    
    @property
    def agent_name(self) -> str:
        # Map role to agent name
        return self._routing_table.get(self._role, {}).get('agent_name', self._role)
    
    # ... implement all interface methods
```

---

## Framework-Agnostic Unified Framework

### Design: Plugin Architecture

```python
# agent_framework_observable/framework.py
from typing import Protocol, Optional, Type

class FrameworkAdapter(Protocol):
    """Protocol for framework adapters."""
    
    def adapt_context(self, framework_context: Any) -> AgentExecutionContext:
        """Adapt framework-specific context to our interface."""
        ...
    
    def wrap_agent(self, framework_agent: Any) -> AgentInterface:
        """Wrap framework-specific agent with our interface."""
        ...
    
    def wrap_middleware(self, middleware: MiddlewareInterface) -> Any:
        """Wrap our middleware for framework-specific use."""
        ...

class AgentFramework:
    """Framework-agnostic unified framework."""
    
    def __init__(
        self,
        service_name: str = "agent_app",
        adapter: Optional[FrameworkAdapter] = None,
        config: Optional[FrameworkConfig] = None
    ):
        """Create framework with optional adapter.
        
        Args:
            service_name: Service name for observability
            adapter: Framework adapter (auto-detects if None)
            config: Framework configuration
        """
        self.service_name = service_name
        self.config = config or FrameworkConfig()
        
        # Auto-detect framework if adapter not provided
        if adapter is None:
            adapter = self._detect_framework()
        
        self.adapter = adapter
        
        # Initialize observability (framework-agnostic)
        self.observability = ObservabilitySystem(self.config.observability)
        self.policy_system = UnifiedPolicySystem(self.config.policy)
        self.prompt_manager = PromptManager(self.config.prompts)
    
    def _detect_framework(self) -> FrameworkAdapter:
        """Auto-detect which framework is being used."""
        try:
            import agent_framework
            return MSAgentFrameworkAdapter()
        except ImportError:
            pass
        
        try:
            import langgraph
            return LangGraphAdapter()
        except ImportError:
            pass
        
        # Default: generic adapter
        return GenericAdapter()
    
    def wrap_agent(
        self,
        agent: Any,  # Framework-specific agent
        name: str,
        prompt: Optional[str] = None
    ) -> Any:
        """Wrap framework-specific agent with observability.
        
        Returns:
            Wrapped agent (same type as input, but with middleware)
        """
        # 1. Load and validate prompt
        if prompt:
            prompt_content = self.prompt_manager.load(prompt)
        else:
            prompt_content = None
        
        # 2. Create middleware
        middleware = UnifiedMiddleware(
            observability=self.observability,
            policy_system=self.policy_system
        )
        
        # 3. Wrap agent using adapter
        wrapped_agent = self.adapter.wrap_agent(
            agent=agent,
            middleware=middleware,
            prompt=prompt_content
        )
        
        return wrapped_agent
```

---

## Usage Examples

### Example 1: Microsoft Agent Framework

```python
from agent_framework_observable import AgentFramework
from agent_framework import OpenAIChatClient

# Create framework (auto-detects MS Agent Framework)
framework = AgentFramework(service_name="my_app")

# Create MS Agent Framework agent
ms_agent = OpenAIChatClient(...).create_agent(...)

# Wrap with observability (returns same type)
observable_agent = framework.wrap_agent(
    agent=ms_agent,
    name="PlannerAgent",
    prompt="planner"
)

# Use normally - observability is automatic
result = await observable_agent.run(context)
```

### Example 2: LangGraph

```python
from agent_framework_observable import AgentFramework
from langgraph import StateGraph

# Create framework (auto-detects LangGraph)
framework = AgentFramework(service_name="my_app")

# Create LangGraph workflow
workflow = StateGraph(...)

# Wrap nodes with observability
@framework.observable_node  # Decorator
async def my_node(state):
    # Business logic only
    return {"result": "..."}

# Framework automatically:
# - Creates traces
# - Records metrics
# - Validates with guardrails
# - Logs policy decisions
```

### Example 3: Custom Role-Routing Table

```python
from agent_framework_observable import AgentFramework

# Create framework with custom adapter
framework = AgentFramework(
    service_name="my_app",
    adapter=RoleRoutingAdapter()
)

# Define role-routing table
routing_table = {
    "planner": {
        "agent_name": "PlannerAgent",
        "prompt": "planner",
        "handler": planner_handler
    },
    "reviewer": {
        "agent_name": "ReviewerAgent",
        "prompt": "reviewer",
        "handler": reviewer_handler
    }
}

# Framework automatically wraps all handlers
for role, config in routing_table.items():
    config["handler"] = framework.wrap_handler(
        handler=config["handler"],
        name=config["agent_name"],
        prompt=config["prompt"]
    )

# Use routing table - observability automatic
def route(role: str, input_data: dict):
    handler = routing_table[role]["handler"]
    context = framework.create_context(role, input_data, routing_table)
    return handler(context)
```

### Example 4: Table-Based Workflow

```python
from agent_framework_observable import AgentFramework

# Create framework
framework = AgentFramework(service_name="my_app")

# Define workflow table
workflow_table = [
    {"step": 1, "agent": "planner", "prompt": "planner"},
    {"step": 2, "agent": "reviewer", "prompt": "reviewer", "condition": "if_approved"},
    {"step": 3, "agent": "executor", "prompt": "executor", "condition": "if_approved"}
]

# Framework automatically:
# - Wraps all agents
# - Creates workflow trace
# - Records workflow metrics
# - Handles conditions

result = await framework.run_table_workflow(
    workflow_table=workflow_table,
    input_data=input_data
)
```

---

## Implementation Requirements

### Phase 1: Abstraction Layer (2-3 weeks)

1. **Define Interfaces**:
   - `AgentExecutionContext` (abstract)
   - `AgentInterface` (abstract)
   - `MiddlewareInterface` (abstract)
   - `FrameworkAdapter` (protocol)

2. **Create Adapters**:
   - Microsoft Agent Framework adapter
   - LangGraph adapter
   - Generic adapter (for custom systems)

3. **Test with Multiple Frameworks**:
   - Verify works with MS Agent Framework
   - Verify works with LangGraph
   - Verify works with custom system

### Phase 2: Framework Integration (2-3 weeks)

1. **Auto-Detection**:
   - Detect which framework is installed
   - Select appropriate adapter automatically

2. **Wrapper Functions**:
   - `wrap_agent()` - Wrap any agent
   - `wrap_workflow()` - Wrap any workflow
   - `wrap_handler()` - Wrap any handler function

3. **Decorators**:
   - `@observable_agent` - Decorator for agents
   - `@observable_node` - Decorator for workflow nodes
   - `@observable_handler` - Decorator for handlers

### Phase 3: Documentation & Examples (1-2 weeks)

1. **Framework-Specific Guides**:
   - MS Agent Framework integration guide
   - LangGraph integration guide
   - Custom framework integration guide
   - Role-routing table guide
   - Table-based workflow guide

2. **Examples**:
   - Example for each supported framework
   - Migration guide from current code

---

## Key Design Decisions

### 1. **Interface-Based, Not Implementation-Based**

✅ **Do**: Define abstract interfaces
❌ **Don't**: Depend on specific framework classes

### 2. **Adapter Pattern**

✅ **Do**: Create adapters for each framework
❌ **Don't**: Hard-code framework-specific logic

### 3. **Auto-Detection with Override**

✅ **Do**: Auto-detect framework, allow manual override
❌ **Don't**: Require explicit framework selection

### 4. **Non-Invasive Wrapping**

✅ **Do**: Wrap existing agents/workflows without modification
❌ **Don't**: Require changes to existing code

### 5. **Framework-Agnostic Core**

✅ **Do**: Core observability has zero framework dependencies
❌ **Don't**: Mix framework-specific code with core

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│         Agent Framework Observable (Core)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Observability│  │    Policy    │  │   Prompts    │  │
│  │   System     │  │    System    │  │   Manager    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         │                  │                  │         │
│         └──────────────────┼──────────────────┘         │
│                            │                            │
│                    ┌───────▼────────┐                   │
│                    │ Unified        │                   │
│                    │ Middleware     │                   │
│                    └───────┬────────┘                   │
└────────────────────────────┼────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │  Adapter Layer   │
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼────────┐  ┌─────────▼────────┐  ┌─────────▼────────┐
│ MS Agent       │  │   LangGraph      │  │  Custom/Role     │
│ Framework      │  │   Adapter        │  │  Routing         │
│ Adapter        │  │                  │  │  Adapter         │
└───────┬────────┘  └─────────┬────────┘  └─────────┬────────┘
        │                     │                     │
┌───────▼────────┐  ┌─────────▼────────┐  ┌─────────▼────────┐
│ MS Agent       │  │   LangGraph      │  │  Custom Agent    │
│ Framework      │  │   Workflow      │  │  System          │
└────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## Benefits of Framework-Agnostic Design

### ✅ True Reusability

- Works with **any** agent framework
- Works with **any** workflow system
- Works with **custom** implementations

### ✅ Non-Invasive

- **No changes** to existing agent code
- **Wrap** existing agents/workflows
- **Backward compatible** with all frameworks

### ✅ Future-Proof

- New frameworks? Just add adapter
- Framework updates? Update adapter only
- Core observability unchanged

### ✅ Enterprise-Ready

- Large companies use **multiple** frameworks
- Different teams, different frameworks
- **One observability library** for all

---

## Migration Path

### For Existing MS Agent Framework Code

```python
# Before
from taskpilot.core.middleware import create_audit_and_policy_middleware
agent.middleware = create_audit_and_policy_middleware(agent.name)

# After (minimal change)
from agent_framework_observable import AgentFramework
framework = AgentFramework()
agent = framework.wrap_agent(agent, name=agent.name, prompt="planner")
```

### For Custom Systems

```python
# Before (no observability)
def my_handler(input_data):
    return process(input_data)

# After (add observability)
from agent_framework_observable import AgentFramework
framework = AgentFramework(adapter=CustomAdapter())

@framework.observable_handler
def my_handler(input_data):
    return process(input_data)  # Same code, now observable
```

---

## Conclusion

**The unified framework CAN be framework-agnostic** with:

1. ✅ **Abstraction layer** (interfaces, not implementations)
2. ✅ **Adapter pattern** (bridge to any framework)
3. ✅ **Auto-detection** (works out of the box)
4. ✅ **Non-invasive wrapping** (no code changes needed)

**Result**: **One library** works with:
- Microsoft Agent Framework
- LangGraph
- Custom role-routing tables
- Table-based workflows
- Any agent/workflow system

**This makes it truly reusable across a large company** with diverse frameworks and teams.
