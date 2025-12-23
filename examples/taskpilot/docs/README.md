# TaskPilot Documentation

Welcome to TaskPilot documentation! This guide helps you navigate the documentation efficiently.

---

## 🚀 Quick Start

### New to TaskPilot?
1. **[ONBOARDING.md](ONBOARDING.md)** - Start here! Get up and running in 5 minutes
2. **[CONFIGURATION.md](CONFIGURATION.md)** - Configure your environment
3. **[CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md)** - Understand the system architecture
4. **[INTEGRATION_TEST_GUIDE.md](INTEGRATION_TEST_GUIDE.md)** - Test the system end-to-end

### Need Help?
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
- **[TESTING.md](TESTING.md)** - How to run and write tests

### Production Deployment?
- **[SPECIFICATION.md](SPECIFICATION.md)** - Complete system specification
- **[details/PRODUCTION_DEPLOYMENT.md](details/PRODUCTION_DEPLOYMENT.md)** - Detailed deployment guide
- **[details/LLM_PRODUCTION_GUIDE.md](details/LLM_PRODUCTION_GUIDE.md)** - LLM-specific production considerations

---

## 📚 Core Documentation

These are the essential documents you'll reference most often:

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **[ONBOARDING.md](ONBOARDING.md)** | Quick start guide | First time setup |
| **[CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md)** | System architecture overview | Understanding the system |
| **[CONFIGURATION.md](CONFIGURATION.md)** | Configuration guide | Setting up environment |
| **[INTEGRATION_TEST_GUIDE.md](INTEGRATION_TEST_GUIDE.md)** | Manual testing steps | Testing observability features |
| **[TESTING.md](TESTING.md)** | Test suite overview | Running/writing tests |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Common issues | When things break |
| **[SPECIFICATION.md](SPECIFICATION.md)** | System specification | Design validation, API contracts |

---

## 📖 Detailed Documentation

For in-depth information on specific topics, see the **[details/](details/)** folder:

### Architecture & Design
- **[details/DESIGN.md](details/DESIGN.md)** - Design principles and patterns
- **[details/GUARDRAILS_ARCHITECTURE_EXPLAINED.md](details/GUARDRAILS_ARCHITECTURE_EXPLAINED.md)** - Guardrails architecture deep dive
- **[details/PRODUCTION_GUARDRAILS_ARCHITECTURE.md](details/PRODUCTION_GUARDRAILS_ARCHITECTURE.md)** - Production guardrails design
- **[details/EMBEDDED_OPA_IMPLEMENTATION.md](details/EMBEDDED_OPA_IMPLEMENTATION.md)** - OPA implementation details
- **[details/ERROR_HANDLING.md](details/ERROR_HANDLING.md)** - Exception hierarchy and error codes reference

### Observability
- **[details/OBSERVABILITY_INTEGRATION.md](details/OBSERVABILITY_INTEGRATION.md)** - Complete observability guide (metrics, traces, logs)
- **[details/OBSERVABILITY_PERFORMANCE_IMPACT.md](details/OBSERVABILITY_PERFORMANCE_IMPACT.md)** - Performance impact analysis
- **[details/ENDPOINTS_USAGE.md](details/ENDPOINTS_USAGE.md)** - HTTP endpoints detailed guide

### Development & Best Practices
- **[details/DEVELOPMENT_PRACTICES.md](details/DEVELOPMENT_PRACTICES.md)** - Development workflow and practices
- **[details/MICROSOFT_AGENT_FRAMEWORK_BEST_PRACTICES.md](details/MICROSOFT_AGENT_FRAMEWORK_BEST_PRACTICES.md)** - Framework best practices
- **[details/CAPABILITIES_MATRIX.md](details/CAPABILITIES_MATRIX.md)** - Capabilities analysis matrix

### Implementation Details
- **[details/STRUCTURED_OUTPUT.md](details/STRUCTURED_OUTPUT.md)** - Structured output implementation
- **[details/PROMPT_MANAGEMENT.md](details/PROMPT_MANAGEMENT.md)** - Prompt management system
- **[details/TASK_TRACKING.md](details/TASK_TRACKING.md)** - Task tracking implementation

### Production & Deployment
- **[details/PRODUCTION_DEPLOYMENT.md](details/PRODUCTION_DEPLOYMENT.md)** - Production deployment guide
- **[details/LLM_PRODUCTION_GUIDE.md](details/LLM_PRODUCTION_GUIDE.md)** - LLM production considerations
- **[details/DOCKER_SETUP.md](details/DOCKER_SETUP.md)** - Docker observability stack setup

### Safety & Security
- **[details/PROMPT_AND_TOOL_SAFETY.md](details/PROMPT_AND_TOOL_SAFETY.md)** - Safety considerations

### Reference
- **[details/REFERENCE.md](details/REFERENCE.md)** - API reference documentation
- **[details/CHANGELOG.md](details/CHANGELOG.md)** - Version history
- **[details/AUTO_ACTIVATE_VENV.md](details/AUTO_ACTIVATE_VENV.md)** - Virtual environment automation

---

## 📁 Documentation Structure

```
docs/
├── README.md (this file)              # Documentation index
│
├── Core Documentation (Essential)
│   ├── ONBOARDING.md                  # Quick start guide
│   ├── CURRENT_ARCHITECTURE.md       # Architecture overview
│   ├── CONFIGURATION.md               # Configuration guide
│   ├── INTEGRATION_TEST_GUIDE.md      # Testing guide
│   ├── TESTING.md                     # Test suite overview
│   ├── TROUBLESHOOTING.md             # Common issues
│   └── SPECIFICATION.md                # System specification
│
└── details/                           # Detailed documentation
    ├── Architecture & Design
    ├── Observability
    ├── Development & Best Practices
    ├── Implementation Details
    ├── Production & Deployment
    ├── Safety & Security
    └── Reference
```

---

## 🎯 Documentation Principles

1. **Core docs** (in `docs/`) - Essential information for daily use
2. **Detailed docs** (in `details/`) - Deep dives and reference material
3. **Uniform structure** - Consistent formatting and organization
4. **Easy navigation** - Clear categorization and cross-references

---

## 📝 Contributing to Documentation

When adding or updating documentation:

1. **Core docs** - For essential, frequently-referenced information
2. **Details folder** - For in-depth guides, reference material, or specialized topics
3. **Update README.md** - Add new documents to the appropriate section
4. **Cross-reference** - Link related documents for easy navigation

---

*Last updated: 2024-12-22*
