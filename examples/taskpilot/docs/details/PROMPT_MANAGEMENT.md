# Prompt Management: Current State & Best Practices

## Current Implementation

**Prompts are currently hardcoded in agent files:**

### Location
- **PlannerAgent**: `src/agents/agent_planner.py` (lines 35-42)
- **ReviewerAgent**: `src/agents/agent_reviewer.py` (lines 18-24)
- **ExecutorAgent**: `src/agents/agent_executor.py` (lines 17-22)

### Current Prompts

**PlannerAgent:**
```python
instructions = """Interpret the user request and propose a task.

Use the create_task function to return structured task information.

Focus on:
- Creating clear, actionable task titles
- Assigning appropriate priority based on urgency and importance
- Providing detailed descriptions when helpful"""
```

**ReviewerAgent:**
```python
instructions = (
    "Review the proposed task for safety and compliance. "
    "Reply with exactly one of: APPROVE, REJECTED, or REVIEW.\n\n"
    "- APPROVE: Task is safe and can proceed automatically\n"
    "- REJECTED: Task is unsafe and should be rejected\n"
    "- REVIEW: Task requires human review (use only for ambiguous cases, <5% of tasks)"
)
```

**ExecutorAgent:**
```python
instructions = (
    "You receive approved task proposals. Your role is to prepare the task "
    "for execution by outputting the task details clearly. "
    "The workflow system will handle the actual execution. "
    "Simply describe the task that needs to be executed."
)
```

## Issues with Current Approach

### ❌ Problems
1. **Hard to maintain**: Prompts scattered across multiple files
2. **No versioning**: Can't track prompt changes over time
3. **No A/B testing**: Can't test different prompt variations
4. **No externalization**: Requires code changes to update prompts
5. **No templating**: Can't use variables or dynamic content
6. **No validation**: No way to validate prompt structure
7. **No documentation**: Prompts not documented separately

## Best Practices

### 1. External Prompt Files

**Recommended Structure:**
```
taskpilot/
├── prompts/
│   ├── planner.yaml
│   ├── reviewer.yaml
│   ├── executor.yaml
│   └── templates/
│       └── common.yaml
```

**YAML Format:**
```yaml
# prompts/planner.yaml
version: "1.0"
agent: PlannerAgent
system_instruction: |
  Interpret the user request and propose a task.
  
  Use the create_task function to return structured task information.
  
  Focus on:
  - Creating clear, actionable task titles
  - Assigning appropriate priority based on urgency and importance
  - Providing detailed descriptions when helpful

variables:
  - name: task_schema
    description: "JSON schema for task structure"
  
metadata:
  author: "TaskPilot Team"
  last_updated: "2025-12-21"
  tags: ["task-creation", "structured-output"]
```

### 2. Prompt Versioning

**Best Practice**: Version prompts to track changes and enable rollback

```yaml
# prompts/planner.yaml
version: "1.1"
previous_version: "1.0"
changelog:
  - version: "1.1"
    date: "2025-12-21"
    changes: "Added emphasis on priority assignment"
  - version: "1.0"
    date: "2025-12-01"
    changes: "Initial prompt"
```

### 3. Prompt Templates

**Best Practice**: Use templates for dynamic content

```yaml
# prompts/planner.yaml
system_instruction: |
  Interpret the user request and propose a task.
  
  Available priorities: {{priorities}}
  Task schema: {{task_schema}}
  
  Focus on:
  - Creating clear, actionable task titles
  - Assigning appropriate priority based on urgency and importance
  - Providing detailed descriptions when helpful
```

### 4. Centralized Prompt Manager

**Best Practice**: Create a prompt manager to load and manage prompts

```python
# src/core/prompt_manager.py
from pathlib import Path
import yaml
from typing import Dict, Optional

class PromptManager:
    """Centralized prompt management."""
    
    def __init__(self, prompts_dir: Path):
        self.prompts_dir = prompts_dir
        self._prompts: Dict[str, Dict] = {}
    
    def load_prompt(self, agent_name: str, version: Optional[str] = None) -> str:
        """Load prompt for agent."""
        # Load from YAML file
        # Support versioning
        # Support templating
        pass
    
    def get_prompt(self, agent_name: str) -> str:
        """Get current prompt for agent."""
        pass
```

### 5. Prompt Testing & A/B Testing

**Best Practice**: Support multiple prompt versions for testing

```yaml
# prompts/planner.yaml
variants:
  default:
    version: "1.0"
    system_instruction: "..."
  experimental:
    version: "1.1"
    system_instruction: "..."
    enabled: false
```

### 6. Prompt Validation

**Best Practice**: Validate prompts before use

```python
def validate_prompt(prompt: str) -> List[str]:
    """Validate prompt structure and content."""
    errors = []
    if len(prompt) < 10:
        errors.append("Prompt too short")
    if "{undefined_var}" in prompt:
        errors.append("Undefined variable in prompt")
    return errors
```

## Recommended Implementation

### Option 1: Simple YAML Files (Recommended for Start)

**Structure:**
```
taskpilot/
├── prompts/
│   ├── planner.yaml
│   ├── reviewer.yaml
│   └── executor.yaml
```

**Implementation:**
```python
# src/core/prompt_loader.py
from pathlib import Path
import yaml

def load_prompt(agent_name: str) -> str:
    """Load prompt from YAML file."""
    prompts_dir = Path(__file__).parent.parent.parent / "prompts"
    prompt_file = prompts_dir / f"{agent_name.lower().replace('agent', '')}.yaml"
    
    if not prompt_file.exists():
        # Fallback to hardcoded prompts
        return get_default_prompt(agent_name)
    
    with open(prompt_file, 'r') as f:
        data = yaml.safe_load(f)
        return data.get('system_instruction', '')
```

### Option 2: Full Prompt Management System

**Features:**
- Version control
- A/B testing
- Templating
- Validation
- Metrics tracking

**Structure:**
```
taskpilot/
├── prompts/
│   ├── agents/
│   │   ├── planner.yaml
│   │   ├── reviewer.yaml
│   │   └── executor.yaml
│   ├── templates/
│   │   └── common.yaml
│   └── versions/
│       └── planner/
│           ├── v1.0.yaml
│           └── v1.1.yaml
```

## Comparison: Current vs. Best Practice

| Aspect | Current | Best Practice |
|--------|---------|---------------|
| **Storage** | Hardcoded in Python | External YAML/JSON files |
| **Versioning** | ❌ None | ✅ Version tracking |
| **Maintainability** | ⚠️ Scattered | ✅ Centralized |
| **A/B Testing** | ❌ Not possible | ✅ Multiple variants |
| **Templating** | ❌ Static | ✅ Dynamic variables |
| **Documentation** | ⚠️ In code comments | ✅ Separate docs |
| **Validation** | ❌ None | ✅ Structure validation |
| **Metrics** | ❌ None | ✅ Track prompt performance |

## Migration Path

### Step 1: Extract Prompts to YAML
1. Create `prompts/` directory
2. Extract each prompt to YAML file
3. Create prompt loader utility

### Step 2: Update Agent Files
1. Replace hardcoded prompts with loader calls
2. Add fallback to hardcoded prompts (backward compatibility)

### Step 3: Add Versioning
1. Add version field to YAML files
2. Support version selection in loader

### Step 4: Add Advanced Features
1. Templating support
2. A/B testing framework
3. Prompt performance metrics

## Example: YAML Prompt Files

### `prompts/planner.yaml`
```yaml
version: "1.0"
agent: PlannerAgent
system_instruction: |
  Interpret the user request and propose a task.
  
  Use the create_task function to return structured task information.
  
  Focus on:
  - Creating clear, actionable task titles
  - Assigning appropriate priority based on urgency and importance
  - Providing detailed descriptions when helpful

metadata:
  author: "TaskPilot Team"
  created: "2025-12-01"
  last_updated: "2025-12-21"
  tags: ["task-creation", "structured-output"]
```

### `prompts/reviewer.yaml`
```yaml
version: "1.0"
agent: ReviewerAgent
system_instruction: |
  Review the proposed task for safety and compliance. 
  Reply with exactly one of: APPROVE, REJECTED, or REVIEW.
  
  - APPROVE: Task is safe and can proceed automatically
  - REJECTED: Task is unsafe and should be rejected
  - REVIEW: Task requires human review (use only for ambiguous cases, <5% of tasks)

metadata:
  author: "TaskPilot Team"
  created: "2025-12-01"
  last_updated: "2025-12-21"
  tags: ["safety", "compliance", "review"]
```

### `prompts/executor.yaml`
```yaml
version: "1.0"
agent: ExecutorAgent
system_instruction: |
  You receive approved task proposals. Your role is to prepare the task 
  for execution by outputting the task details clearly. 
  The workflow system will handle the actual execution. 
  Simply describe the task that needs to be executed.

metadata:
  author: "TaskPilot Team"
  created: "2025-12-01"
  last_updated: "2025-12-21"
  tags: ["execution", "task-preparation"]
```

## Benefits of External Prompts

1. **Non-developers can update prompts** without code changes
2. **Version control** for prompt changes
3. **A/B testing** different prompt variations
4. **Easier maintenance** with centralized storage
5. **Documentation** of prompt evolution
6. **Templating** for dynamic content
7. **Validation** before deployment
8. **Metrics** tracking prompt performance

## Next Steps

1. **Create `prompts/` directory** with YAML files
2. **Implement prompt loader** utility
3. **Update agent files** to use loader
4. **Add versioning** support
5. **Document prompt changes** in changelog
