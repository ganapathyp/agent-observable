# Automatic Virtual Environment Activation

This guide explains how to automatically activate the virtual environment when you navigate to the `taskpilot` folder.

## Option 1: direnv (Recommended)

**direnv** is a popular tool that automatically loads/unloads environment variables and activates virtual environments based on `.envrc` files.

### Installation

```bash
# macOS (using Homebrew)
brew install direnv

# Or using MacPorts
sudo port install direnv
```

### Setup

1. **Add direnv hook to your shell** (add to `~/.zshrc`):

```bash
# Add this line to ~/.zshrc
eval "$(direnv hook zsh)"
```

2. **Reload your shell**:
```bash
source ~/.zshrc
```

3. **Allow direnv in the taskpilot directory** (first time only):
```bash
cd /Users/ganapathypichumani/dev/code/maia\ v2/demo_agentframework/taskpilot
direnv allow
```

### How It Works

- When you `cd` into the `taskpilot` folder, direnv automatically:
  - Activates `.venv` if it exists (or creates it if missing)
  - Installs/updates dependencies if needed
  - Shows a helpful status message

- When you `cd` out of the folder, direnv automatically:
  - Deactivates the virtual environment
  - Cleans up the environment

### Benefits

- ✅ Automatic activation/deactivation
- ✅ Works with any shell (zsh, bash, fish)
- ✅ Can also load `.env` files automatically
- ✅ No manual commands needed

---

## Option 2: Simple Zsh Hook (No Dependencies)

If you prefer not to install direnv, you can use a simple zsh function.

### Setup

Add this to your `~/.zshrc`:

```bash
# Auto-activate virtual environment when entering taskpilot directory
auto_venv() {
    if [[ -f .venv/bin/activate ]]; then
        source .venv/bin/activate
        echo "✅ Virtual environment activated"
    elif [[ -f venv/bin/activate ]]; then
        source venv/bin/activate
        echo "✅ Virtual environment activated"
    fi
}

# Hook into directory changes
autoload -U add-zsh-hook
add-zsh-hook chpwd auto_venv

# Activate on current directory if applicable
auto_venv
```

Then reload your shell:
```bash
source ~/.zshrc
```

### How It Works

- Automatically activates `.venv` or `venv` when you `cd` into any directory that has one
- Works for all projects, not just taskpilot
- Simpler but less configurable than direnv

---

## Option 3: Shell Alias (Quick Access)

Add this to your `~/.zshrc` for quick navigation + activation:

```bash
# Quick alias to cd to taskpilot and activate venv
taskpilot() {
    cd "/Users/ganapathypichumani/dev/code/maia v2/demo_agentframework/taskpilot"
    if [ -f .venv/bin/activate ]; then
        source .venv/bin/activate
        echo "✅ TaskPilot virtual environment activated"
    else
        echo "⚠️  Virtual environment not found. Run: make install"
    fi
}
```

Then use:
```bash
taskpilot  # Instead of cd'ing manually
```

---

## Verification

After setup, test it:

```bash
# Navigate to taskpilot folder
cd /Users/ganapathypichumani/dev/code/maia\ v2/demo_agentframework/taskpilot

# Check if venv is activated (should show .venv in prompt or path)
which python3
# Should show: /Users/.../taskpilot/.venv/bin/python3

# Or check Python path
python3 -c "import sys; print(sys.executable)"
# Should show path ending in .venv/bin/python3
```

---

## Troubleshooting

### direnv: "direnv: error .envrc is blocked"

**Solution:**
```bash
cd taskpilot
direnv allow
```

### direnv: "command not found: direnv"

**Solution:** Install direnv first:
```bash
brew install direnv
# Then add hook to ~/.zshrc and reload
```

### Zsh hook not working

**Solution:**
1. Check if function is loaded: `type auto_venv`
2. Manually reload: `source ~/.zshrc`
3. Check if `.venv/bin/activate` exists in the directory

### Virtual environment not found

**Solution:**
```bash
cd taskpilot
make install
# Or manually:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

---

## Recommendation

**Use direnv (Option 1)** - It's the most robust solution and widely used in the Python community. It also handles environment variable loading from `.env` files automatically.
