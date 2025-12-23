# Production Deployment Guide

## Overview

This guide covers production deployment architecture for the TaskPilot agentic system, including:
- Application deployment (containers, orchestration)
- Observability stack (logs, traces, metrics)
- Visualization dashboards
- Scalability and reliability

---

## Production Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Production Stack                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │   Clients    │─────▶│  API Gateway │─────▶│  Load        │ │
│  │  (Web/Mobile)│      │  (Envoy/Nginx)│      │  Balancer    │ │
│  └──────────────┘      └──────────────┘      └──────┬───────┘ │
│                                                       │         │
│  ┌───────────────────────────────────────────────────┼───────┐ │
│  │              Kubernetes Cluster                    │       │ │
│  │                                                     │       │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐│       │ │
│  │  │ TaskPilot    │  │ TaskPilot    │  │ TaskPilot ││       │ │
│  │  │ Pod 1        │  │ Pod 2        │  │ Pod N     ││       │ │
│  │  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘│       │ │
│  │         │                  │                │     │       │ │
│  │         └──────────────────┼────────────────┘     │       │ │
│  │                            │                       │       │ │
│  │  ┌──────────────────────────┼───────────────────┐  │       │ │
│  │  │      Sidecar Containers  │                   │  │       │ │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐      │  │       │ │
│  │  │  │ OPA      │ │ NeMo     │ │ Metrics │      │  │       │ │
│  │  │  │ Sidecar  │ │ Guardrails│ │ Exporter│      │  │       │ │
│  │  │  └──────────┘ └──────────┘ └──────────┘      │  │       │ │
│  │  └───────────────────────────────────────────────┘  │       │ │
│  └─────────────────────────────────────────────────────┘       │ │
│                                                                 │ │
│  ┌─────────────────────────────────────────────────────────────┐│ │
│  │              Observability Stack                           ││ │
│  │                                                              ││ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    ││ │
│  │  │ Prometheus   │  │ OpenTelemetry│  │ ELK Stack     │    ││ │
│  │  │ (Metrics)    │  │ Collector    │  │ (Logs)        │    ││ │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    ││ │
│  │         │                  │                  │           ││ │
│  │         └──────────────────┼──────────────────┘           ││ │
│  │                            │                               ││ │
│  │                    ┌───────▼───────┐                      ││ │
│  │                    │    Grafana     │                      ││ │
│  │                    │  (Dashboards) │                      ││ │
│  │                    └────────────────┘                      ││ │
│  └─────────────────────────────────────────────────────────────┘│ │
│                                                                 │ │
│  ┌─────────────────────────────────────────────────────────────┐│ │
│  │              Storage Layer                                   ││ │
│  │                                                              ││ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    ││ │
│  │  │ PostgreSQL   │  │ Redis        │  │ S3/MinIO     │    ││ │
│  │  │ (Decisions)  │  │ (Cache)      │  │ (Traces)     │    ││ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    ││ │
│  └─────────────────────────────────────────────────────────────┘│ │
│                                                                 │ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. Application Deployment

### Option A: Docker Containers (Recommended for Small/Medium Scale)

#### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose metrics endpoint (if implemented)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from taskpilot.core.observability import get_health_checker; \
    import sys; hc = get_health_checker(); status = hc.check_health(); \
    sys.exit(0 if status.status == 'healthy' else 1)"

# Run application
CMD ["python", "main.py"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  taskpilot:
    build: .
    container_name: taskpilot
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
      - ./traces.jsonl:/app/traces.jsonl
      - ./decision_logs.jsonl:/app/decision_logs.jsonl
    ports:
      - "8000:8000"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "health_check.py", "--json"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Prometheus for metrics
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  # Grafana for visualization
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on:
      - prometheus

  # OpenTelemetry Collector
  otel-collector:
    image: otel/opentelemetry-collector:latest
    container_name: otel-collector
    volumes:
      - ./otel-collector-config.yml:/etc/otel-collector-config.yml
    ports:
      - "4317:4317"  # OTLP gRPC
      - "4318:4318"  # OTLP HTTP
    command: ["--config=/etc/otel-collector-config.yml"]
    depends_on:
      - taskpilot

volumes:
  prometheus-data:
  grafana-data:
```

---

### Option B: Kubernetes (Recommended for Large Scale)

#### Deployment Manifest

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: taskpilot
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: taskpilot
  template:
    metadata:
      labels:
        app: taskpilot
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: taskpilot
        image: taskpilot:latest
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: taskpilot-secrets
              key: openai-api-key
        - name: LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        volumeMounts:
        - name: data
          mountPath: /app/data
        - name: traces
          mountPath: /app/traces.jsonl
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: taskpilot-data
      - name: traces
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: taskpilot
  namespace: production
spec:
  selector:
    app: taskpilot
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

---

## 2. Observability Stack

### 2.1 Metrics Collection (Prometheus)

#### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'taskpilot'
    static_configs:
      - targets: ['taskpilot:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

#### Metrics Endpoint Implementation

```python
# Add to main.py or create metrics_server.py
from fastapi import FastAPI
from fastapi.responses import Response
from taskpilot.core.observability import get_metrics_collector

app = FastAPI()

@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    metrics = get_metrics_collector()
    all_metrics = metrics.get_all_metrics()
    
    lines = []
    
    # Counters
    for name, value in all_metrics["counters"].items():
        lines.append(f"# TYPE {name} counter")
        lines.append(f"{name} {value}")
    
    # Gauges
    for name, value in all_metrics["gauges"].items():
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name} {value}")
    
    # Histograms
    for name, stats in all_metrics["histograms"].items():
        lines.append(f"# TYPE {name} histogram")
        lines.append(f"{name}_count {stats['count']}")
        lines.append(f"{name}_sum {stats['avg'] * stats['count']}")
        lines.append(f"{name}_bucket{{le=\"+Inf\"}} {stats['count']}")
    
    return Response("\n".join(lines), media_type="text/plain")

@app.get("/health")
def health():
    """Health check endpoint."""
    from taskpilot.core.observability import get_health_checker
    health_checker = get_health_checker()
    status = health_checker.check_health()
    return {"status": status.status, "checks": status.checks}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

### 2.2 Distributed Tracing (OpenTelemetry)

#### OpenTelemetry Collector Configuration

```yaml
# otel-collector-config.yml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 10s
    send_batch_size: 1024

exporters:
  # Export to Jaeger
  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true
  
  # Export to Tempo
  tempo:
    endpoint: tempo:4317
    tls:
      insecure: true
  
  # Export to file (backup)
  file:
    path: /var/log/traces.jsonl

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger, tempo, file]
```

#### Application Integration

```python
# Add to main.py
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

# Initialize OpenTelemetry
resource = Resource.create({"service.name": "taskpilot"})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

# Add OTLP exporter
otlp_exporter = OTLPSpanExporter(
    endpoint="http://otel-collector:4317",
    insecure=True
)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Use in code
with tracer.start_as_current_span("workflow_execution") as span:
    span.set_attribute("request_id", request_id)
    # ... workflow code ...
```

---

### 2.3 Log Aggregation (ELK Stack)

#### Elasticsearch Configuration

```yaml
# docker-compose.yml addition
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: elasticsearch
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    container_name: logstash
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
      - ./logstash/config:/usr/share/logstash/config
    ports:
      - "5044:5044"
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    container_name: kibana
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
```

#### Logstash Pipeline

```ruby
# logstash/pipeline/logs.conf
input {
  file {
    path => "/var/log/taskpilot/*.log"
    codec => json
    type => "taskpilot"
  }
}

filter {
  if [type] == "taskpilot" {
    # Parse JSON logs
    json {
      source => "message"
    }
    
    # Extract request_id
    if [request_id] {
      mutate {
        add_field => { "[@metadata][request_id]" => "%{request_id}" }
      }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "taskpilot-logs-%{+YYYY.MM.dd}"
  }
}
```

#### Application Logging Configuration

```python
# Add structured logging
import logging
import json
from pythonjsonlogger import jsonlogger

# Configure JSON logger
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(timestamp)s %(level)s %(name)s %(message)s'
)
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Use in code
logger.info("Workflow started", extra={
    "request_id": request_id,
    "agent": "PlannerAgent",
    "latency_ms": 1234.56
})
```

---

## 3. Visualization Dashboards

### 3.1 Grafana Dashboards

#### Dashboard: System Overview

```json
{
  "dashboard": {
    "title": "TaskPilot System Overview",
    "panels": [
      {
        "title": "Workflow Execution Rate",
        "targets": [
          {
            "expr": "rate(workflow_runs[5m])",
            "legendFormat": "Runs/sec"
          }
        ]
      },
      {
        "title": "Agent Latency (P95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, agent_PlannerAgent_latency_ms)",
            "legendFormat": "PlannerAgent"
          },
          {
            "expr": "histogram_quantile(0.95, agent_ReviewerAgent_latency_ms)",
            "legendFormat": "ReviewerAgent"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(workflow_errors[5m])",
            "legendFormat": "Errors/sec"
          }
        ]
      },
      {
        "title": "Guardrails Blocks",
        "targets": [
          {
            "expr": "rate(agent_PlannerAgent_guardrails_blocked[5m])",
            "legendFormat": "PlannerAgent"
          }
        ]
      }
    ]
  }
}
```

#### Dashboard: Policy Decisions

```json
{
  "dashboard": {
    "title": "Policy Decisions & Guardrails",
    "panels": [
      {
        "title": "OPA Decisions (Allow/Deny)",
        "targets": [
          {
            "expr": "sum(rate(decision_logs_total{decision_type=\"tool_call\"}[5m])) by (result)",
            "legendFormat": "{{result}}"
          }
        ]
      },
      {
        "title": "NeMo Guardrails Blocks",
        "targets": [
          {
            "expr": "sum(rate(decision_logs_total{decision_type=\"guardrails_input\"}[5m])) by (result)",
            "legendFormat": "{{result}}"
          }
        ]
      }
    ]
  }
}
```

---

### 3.2 Jaeger/Tempo for Traces

#### Access Traces

1. **Jaeger UI**: `http://localhost:16686`
   - Search traces by request_id
   - View span details
   - Analyze performance

2. **Tempo UI**: `http://localhost:3200`
   - Similar to Jaeger
   - Better for high-volume traces

---

## 4. Complete Production Setup

### 4.1 Full docker-compose.yml

```yaml
version: '3.8'

services:
  # Application
  taskpilot:
    build: .
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
    volumes:
      - ./data:/app/data
    ports:
      - "8000:8000"
    depends_on:
      - prometheus
      - otel-collector

  # Metrics
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"

  # Visualization
  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana:/etc/grafana/provisioning
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on:
      - prometheus

  # Tracing
  otel-collector:
    image: otel/opentelemetry-collector:latest
    volumes:
      - ./otel-collector-config.yml:/etc/otel-collector-config.yml
    ports:
      - "4317:4317"
      - "4318:4318"
    depends_on:
      - jaeger

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"
      - "14250:14250"

  # Logs
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

volumes:
  prometheus-data:
  grafana-data:
  elasticsearch-data:
```

---

## 5. Deployment Steps

### Step 1: Prepare Application

```bash
# 1. Add metrics endpoint
# (Implement /metrics endpoint as shown above)

# 2. Add OpenTelemetry integration
# (Add OTLP exporter as shown above)

# 3. Configure structured logging
# (Add JSON logger as shown above)
```

### Step 2: Build and Deploy

```bash
# Build Docker image
docker build -t taskpilot:latest .

# Start all services
docker-compose up -d

# Verify services
docker-compose ps
```

### Step 3: Access Dashboards

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686
- **Kibana**: http://localhost:5601
- **Application**: http://localhost:8000

---

## 6. Production Checklist

### Application
- [ ] Docker containerization
- [ ] Health check endpoints
- [ ] Metrics endpoint (`/metrics`)
- [ ] Structured logging (JSON)
- [ ] OpenTelemetry integration
- [ ] Environment variable configuration
- [ ] Secrets management

### Observability
- [ ] Prometheus configured
- [ ] Grafana dashboards created
- [ ] OpenTelemetry collector running
- [ ] Jaeger/Tempo for traces
- [ ] ELK stack for logs
- [ ] Alert rules configured

### Infrastructure
- [ ] Load balancer configured
- [ ] Auto-scaling rules
- [ ] Resource limits set
- [ ] Persistent volumes
- [ ] Backup strategy
- [ ] Monitoring alerts

---

## 7. Scaling Considerations

### Horizontal Scaling

```yaml
# Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: taskpilot-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: taskpilot
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Vertical Scaling

```yaml
# Resource requests/limits
resources:
  requests:
    memory: "1Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "4000m"
```

---

## 8. Monitoring and Alerts

### Prometheus Alert Rules

```yaml
# alerts.yml
groups:
- name: taskpilot
  rules:
  - alert: HighErrorRate
    expr: rate(workflow_errors[5m]) > 0.1
    for: 5m
    annotations:
      summary: "High error rate detected"
  
  - alert: HighLatency
    expr: histogram_quantile(0.95, workflow_latency_ms) > 5000
    for: 10m
    annotations:
      summary: "P95 latency exceeds 5 seconds"
  
  - alert: GuardrailsBlocking
    expr: rate(agent_*_guardrails_blocked[5m]) > 0.05
    for: 5m
    annotations:
      summary: "High guardrails blocking rate"
```

---

## Summary

### Production Stack

1. **Application**: Docker containers or Kubernetes pods
2. **Metrics**: Prometheus + Grafana
3. **Traces**: OpenTelemetry + Jaeger/Tempo
4. **Logs**: ELK Stack (Elasticsearch, Logstash, Kibana)
5. **Storage**: PostgreSQL (decisions), Redis (cache), S3 (traces)

### Access Points

- **Application**: `http://localhost:8000`
- **Metrics**: Prometheus `http://localhost:9090`
- **Dashboards**: Grafana `http://localhost:3000`
- **Traces**: Jaeger `http://localhost:16686`
- **Logs**: Kibana `http://localhost:5601`

### Next Steps

1. Implement metrics endpoint (`/metrics`)
2. Add OpenTelemetry integration
3. Configure structured logging
4. Deploy with docker-compose
5. Create Grafana dashboards
6. Set up alerting rules

---

*This guide provides a complete production deployment setup with full observability stack.*
