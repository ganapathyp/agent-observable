# Configuration Guide

TaskPilot uses environment variables and configuration files for all settings. This makes it easy to:
- **Work out-of-the-box locally** with sensible defaults
- **Deploy to production** by setting environment variables
- **Customize paths** for different deployment scenarios

---

## Quick Start

### Local Development (Out-of-the-Box)

**No configuration needed!** TaskPilot works immediately:

```bash
# 1. Set your OpenAI API key
echo "OPENAI_API_KEY=your-key-here" > .env

# 2. Run
python main.py
```

All paths default to the project root directory.

---

## Configuration Files

### `.env` File

Create a `.env` file in the project root (see `.env.example`):

```bash
cp .env.example .env
# Edit .env with your values
```

**Priority:**
1. Environment variables (highest)
2. `.env` file
3. Default values (lowest)

---

## Configuration Options

### OpenAI Configuration

```bash
OPENAI_API_KEY=your-api-key-here        # Required
OPENAI_MODEL_ID=gpt-4o-mini             # Optional, defaults to gpt-4o-mini
```

### Server Configuration

```bash
PORT=8000                                # HTTP server port
HOST=0.0.0.0                            # HTTP server host
```

### File Paths

All paths are **relative to project root by default**, but can be set to **absolute paths** for production:

```bash
# Data files
TASKS_FILE=.tasks.json                  # Task storage
METRICS_FILE=metrics.json               # Metrics storage
TRACES_FILE=traces.jsonl                # Trace storage
DECISION_LOGS_FILE=decision_logs.jsonl   # Decision log storage

# Directories
LOGS_DIR=logs                           # Logs directory
PROMPTS_DIR=prompts                     # Agent prompts
POLICIES_DIR=policies                   # OPA policies
GUARDRAILS_CONFIG_DIR=guardrails        # Guardrails config
OBSERVABILITY_DIR=observability          # Observability configs
```

**For Docker/Production:**
```bash
# Use absolute paths
TASKS_FILE=/var/lib/taskpilot/.tasks.json
METRICS_FILE=/var/lib/taskpilot/metrics.json
LOGS_DIR=/var/log/taskpilot
```

### Observability URLs

These URLs are used in API responses (e.g., `/` endpoint):

```bash
GRAFANA_URL=http://localhost:3000
PROMETHEUS_URL=http://localhost:9090
JAEGER_URL=http://localhost:16686
KIBANA_URL=http://localhost:5601
```

**For Production:**
```bash
GRAFANA_URL=https://grafana.example.com
PROMETHEUS_URL=https://prometheus.example.com
# etc.
```

### OpenTelemetry

```bash
OTEL_ENABLED=true                      # Enable/disable OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=taskpilot
```

### Workflow

```bash
WORKFLOW_INTERVAL_SECONDS=60            # Background workflow interval (server mode)
```

---

## Production Deployment

### Example: Kubernetes Deployment

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: taskpilot-config
data:
  PORT: "8000"
  HOST: "0.0.0.0"
  OTEL_ENABLED: "true"
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector:4317"
  GRAFANA_URL: "https://grafana.example.com"
  PROMETHEUS_URL: "https://prometheus.example.com"
---
apiVersion: v1
kind: Secret
metadata:
  name: taskpilot-secrets
stringData:
  OPENAI_API_KEY: "your-api-key"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: taskpilot
spec:
  template:
    spec:
      containers:
      - name: taskpilot
        image: taskpilot:latest
        envFrom:
        - configMapRef:
            name: taskpilot-config
        - secretRef:
            name: taskpilot-secrets
        env:
        - name: TASKS_FILE
          value: "/data/.tasks.json"
        - name: METRICS_FILE
          value: "/data/metrics.json"
        - name: LOGS_DIR
          value: "/var/log/taskpilot"
        volumeMounts:
        - name: data
          mountPath: /data
        - name: logs
          mountPath: /var/log/taskpilot
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: taskpilot-data
      - name: logs
        emptyDir: {}
```

### Example: Docker Compose

```yaml
services:
  taskpilot:
    image: taskpilot:latest
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - PORT=8000
      - TASKS_FILE=/data/.tasks.json
      - METRICS_FILE=/data/metrics.json
      - LOGS_DIR=/var/log/taskpilot
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
    volumes:
      - taskpilot-data:/data
      - taskpilot-logs:/var/log/taskpilot
    ports:
      - "8000:8000"
```

---

## Path Resolution

### Default Behavior

1. **Relative paths** → Resolved relative to project root
2. **Absolute paths** → Used as-is
3. **Not set** → Uses default relative to project root

### Examples

```bash
# Relative path (default)
METRICS_FILE=metrics.json
# Resolves to: /path/to/taskpilot/metrics.json

# Absolute path (production)
METRICS_FILE=/var/lib/taskpilot/metrics.json
# Uses: /var/lib/taskpilot/metrics.json

# Not set
# Uses default: taskpilot/metrics.json
```

---

## Logs Directory

The logs directory has special handling for Docker deployments:

1. **First checks:** `DOCKER_LOGS_DIR` (if set)
2. **Then checks:** `LOGS_DIR` (if set)
3. **Falls back to:** `logs/` in project root

**For Docker/Filebeat:**
```bash
# Set Docker logs directory
DOCKER_LOGS_DIR=/var/log/taskpilot

# Or set logs directory directly
LOGS_DIR=/var/log/taskpilot
```

The application will:
- Use Docker directory if it exists and is writable
- Otherwise use local directory
- Create directories automatically

---

## Configuration Access in Code

### Using Configuration

```python
from taskpilot.core.config import get_config, get_paths, get_app_config

# Get full config
config = get_config()

# Get paths
paths = get_paths()
tasks_file = paths.tasks_file
logs_dir = paths.logs_dir

# Get app config
app_config = get_app_config()
port = app_config.port
grafana_url = app_config.grafana_url
```

### Creating Custom Config

```python
from taskpilot.core.config import create_config, PathConfig, AppConfig

# Create config with custom base directory
config = create_config(base_dir=Path("/custom/path"))

# Or with custom .env file
config = create_config(env_file_path=Path("/custom/.env"))
```

---

## Validation

Configuration is validated on load:

- **Required:** `OPENAI_API_KEY` must be set
- **Paths:** Directories are created automatically if they don't exist
- **Ports:** Must be valid port numbers (1-65535)

---

## Troubleshooting

### Configuration Not Loading

**Check:**
1. `.env` file exists and is readable
2. Environment variables are set correctly
3. Paths are valid and writable

**Debug:**
```python
from taskpilot.core.config import get_config
config = get_config()
print(f"Paths: {config.paths}")
print(f"App: {config.app}")
```

### Path Issues

**Problem:** Files not found or permission errors

**Solution:**
- Use absolute paths for production
- Ensure directories exist and are writable
- Check file permissions

**Example:**
```bash
# Create directories
mkdir -p /var/lib/taskpilot /var/log/taskpilot

# Set permissions
chown -R taskpilot:taskpilot /var/lib/taskpilot /var/log/taskpilot
chmod 755 /var/lib/taskpilot /var/log/taskpilot
```

---

## Best Practices

1. **Local Development:** Use defaults (no configuration needed)
2. **Docker:** Use environment variables in `docker-compose.yml`
3. **Kubernetes:** Use ConfigMaps and Secrets
4. **Production:** Use absolute paths for all data files
5. **Security:** Never commit `.env` files (use `.env.example`)

---

*For more details, see [.env.example](../.env.example) and [CURRENT_ARCHITECTURE.md](CURRENT_ARCHITECTURE.md)*
