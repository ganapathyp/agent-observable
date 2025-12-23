# Setup Monorepo Structure - Step by Step

**Goal**: Create `agent-observable` monorepo with taskpilot as example client.

**Current Structure**:
```
maia v2/
└── demo_agentframework/
    └── taskpilot/          # Current location
```

**Target Structure**:
```
maia v2/
└── agent-observable/        # New monorepo root
    ├── libraries/           # Future micro-libraries (empty for now)
    │   ├── agent-observable-core/
    │   ├── agent-observable-policy/
    │   ├── agent-observable-guardrails/
    │   └── agent-observable-prompts/
    ├── examples/
    │   └── taskpilot/       # Moved from demo_agentframework/taskpilot
    ├── .git/
    ├── .gitignore
    └── README.md
```

---

## Step-by-Step Instructions

### Step 1: Create New Monorepo Directory

```bash
# Navigate to parent directory
cd "/Users/ganapathypichumani/dev/code/maia v2"

# Create new monorepo root
mkdir agent-observable
cd agent-observable
```

---

### Step 2: Initialize Git Repository

```bash
# Initialize git repo
git init

# Create initial .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv
pip-log.txt
pip-delete-this-directory.txt

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Project specific
*.log
*.jsonl
logs/
traces/
.env
.env.local

# Build
dist/
build/
*.egg-info/
EOF

# Create initial README
cat > README.md << 'EOF'
# Agent Observable

Enterprise micro-libraries for agent observability, policy, guardrails, and prompts.

## Structure

- `libraries/` - Reusable micro-libraries
- `examples/` - Example implementations (taskpilot)

## Version

v0.01 - Initial baseline
EOF
```

---

### Step 3: Create Directory Structure

```bash
# Create libraries directory (for future micro-libs)
mkdir -p libraries

# Create examples directory
mkdir -p examples

# Create placeholder for future libraries (optional, for documentation)
mkdir -p libraries/agent-observable-core
mkdir -p libraries/agent-observable-policy
mkdir -p libraries/agent-observable-guardrails
mkdir -p libraries/agent-observable-prompts

# Add placeholder READMEs (optional)
echo "# agent-observable-core\n\nObservability library (to be extracted)" > libraries/agent-observable-core/README.md
echo "# agent-observable-policy\n\nPolicy decisions library (to be extracted)" > libraries/agent-observable-policy/README.md
echo "# agent-observable-guardrails\n\nGuardrails library (to be extracted)" > libraries/agent-observable-guardrails/README.md
echo "# agent-observable-prompts\n\nPrompt management library (to be extracted)" > libraries/agent-observable-prompts/README.md
```

---

### Step 4: Move taskpilot to examples/

```bash
# Copy taskpilot to examples (we'll move it, not copy, but this is safer)
cp -r "../demo_agentframework/taskpilot" "examples/taskpilot"

# Verify the move
ls -la examples/taskpilot/

# If everything looks good, you can remove the original later:
# rm -rf "../demo_agentframework/taskpilot"
```

**OR** if you prefer to move (not copy):

```bash
# Move taskpilot
mv "../demo_agentframework/taskpilot" "examples/taskpilot"
```

---

### Step 5: Update taskpilot Paths (if needed)

After moving, check if taskpilot has any hard-coded paths that reference its old location. Most Python imports should be relative and work fine.

```bash
# Check for any absolute paths in taskpilot
cd examples/taskpilot
grep -r "/demo_agentframework" . || echo "No hard-coded paths found"
grep -r "demo_agentframework" . || echo "No references found"
```

---

### Step 6: Initial Git Commit

```bash
# Go back to monorepo root
cd "/Users/ganapathypichumani/dev/code/maia v2/agent-observable"

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: agent-observable monorepo v0.01

- Created monorepo structure
- Moved taskpilot to examples/
- Set up libraries/ directory for future micro-libraries
- Baseline for 2-week sprint"
```

---

### Step 7: Create v0.01 Tag

```bash
# Create tag for baseline
git tag -a v0.01 -m "Baseline version before 2-week sprint

This is the checkpoint before starting Phase 0 refactoring.
Can be restored if needed during development."
```

---

### Step 8: Verify Structure

```bash
# Check structure
tree -L 3 -I '__pycache__|*.pyc|.git' || find . -maxdepth 3 -type d | grep -v ".git" | sort

# Verify git status
git status

# Verify tag
git tag -l

# Show tag details
git show v0.01
```

---

### Step 9: Test taskpilot Still Works

```bash
# Navigate to taskpilot
cd examples/taskpilot

# Test imports (adjust based on your setup)
python -c "import sys; sys.path.insert(0, '.'); from src.core import config; print('Imports work!')" || echo "Check your Python setup"

# Run existing tests if you have them
# pytest tests/ || echo "No tests found or pytest not installed"
```

---

## Final Structure

After setup, you should have:

```
agent-observable/
├── .git/                          # Git repository
├── .gitignore
├── README.md
├── libraries/                     # Future micro-libraries
│   ├── agent-observable-core/
│   │   └── README.md
│   ├── agent-observable-policy/
│   │   └── README.md
│   ├── agent-observable-guardrails/
│   │   └── README.md
│   └── agent-observable-prompts/
│       └── README.md
└── examples/
    └── taskpilot/                 # Your existing code
        ├── src/
        ├── tests/
        ├── docs/
        └── ...
```

---

## Restore Checkpoint (if needed)

If something goes wrong during development, you can restore:

```bash
# Restore to v0.01 tag
git checkout v0.01

# Or create a new branch from v0.01
git checkout -b restore-baseline v0.01
```

---

## Next Steps

1. ✅ Monorepo structure created
2. ✅ Git initialized
3. ✅ v0.01 tag created
4. ⬜ Start Phase 0, Task 0.1 (Create Abstraction Interfaces)

---

## Notes

- **Keep original taskpilot**: You may want to keep the original `demo_agentframework/taskpilot` as backup until you verify everything works
- **Git history**: If `demo_agentframework` was a git repo, you'll lose that history. If you want to preserve it, use `git subtree` or `git filter-branch`
- **Dependencies**: Update any CI/CD or documentation that references the old path

---

*Ready to start 2-week sprint!*
