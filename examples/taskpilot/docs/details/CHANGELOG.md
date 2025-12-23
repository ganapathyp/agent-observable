# Changelog

## [0.1.0] - 2025-12-20

### Refactored
- **Organized directory structure** into logical subpackages:
  - `taskpilot/agents/` - All agent definitions
  - `taskpilot/core/` - Configuration, middleware, workflow
  - `taskpilot/tools/` - Tools for agents and workflows
- **Improved imports** with cleaner package structure
- **Added package __init__ files** for better exports
- **Fixed configuration paths** to correctly resolve .env file
- **Cleaned build artifacts** (__pycache__, *.egg-info)

### Fixed
- Workflow structure (executor chain conflict)
- Conditional branching (executor now runs on APPROVE)
- Configuration file path resolution
- Import paths after refactoring

### Added
- Comprehensive error handling
- Proper logging (replaced print statements)
- Configuration management system
- Consolidated tool definitions
- Improved middleware message extraction
- Isolated virtual environment setup
- Documentation (README, REFACTORING_SUMMARY)

### Changed
- All imports now use organized subpackages
- Main entry point remains at root for easy execution
- Scripts updated to work with new structure

### Testing
- ✅ All imports work correctly
- ✅ Full workflow executes successfully
- ✅ Configuration resolves correctly
- ✅ Isolated venv works properly
- ✅ No linter errors
