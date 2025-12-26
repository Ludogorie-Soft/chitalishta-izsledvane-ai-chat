# Observability Guide

This guide explains how to monitor and analyze the Chitalishta RAG System, especially LangChain operations, in both development and production environments.

## Current Logging Setup

The application uses **structured JSON logging** with the following features:

- **Request ID tracking**: Every request gets a unique UUID for end-to-end tracing
- **Structured JSON logs**: All logs are in JSON format for easy parsing and querying
- **LangChain callbacks**: All LLM calls, retrievals, and chain executions are logged
- **Request/response logging**: All HTTP requests and responses are logged with timing

## Log Output

### Development (Local)

Logs are written to **stdout** (console) in JSON format. You can see them in your terminal where FastAPI is running.

### Production (Docker)

In Docker, logs go to **stdout/stderr** and are captured by Docker's logging driver. You can access them via:

```bash
# View live logs
docker-compose -f docker-compose.prod.yml logs -f app

# View last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 app

# View logs for specific time range
docker-compose -f docker-compose.prod.yml logs --since 1h app

# Save logs to file
docker-compose -f docker-compose.prod.yml logs app > app.log
```

## Log Structure

All logs are structured JSON with the following common fields:

```json
{
  "event": "llm_start",
  "timestamp": "2025-01-15T10:30:45.123456",
  "level": "info",
  "logger": "app.rag.langchain_callbacks",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "run_id": "abc123",
  "model": "gpt-4o-mini",
  "prompt_count": 1,
  "prompt_preview": "..."
}
```

### Key Event Types

1. **Request Events**:
   - `request_started`: HTTP request received
   - `request_completed`: HTTP request finished successfully
   - `request_failed`: HTTP request failed

2. **LangChain LLM Events**:
   - `llm_start`: LLM call initiated
   - `llm_end`: LLM call completed (includes token usage, latency)
   - `llm_error`: LLM call failed

3. **LangChain Retrieval Events**:
   - `retriever_start`: Document retrieval started
   - `retriever_end`: Document retrieval completed (includes document count, sources)
   - `retriever_error`: Retrieval failed

4. **LangChain Chain Events**:
   - `chain_start`: Chain execution started
   - `chain_end`: Chain execution completed
   - `chain_error`: Chain execution failed

5. **SQL Events**:
   - `sql_query_audit`: SQL query executed (from SQLAuditLogger)

## Observability Options

### Option 1: Docker Logs (Simple, No Setup)

**Best for**: Quick debugging, small deployments

**Access logs**:
```bash
# On EC2 server
docker-compose -f docker-compose.prod.yml logs -f app

# Filter for specific request
docker-compose -f docker-compose.prod.yml logs app | grep "request_id:550e8400-e29b-41d4-a716-446655440000"

# Filter for LangChain events
docker-compose -f docker-compose.prod.yml logs app | grep "llm_start\|llm_end\|retriever_start\|chain_start"
```

**Limitations**:
- No long-term storage
- Limited search capabilities
- No visualization

### Option 2: File-Based Logging (Simple, Persistent)

**Best for**: Single server, basic persistence

**Setup**:

1. Update `.env` on EC2:
```bash
LOG_FILE=/app/logs/app.log
LOG_LEVEL=INFO
LOG_FORMAT=json
```

2. Mount log directory in `docker-compose.prod.yml`:
```yaml
services:
  app:
    volumes:
      - ./logs:/app/logs
```

3. Access logs:
```bash
# View logs
tail -f /path/to/logs/app.log

# Search for request ID
grep "550e8400-e29b-41d4-a716-446655440000" /path/to/logs/app.log

# Count LLM calls
grep -c "llm_start" /path/to/logs/app.log
```

**Limitations**:
- Manual log management
- Limited query capabilities
- No visualization

### Option 3: AWS CloudWatch Logs (Recommended for AWS EC2)

**Best for**: AWS deployments, integrated monitoring

**Setup**:

1. Install CloudWatch agent on EC2:
```bash
# Download CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
sudo rpm -U ./amazon-cloudwatch-agent.rpm
```

2. Configure CloudWatch to collect Docker logs:
```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/lib/docker/containers/*/*-json.log",
            "log_group_name": "/aws/ec2/chitalishta-ai-chat",
            "log_stream_name": "{instance_id}",
            "timezone": "UTC"
          }
        ]
      }
    }
  }
}
```

3. Query logs in CloudWatch:
```bash
# Using AWS CLI
aws logs filter-log-events \
  --log-group-name /aws/ec2/chitalishta-ai-chat \
  --filter-pattern "llm_start"

# Get logs for specific request
aws logs filter-log-events \
  --log-group-name /aws/ec2/chitalishta-ai-chat \
  --filter-pattern "550e8400-e29b-41d4-a716-446655440000"
```

**Benefits**:
- Automatic log aggregation
- Long-term storage
- Search and filtering
- Integration with AWS services

### Option 4: Grafana Loki (Self-Hosted, Powerful)

**Best for**: Self-hosted deployments, advanced querying

**Setup**:

1. Add Loki to `docker-compose.prod.yml`:
```yaml
services:
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - loki_data:/loki
    command: -config.file=/etc/loki/local-config.yaml

  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - ./promtail-config.yml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  loki_data:
  grafana_data:
```

2. Configure Promtail (`promtail-config.yml`):
```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        regex: '/(.*)'
        target_label: 'container'
```

3. Query logs using LogQL:
```logql
# All LLM calls
{container="chitalishta_ai_chat_app"} |= "llm_start"

# LLM calls for specific request
{container="chitalishta_ai_chat_app"} | json | request_id="550e8400-e29b-41d4-a716-446655440000"

# Average LLM latency
{container="chitalishta_ai_chat_app"} | json | event="llm_end" | unwrap duration_ms | avg()
```

**Benefits**:
- Powerful query language (LogQL)
- Grafana dashboards
- Real-time monitoring
- Cost-effective

### Option 5: ELK Stack (Elasticsearch, Logstash, Kibana)

**Best for**: Enterprise deployments, full-text search

**Setup**: Similar to Loki but uses Elasticsearch for storage and Kibana for visualization.

## Querying LangChain Logs

### Find All Operations for a Request

```bash
# Using grep (file-based or Docker logs)
grep "550e8400-e29b-41d4-a716-446655440000" logs/app.log

# Using jq (if logs are in file)
cat logs/app.log | jq 'select(.request_id == "550e8400-e29b-41d4-a716-446655440000")'
```

### Analyze LLM Performance

```bash
# Extract all LLM latencies
cat logs/app.log | jq 'select(.event == "llm_end") | {request_id, model, duration_ms, token_usage}'

# Calculate average LLM latency
cat logs/app.log | jq 'select(.event == "llm_end") | .duration_ms' | awk '{sum+=$1; count++} END {print sum/count}'

# Find slowest LLM calls
cat logs/app.log | jq 'select(.event == "llm_end") | {request_id, model, duration_ms}' | sort -t: -k3 -n | tail -10
```

### Track Token Usage

```bash
# Extract token usage for all LLM calls
cat logs/app.log | jq 'select(.event == "llm_end") | {request_id, model, token_usage}'

# Calculate total tokens used
cat logs/app.log | jq 'select(.event == "llm_end") | .token_usage.total_tokens' | awk '{sum+=$1} END {print sum}'
```

### Monitor Retrieval Operations

```bash
# Find all retrieval operations
cat logs/app.log | jq 'select(.event == "retriever_end") | {request_id, query, document_count, sources, duration_ms}'

# Find retrievals with most documents
cat logs/app.log | jq 'select(.event == "retriever_end") | {request_id, document_count}' | sort -t: -k2 -n | tail -10
```

### Track Chain Execution Flow

```bash
# Get full chain execution for a request
cat logs/app.log | jq 'select(.request_id == "550e8400-e29b-41d4-a716-446655440000") | {event, chain_name, duration_ms, timestamp}'

# Find slowest chains
cat logs/app.log | jq 'select(.event == "chain_end") | {chain_name, duration_ms}' | sort -t: -k2 -n | tail -10
```

## Example Analysis Script

Create a Python script to analyze logs:

```python
#!/usr/bin/env python3
"""Analyze LangChain observability logs."""

import json
import sys
from collections import defaultdict
from typing import Dict, List

def analyze_logs(log_file: str):
    """Analyze structured logs for LangChain operations."""

    llm_calls = []
    retrievals = []
    chains = []
    requests = defaultdict(list)

    with open(log_file, 'r') as f:
        for line in f:
            try:
                log = json.loads(line)
                event = log.get('event')
                request_id = log.get('request_id')

                if request_id:
                    requests[request_id].append(log)

                if event == 'llm_end':
                    llm_calls.append(log)
                elif event == 'retriever_end':
                    retrievals.append(log)
                elif event == 'chain_end':
                    chains.append(log)
            except json.JSONDecodeError:
                continue

    # Print statistics
    print(f"Total LLM calls: {len(llm_calls)}")
    if llm_calls:
        avg_latency = sum(l.get('duration_ms', 0) for l in llm_calls) / len(llm_calls)
        print(f"Average LLM latency: {avg_latency:.2f}ms")

    print(f"Total retrievals: {len(retrievals)}")
    if retrievals:
        avg_docs = sum(l.get('document_count', 0) for l in retrievals) / len(retrievals)
        print(f"Average documents per retrieval: {avg_docs:.2f}")

    print(f"Total chains: {len(chains)}")
    if chains:
        avg_chain_latency = sum(l.get('duration_ms', 0) for l in chains) / len(chains)
        print(f"Average chain latency: {avg_chain_latency:.2f}ms")

    # Find slowest request
    if requests:
        slowest = max(requests.items(), key=lambda x: sum(l.get('duration_ms', 0) for l in x[1]))
        print(f"\nSlowest request: {slowest[0]}")
        print(f"Total duration: {sum(l.get('duration_ms', 0) for l in slowest[1]):.2f}ms")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python analyze_logs.py <log_file>")
        sys.exit(1)
    analyze_logs(sys.argv[1])
```

## Production Recommendations

### For EC2 Deployment:

1. **Use CloudWatch Logs** (if on AWS):
   - Automatic log collection
   - Long-term retention
   - Integration with other AWS services

2. **Or use file-based logging with log rotation**:
   - Set `LOG_FILE=/app/logs/app.log` in environment
   - Mount logs directory as volume
   - Use log rotation (already configured)
   - Periodically archive old logs to S3

3. **Set appropriate log levels**:
   - Development: `LOG_LEVEL=DEBUG` (more verbose)
   - Production: `LOG_LEVEL=INFO` (balanced)
   - Troubleshooting: `LOG_LEVEL=DEBUG` temporarily

### Monitoring Key Metrics:

1. **Request latency**: Track `duration_ms` in `request_completed` events
2. **LLM performance**: Monitor `llm_end` events for latency and token usage
3. **Retrieval performance**: Track `retriever_end` for document count and latency
4. **Error rates**: Count `llm_error`, `retriever_error`, `chain_error` events
5. **Token usage**: Sum `token_usage.total_tokens` for cost tracking

### Alerting:

Set up alerts for:
- High error rates (`llm_error`, `chain_error` > threshold)
- Slow requests (`duration_ms` > threshold)
- High token usage (cost monitoring)
- Retrieval failures (`retriever_error`)

## Next Steps

For Step 10.3 (Performance monitoring), we'll add:
- Prometheus metrics endpoint
- Performance metrics collection
- System resource monitoring
- Cost tracking

This will complement the structured logging with real-time metrics and dashboards.

