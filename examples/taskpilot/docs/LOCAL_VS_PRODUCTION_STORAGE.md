# Local vs Production Storage Configuration

## Overview

This document explains **ALL** storage location differences between local development and production deployments for TaskPilot.

---

## Task Store Persistence

### Local Development

**Default Location:**
```
/path/to/taskpilot/.tasks.json
```

**Configuration:**
- **No environment variable set** → Uses project root: `taskpilot/.tasks.json`
- **Relative path** → Resolved relative to project root
- **Example:** `TASKS_FILE=.tasks.json` → `taskpilot/.tasks.json`

**Code Path:**
1. `TaskStore.__init__()` checks if `storage_path` is provided
2. If `None`, calls `get_paths().tasks_file` from `PathConfig`
3. `PathConfig.from_env()` checks `TASKS_FILE` environment variable
4. If not set, defaults to `base_dir / ".tasks.json"`
5. `base_dir` = project root (`taskpilot/` directory)

**File Location:**
- **Path:** `taskpilot/.tasks.json`
- **Backup:** `taskpilot/.tasks.json.bak` (auto-created on save)
- **Temp:** `taskpilot/.tasks.json.tmp` (during atomic writes)

---

### Production (Docker)

**Recommended Location:**
```
/var/lib/taskpilot/.tasks.json
```

**Configuration:**
```bash
# Environment variable
TASKS_FILE=/var/lib/taskpilot/.tasks.json
```

**Docker Volume Mount:**
```yaml
# docker-compose.yml
services:
  taskpilot:
    environment:
      - TASKS_FILE=/data/.tasks.json
    volumes:
      - taskpilot-data:/data
volumes:
  taskpilot-data:
```

**File Location:**
- **Path:** `/data/.tasks.json` (inside container)
- **Persistent:** Yes (via Docker volume)
- **Backup:** `/data/.tasks.json.bak`
- **Temp:** `/data/.tasks.json.tmp`

---

### Production (Kubernetes)

**Recommended Location:**
```
/persistent-storage/.tasks.json
```

**Configuration:**
```yaml
# k8s/deployment.yaml
env:
  - name: TASKS_FILE
    value: "/data/.tasks.json"
volumeMounts:
  - name: taskpilot-data
    mountPath: /data
volumes:
  - name: taskpilot-data
    persistentVolumeClaim:
      claimName: taskpilot-data-pvc
```

**File Location:**
- **Path:** `/data/.tasks.json` (inside pod)
- **Persistent:** Yes (via PersistentVolumeClaim)
- **Storage Backend:** Can be:
  - Network-attached storage (NFS, EBS, Azure Disk)
  - Cloud storage (S3 via CSI driver, GCS)
  - Local SSD (for single-node clusters)

---

## Complete Storage Location Comparison

### Data Files

| File Type | Local Default | Production (Docker) | Production (K8s) | Environment Variable |
|-----------|--------------|---------------------|------------------|---------------------|
| **Tasks** | `taskpilot/.tasks.json` | `/var/lib/taskpilot/.tasks.json` | `/data/.tasks.json` | `TASKS_FILE` |
| **Metrics** | `taskpilot/metrics.json` | `/var/lib/taskpilot/metrics.json` | `/data/metrics.json` | `METRICS_FILE` |
| **Traces** | `taskpilot/traces.jsonl` | `/var/lib/taskpilot/traces.jsonl` | `/data/traces.jsonl` | `TRACES_FILE` |
| **Decision Logs** | `taskpilot/decision_logs.jsonl` | `/var/lib/taskpilot/decision_logs.jsonl` | `/data/decision_logs.jsonl` | `DECISION_LOGS_FILE` |

### Directories

| Directory Type | Local Default | Production (Docker) | Production (K8s) | Environment Variable |
|----------------|--------------|---------------------|------------------|---------------------|
| **Logs** | `taskpilot/logs/` | `/var/log/taskpilot/` | `/var/log/taskpilot/` | `LOGS_DIR` or `DOCKER_LOGS_DIR` |
| **Prompts** | `taskpilot/prompts/` | `/app/prompts/` | `/app/prompts/` | `PROMPTS_DIR` |
| **Policies** | `taskpilot/policies/` | `/app/policies/` | `/app/policies/` | `POLICIES_DIR` |
| **Guardrails** | `taskpilot/guardrails/` | `/app/guardrails/` | `/app/guardrails/` | `GUARDRAILS_CONFIG_DIR` |
| **Observability** | `taskpilot/observability/` | `/app/observability/` | `/app/observability/` | `OBSERVABILITY_DIR` |

---

## Configuration Resolution Logic

### Path Resolution Priority

1. **Environment Variable** (highest priority)
   - If `TASKS_FILE` is set → Use that path (absolute or relative)
   
2. **PathConfig from .env file**
   - Loads from `.env` file in project root
   - Uses `TASKS_FILE` if present
   
3. **Default** (lowest priority)
   - Relative to project root: `base_dir / ".tasks.json"`

### Code Flow

```python
# 1. TaskStore initialization
TaskStore.__init__(storage_path=None)
  ↓
# 2. Get from PathConfig
paths = get_paths()  # Returns PathConfig instance
storage_path = paths.tasks_file
  ↓
# 3. PathConfig resolution
PathConfig.from_env()
  ↓
# 4. Check environment variable
tasks_file = os.getenv("TASKS_FILE")
  ↓
if tasks_file:
    tasks_file = Path(tasks_file).resolve()  # Absolute or relative
else:
    tasks_file = base_dir / ".tasks.json"     # Default
```

---

## Production Deployment Examples

### Example 1: Docker Compose (Simple)

```yaml
version: '3.8'
services:
  taskpilot:
    image: taskpilot:latest
    environment:
      - TASKS_FILE=/data/.tasks.json
      - METRICS_FILE=/data/metrics.json
      - TRACES_FILE=/data/traces.jsonl
      - DECISION_LOGS_FILE=/data/decision_logs.jsonl
      - LOGS_DIR=/var/log/taskpilot
    volumes:
      - taskpilot-data:/data
      - taskpilot-logs:/var/log/taskpilot
volumes:
  taskpilot-data:
  taskpilot-logs:
```

**Storage Locations:**
- Tasks: `/data/.tasks.json` (persistent volume)
- Logs: `/var/log/taskpilot/` (persistent volume)

---

### Example 2: Docker Compose (With Observability)

```yaml
version: '3.8'
services:
  taskpilot:
    environment:
      - TASKS_FILE=/app/data/.tasks.json
      - METRICS_FILE=/app/data/metrics.json
      - LOGS_DIR=/var/log/taskpilot
    volumes:
      - ./data:/app/data              # Local bind mount
      - ./logs:/var/log/taskpilot     # For Filebeat
```

**Storage Locations:**
- Tasks: `./data/.tasks.json` (host filesystem)
- Logs: `./logs/` (host filesystem, mounted to `/var/log/taskpilot` in container)

---

### Example 3: Kubernetes with PersistentVolume

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: taskpilot-data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: fast-ssd
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
        env:
        - name: TASKS_FILE
          value: "/data/.tasks.json"
        - name: METRICS_FILE
          value: "/data/metrics.json"
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: taskpilot-data-pvc
```

**Storage Locations:**
- Tasks: `/data/.tasks.json` (on PersistentVolume)
- **Backend:** Can be EBS (AWS), Azure Disk, GCE Persistent Disk, or NFS

---

### Example 4: Kubernetes with ConfigMap/Secret

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: taskpilot-config
data:
  TASKS_FILE: "/data/.tasks.json"
  METRICS_FILE: "/data/metrics.json"
  LOGS_DIR: "/var/log/taskpilot"
---
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: taskpilot
        envFrom:
        - configMapRef:
            name: taskpilot-config
```

---

## Storage Backend Options (Production)

### Option 1: File System (Current Implementation)

**Pros:**
- Simple, no dependencies
- Fast for small-medium datasets
- Easy backup (just copy file)

**Cons:**
- Not suitable for multi-instance deployments
- No concurrent access control
- File size limits for large datasets

**Use Case:** Single-instance deployments, Docker containers

---

### Option 2: Database (PostgreSQL/MySQL)

**Not Currently Implemented** - Would require:
- Database connection pooling
- Schema migration
- Query optimization
- Transaction support

**Use Case:** Multi-instance deployments, high availability

---

### Option 3: Object Storage (S3/MinIO)

**Not Currently Implemented** - Would require:
- S3 client library
- Object versioning
- Bucket configuration
- Access credentials

**Use Case:** Cloud deployments, large-scale storage

---

### Option 4: Redis (In-Memory + Persistence)

**Not Currently Implemented** - Would require:
- Redis connection
- Serialization/deserialization
- TTL management
- Persistence configuration

**Use Case:** High-performance, temporary task storage

---

## Current Implementation Details

### Task Store Architecture

**Storage Type:** File-based JSON

**File Format:**
```json
{
  "task_id_1": {
    "id": "task_id_1",
    "title": "Task Title",
    "priority": "high",
    "status": "pending",
    "created_at": "2025-12-22T12:00:00",
    ...
  },
  "task_id_2": { ... }
}
```

**Persistence Strategy:**
1. **Atomic Writes:** Write to `.tmp` file first
2. **Backup:** Create `.bak` before overwriting
3. **Error Recovery:** Load from backup if main file corrupted
4. **Directory Creation:** Auto-creates parent directories

**Concurrency:**
- **Local:** File locking not implemented (single process)
- **Production:** Not safe for multi-instance (would need database)

---

## Environment Variable Reference

### All Storage-Related Environment Variables

```bash
# Data Files
TASKS_FILE=.tasks.json                    # Task storage
METRICS_FILE=metrics.json                 # Metrics storage
TRACES_FILE=traces.jsonl                  # Trace storage
DECISION_LOGS_FILE=decision_logs.jsonl    # Decision log storage

# Directories
LOGS_DIR=logs                             # Logs directory
DOCKER_LOGS_DIR=/var/log/taskpilot        # Docker logs (checked first)
PROMPTS_DIR=prompts                       # Agent prompts
POLICIES_DIR=policies                     # OPA policies
GUARDRAILS_CONFIG_DIR=guardrails         # Guardrails config
OBSERVABILITY_DIR=observability           # Observability configs

# Base Directory (rarely needed)
BASE_DIR=/path/to/taskpilot               # Override project root
```

---

## Path Resolution Examples

### Example 1: Local Development (No Config)

```bash
# No environment variables set
# Result:
tasks_file = /Users/ganapathypichumani/dev/code/maia v2/demo_agentframework/taskpilot/.tasks.json
```

### Example 2: Local Development (Relative Path)

```bash
# .env file:
TASKS_FILE=.tasks.json

# Result:
tasks_file = /Users/ganapathypichumani/dev/code/maia v2/demo_agentframework/taskpilot/.tasks.json
```

### Example 3: Local Development (Absolute Path)

```bash
# .env file:
TASKS_FILE=/tmp/my-tasks.json

# Result:
tasks_file = /tmp/my-tasks.json
```

### Example 4: Docker (Volume Mount)

```bash
# Environment variable:
TASKS_FILE=/data/.tasks.json

# Docker volume:
volumes:
  - taskpilot-data:/data

# Result:
tasks_file = /data/.tasks.json (inside container)
# Persisted in Docker volume: taskpilot-data
```

### Example 5: Kubernetes (PVC)

```bash
# Environment variable:
TASKS_FILE=/data/.tasks.json

# Kubernetes volume:
volumeMounts:
  - mountPath: /data
    persistentVolumeClaim:
      claimName: taskpilot-data-pvc

# Result:
tasks_file = /data/.tasks.json (inside pod)
# Persisted in PersistentVolume (EBS, Azure Disk, etc.)
```

---

## Logs Directory Special Handling

The logs directory has **special logic** for Docker deployments:

```python
# From config.py
logs_dir = os.getenv("LOGS_DIR")
if logs_dir:
    logs_dir = Path(logs_dir).resolve()
else:
    # Check Docker directory first
    docker_log_dir = os.getenv("DOCKER_LOGS_DIR")
    if docker_log_dir:
        docker_log_dir = Path(docker_log_dir).resolve()
    else:
        docker_log_dir = Path("/var/log/taskpilot")
    
    local_log_dir = base_dir / "logs"
    
    # Use Docker directory if it exists and is writable
    if docker_log_dir.exists() and os.access(docker_log_dir, os.W_OK):
        logs_dir = docker_log_dir
    else:
        logs_dir = local_log_dir
```

**Priority:**
1. `LOGS_DIR` environment variable (if set)
2. `DOCKER_LOGS_DIR` environment variable (if set)
3. `/var/log/taskpilot` (if exists and writable)
4. `taskpilot/logs/` (fallback)

---

## Production Considerations

### Multi-Instance Deployments

**Current Limitation:**
- File-based storage is **NOT safe** for multiple instances
- Each instance would have its own `.tasks.json` file
- No synchronization between instances

**Solution Options:**
1. **Use a database** (PostgreSQL, MySQL)
2. **Use shared storage** (NFS, EFS)
3. **Use object storage** (S3, MinIO)
4. **Use a cache** (Redis with persistence)

### Backup Strategy

**Local:**
- Manual backup: Copy `.tasks.json` file
- Auto-backup: `.tasks.json.bak` created on each save

**Production:**
- **Docker:** Backup Docker volume
- **Kubernetes:** Backup PersistentVolume
- **Cloud:** Use cloud backup services (AWS Backup, Azure Backup)

### Data Migration

**From Local to Production:**
```bash
# 1. Export from local
cp taskpilot/.tasks.json /tmp/tasks-backup.json

# 2. Copy to production
scp /tmp/tasks-backup.json production-server:/var/lib/taskpilot/.tasks.json

# 3. Set permissions
chown taskpilot:taskpilot /var/lib/taskpilot/.tasks.json
chmod 644 /var/lib/taskpilot/.tasks.json
```

---

## Summary Table: All Storage Locations

| Component | Local Default | Production Default | Configurable Via |
|-----------|--------------|-------------------|------------------|
| **Task Store** | `taskpilot/.tasks.json` | `/var/lib/taskpilot/.tasks.json` | `TASKS_FILE` |
| **Metrics** | `taskpilot/metrics.json` | `/var/lib/taskpilot/metrics.json` | `METRICS_FILE` |
| **Traces** | `taskpilot/traces.jsonl` | `/var/lib/taskpilot/traces.jsonl` | `TRACES_FILE` |
| **Decision Logs** | `taskpilot/decision_logs.jsonl` | `/var/lib/taskpilot/decision_logs.jsonl` | `DECISION_LOGS_FILE` |
| **Application Logs** | `taskpilot/logs/` | `/var/log/taskpilot/` | `LOGS_DIR` or `DOCKER_LOGS_DIR` |
| **Prompts** | `taskpilot/prompts/` | `/app/prompts/` | `PROMPTS_DIR` |
| **Policies** | `taskpilot/policies/` | `/app/policies/` | `POLICIES_DIR` |
| **Guardrails Config** | `taskpilot/guardrails/` | `/app/guardrails/` | `GUARDRAILS_CONFIG_DIR` |
| **Observability Configs** | `taskpilot/observability/` | `/app/observability/` | `OBSERVABILITY_DIR` |

---

## Key Differences Summary

### 1. **Path Type**
- **Local:** Relative paths (default to project root)
- **Production:** Absolute paths (typically `/var/lib/` or `/data/`)

### 2. **Persistence**
- **Local:** Files in project directory (lost if directory deleted)
- **Production:** Docker volumes or PersistentVolumes (survive container restarts)

### 3. **Configuration**
- **Local:** Defaults work out-of-the-box
- **Production:** Must set environment variables

### 4. **Multi-Instance**
- **Local:** Single instance (file-based OK)
- **Production:** Multiple instances require database/shared storage

### 5. **Backup**
- **Local:** Manual file copy
- **Production:** Volume snapshots, cloud backups

---

*This document provides a complete reference for all storage location differences between local and production deployments.*
