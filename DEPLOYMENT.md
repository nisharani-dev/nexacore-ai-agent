# NexaCore Backend - Deployment Guide

## Overview

NexaCore is a production-ready onboarding assistant backend with database-backed persistence, authentication, observability, and cloud-native architecture.

**Key Features:**
- SQLite database with WAL mode for reliable persistence
- Session and audit trail management
- Hindsight memory backend with local JSON or HTTP cloud support
- Prometheus-compatible metrics and histograms
- FastAPI with CORS, middleware, and error handling
- Cloud-ready adapters for deployment on AWS Lambda, GCP Cloud Run, Kubernetes, or traditional VMs

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         NexaCore Backend                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │   FastAPI    │   │   Database   │   │   Hindsight  │        │
│  │   (server)   │──▶│   (SQLite)   │   │   Memory     │        │
│  └──────────────┘   └──────────────┘   └──────────────┘        │
│         │                                       │                │
│         │ HTTP Requests                         │ Local/HTTP     │
│         │                                       │                │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │ Auth/Session │   │ Observability│   │   Context    │        │
│  │   Handler    │   │   (Metrics)  │   │   Builder    │        │
│  └──────────────┘   └──────────────┘   └──────────────┘        │
│         │                                       │                │
│         └───────────────┬───────────────────────┘                │
│                         │                                        │
│                    Agent Processing                             │
│                   (LangGraph + Groq)                            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## System Requirements

- **Python**: 3.11 or later
- **Runtime**: 256 MB minimum memory, 500 MB disk for database
- **Network**: HTTPS for cloud deployments, HTTP for local/dev
- **Optional**: Groq API key for LLM functionality

## Local Development

### Setup

1. **Create Python environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   # or: venv\Scripts\activate  (Windows)
   ```

2. **Install dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Run server:**
   ```bash
   python -m backend.main
   # or: uvicorn backend.server:app --reload --port 8000
   ```

5. **Verify:**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/ready
   ```

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `PORT` | `8000` | HTTP server port |
| `APP_ENV` | `development` | Environment: `development` or `production` |
| `AUTH_REQUIRED` | `false` | Enforce authentication on all endpoints |
| `APP_API_KEY` | (none) | API key for token auth (Bearer or x-api-key) |
| `GROQ_API_KEY` | (none) | LLM API key for agent responses |
| `DATABASE_PATH` | `data/app.db` | SQLite database location |
| `HINDSIGHT_BACKEND` | `local` | Memory backend: `local` or `http` |
| `HINDSIGHT_PROJECT` | `ramp-onboarding-demo` | Project name for Hindsight |
| `HINDSIGHT_STORE_PATH` | `data/hindsight_store.json` | Local memory store path (for local backend) |
| `HINDSIGHT_BASE_URL` | (none) | Cloud API endpoint (for HTTP backend) |
| `HINDSIGHT_API_KEY` | (none) | Cloud API authentication key |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## Database Schema

The SQLite database includes the following tables:

### `tickets` - Support and blockers
```sql
CREATE TABLE tickets (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    assignee_team TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

**Indexes**: `assignee_team`, `status`, `created_at`

### `reminders` - Scheduled notifications
```sql
CREATE TABLE reminders (
    id TEXT PRIMARY KEY,
    recipient TEXT NOT NULL,
    message TEXT NOT NULL,
    due_in_hours INTEGER NOT NULL,
    scheduled_for TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

**Indexes**: `recipient`, `status`, `created_at`

### `sessions` - User sessions and profiles
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_name TEXT,
    team_name TEXT,
    role_title TEXT,
    employment_type TEXT,
    auth_subject TEXT,
    created_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);
```

**Indexes**: `team_name`, `employment_type`, `created_at`

### `audit_events` - Operational audit trail
```sql
CREATE TABLE audit_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    actor TEXT,
    session_id TEXT,
    request_id TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

**Indexes**: `event_type`, `session_id`, `created_at`

### `memory_metadata` - Memory backend tracking
```sql
CREATE TABLE memory_metadata (
    id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    level TEXT NOT NULL,
    source TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    backend_kind TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(content_hash, namespace)
);
```

**Indexes**: `namespace`, `level`, `source`, `created_at`

## API Endpoints

### Health & Readiness

- `GET /health` - Basic liveness check
- `GET /ready` - Detailed readiness probe (includes dependency checks)
- `GET /health-detailed` - Comprehensive health including metrics

### Observability

- `GET /metrics` - Prometheus exposition format metrics
- `GET /stats` - JSON-formatted metrics summary
- `GET /db-stats` - Database operational statistics

### Memory & Context

- `GET /memories?team={team}&employee_type={type}` - Retrieved context memories
- `GET /memory/summary` - Memory backend metadata

### Sessions

- `POST /sessions` - Create new session
- `GET /sessions` - List recent sessions
- `GET /sessions/{session_id}` - Get specific session

### Data Management

- `GET /tickets` - List all tickets
- `GET /reminders` - List all reminders
- `GET /audit` - List audit events

### Chat

- `POST /chat` - Main agent endpoint (see frontend integration)

### Maintenance

- `POST /demo/reset` - Reset demo data (development only)

## Deployment

### Docker (Production)

1. **Build image:**
   ```bash
   docker build -f backend/Dockerfile -t nexacore-backend:latest .
   ```

2. **Run container:**
   ```bash
   docker run -d \
     --name nexacore-backend \
     -p 8000:8000 \
     -e PORT=8000 \
     -e APP_ENV=production \
     -e AUTH_REQUIRED=true \
     -e APP_API_KEY=your-secret-key \
     -e GROQ_API_KEY=your-groq-key \
     -v /data:/app/data \
     nexacore-backend:latest
   ```

### AWS Lambda

1. **Package for Lambda:**
   ```bash
   pip install -r backend/requirements.txt -t ./python/lib/python3.11/site-packages/
   zip -r lambda-package.zip python/
   ```

2. **Deploy:**
   - Upload `lambda-package.zip` to AWS Lambda
   - Set handler: `backend.server.app` (with Mangum adapter)
   - Environment: Terraform-managed via `backend/Dockerfile`
   - Memory: 512 MB minimum recommended

3. **Terraform config example:**
   ```hcl
   resource "aws_lambda_function" "nexacore" {
     filename      = "lambda-package.zip"
     function_name = "nexacore-backend"
     role          = aws_iam_role.lambda_role.arn
     handler       = "index.handler"
     runtime       = "python3.11"
     timeout       = 30
     memory_size   = 512
     
     environment {
       variables = {
         APP_ENV         = "production"
         AUTH_REQUIRED   = "true"
         APP_API_KEY     = var.api_key
         GROQ_API_KEY    = var.groq_api_key
         HINDSIGHT_BACKEND = "http"
         HINDSIGHT_BASE_URL = aws_apigatewayv2_api.hindsight.api_endpoint
         HINDSIGHT_API_KEY = var.hindsight_api_key
       }
     }
   }
   ```

### Kubernetes

1. **Dockerfile (already provided):**
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY backend/requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   CMD ["python", "-m", "backend.main"]
   ```

2. **Kubernetes manifest:**
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: nexacore-backend
   spec:
     replicas: 2
     selector:
       matchLabels:
         app: nexacore-backend
     template:
       metadata:
         labels:
           app: nexacore-backend
       spec:
         containers:
         - name: backend
           image: nexacore-backend:latest
           ports:
           - containerPort: 8000
           env:
           - name: PORT
             value: "8000"
           - name: APP_ENV
             value: "production"
           - name: AUTH_REQUIRED
             value: "true"
           - name: APP_API_KEY
             valueFrom:
               secretKeyRef:
                 name: nexacore-secrets
                 key: api-key
           - name: GROQ_API_KEY
             valueFrom:
               secretKeyRef:
                 name: nexacore-secrets
                 key: groq-api-key
           livenessProbe:
             httpGet:
               path: /health
               port: 8000
             initialDelaySeconds: 10
             periodSeconds: 30
           readinessProbe:
             httpGet:
               path: /ready
               port: 8000
             initialDelaySeconds: 5
             periodSeconds: 10
           volumeMounts:
           - name: data
             mountPath: /app/data
         volumes:
         - name: data
           emptyDir: {}  # Or use persistent volume
   ```

3. **Service:**
   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: nexacore-backend
   spec:
     selector:
       app: nexacore-backend
     type: LoadBalancer
     ports:
     - protocol: TCP
       port: 80
       targetPort: 8000
   ```

## Monitoring

### Prometheus Integration

1. **Scrape config:**
   ```yaml
   scrape_configs:
     - job_name: 'nexacore-backend'
       static_configs:
         - targets: ['localhost:8000']
       metrics_path: '/metrics'
   ```

2. **Key metrics:**
   - `http_requests_total` - HTTP request count by method/path/status
   - `http_request_duration_ms` - Histogram of request latency
   - `sessions_created_total` - Session creation count
   - `tickets_total` - Current ticket count
   - `reminders_total` - Current reminder count
   - `memory_records_total` - Memory backend record count

### Alerting

Example Prometheus alert rules:

```yaml
groups:
  - name: nexacore
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_failed_total[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
      
      - alert: DatabaseUnhealthy
        expr: up{job="nexacore-backend"} == 0
        for: 1m
        annotations:
          summary: "Backend is down"
      
      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_ms) > 1000
        for: 5m
        annotations:
          summary: "P95 latency exceeding 1s"
```

### Logs

View logs with:

```bash
# Docker
docker logs -f nexacore-backend

# Kubernetes
kubectl logs -f deployment/nexacore-backend

# Local development
# Logs output to stdout/stderr, captured by uvicorn
```

Log format: `TIMESTAMP | LEVEL | NAME | MESSAGE`

## Backup & Disaster Recovery

### Database Backup

1. **Manual backup:**
   ```bash
   sqlite3 data/app.db ".backup data/app.db.backup"
   ```

2. **Automated backups (Kubernetes):**
   ```yaml
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: nexacore-backup
   spec:
     schedule: "0 2 * * *"  # Daily at 2 AM
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: backup
               image: sqlite
               command:
                 - /bin/sh
                 - -c
                 - sqlite3 /data/app.db ".backup /backups/app.db.$(date +%Y%m%d)"
               volumeMounts:
               - name: data
                 mountPath: /data
               - name: backups
                 mountPath: /backups
             volumes:
             - name: data
               persistentVolumeClaim:
                 claimName: nexacore-data
             - name: backups
               persistentVolumeClaim:
                 claimName: nexacore-backups
   ```

3. **Point-in-time recovery:**
   ```bash
   # SQLite maintains WAL (Write-Ahead Log)
   # To recover to a point in time, use the WAL files
   # WAL files: app.db-wal, app.db-shm
   ```

### Memory Backend Backup

For local JSON backend, backup `data/hindsight_store.json`:

```bash
cp data/hindsight_store.json data/hindsight_store.json.backup
```

For HTTP backend, backups are handled by the cloud provider.

## Troubleshooting

### Database Locked

**Error:** `sqlite3.OperationalError: database is locked`

**Solution:**
```bash
# WAL mode should prevent this, but if it occurs:
# 1. Stop the service
# 2. Delete -wal and -shm files
# 3. Restart

rm data/app.db-wal data/app.db-shm
```

### Memory Backend Connection Failure

**Error:** `EnvironmentError: Hindsight HTTP backend selected but HINDSIGHT_BASE_URL or HINDSIGHT_API_KEY is missing`

**Solution:** Verify environment variables are set:
```bash
echo $HINDSIGHT_BASE_URL
echo $HINDSIGHT_API_KEY
```

### High Latency

**Diagnose:**
1. Check `/stats` endpoint for histogram metrics
2. Look for slow queries in logs
3. Verify database indexes exist: `sqlite3 data/app.db ".indices"`

**Solutions:**
- Increase database cache: `PRAGMA cache_size=10000`
- Add indexes for frequently filtered columns
- Consider pagination for large result sets

### Authentication Failures

**Enable debug logging:**
```bash
LOG_LEVEL=DEBUG python -m backend.main
```

Check for:
- Missing `Authorization` or `x-api-key` headers
- Incorrect API key format
- Session ID format/validity

## Performance Tuning

### Database

```python
# In backend/db.py, these are already configured:
PRAGMA journal_mode=WAL;          # Enable write-ahead logging
PRAGMA synchronous=NORMAL;        # Balance speed vs safety
PRAGMA cache_size=10000;          # Larger in-memory cache
```

### Application

- Connection pooling: FastAPI + SQLite is single-threaded; use connection context manager
- Async processing: Use background tasks for long operations
- Caching: Add Redis for session caching in high-scale deployments

## Security

### API Authentication

Enable auth in production:

```bash
export AUTH_REQUIRED=true
export APP_API_KEY=your-strong-secret-key-min-32-chars
```

Request with:
```bash
curl -H "x-api-key: your-strong-secret-key-min-32-chars" \
  http://localhost:8000/chat
```

Or Bearer token:
```bash
curl -H "Authorization: Bearer your-strong-secret-key-min-32-chars" \
  http://localhost:8000/chat
```

### HTTPS

Use a reverse proxy (Nginx, CloudFlare, AWS ALB) to terminate TLS:

```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    ssl_certificate /etc/ssl/certs/your-cert.pem;
    ssl_certificate_key /etc/ssl/private/your-key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Database Encryption

SQLite can be encrypted with `sqlcipher`, but adds overhead:

```bash
pip install pysqlcipher3
# Then update backend/db.py to use cipher
```

### Audit Logging

All meaningful operations are logged to the `audit_events` table with:
- `event_type`: What happened (chat, session.created, etc.)
- `actor`: Who triggered it (auth subject)
- `session_id`: Associated session
- `payload_json`: Full event details

Query audit logs:
```bash
curl http://localhost:8000/audit
```

## Scaling

### Vertical Scaling

- **CPU**: Agent processing is primarily single-threaded; multiple replicas more effective than CPU scaling
- **Memory**: Increase for larger in-memory database cache and metrics histograms
- **Disk**: Database grows ~1 MB per 10k audit events; plan for growth

### Horizontal Scaling

1. **Stateless backend instances:**
   - All state in external SQLite (shared volume) or cloud database
   - Stateless memory (no session affinity needed)
   - Load balance across instances

2. **Shared database approach (Kubernetes):**
   ```yaml
   # Use persistent volume for database
   volumeMounts:
   - name: data
     mountPath: /app/data
   volumes:
   - name: data
     persistentVolumeClaim:
       claimName: nexacore-data
   ```

3. **Cloud database migration (future):**
   - Port from SQLite to PostgreSQL
   - Update `backend/db.py` to use `psycopg` driver
   - Scale horizontally without shared storage

### Caching Layer

Add Redis for:
- Session caching (hot reads)
- Memory search result caching
- Metrics aggregation

```python
# Future enhancement in backend/cache.py
from redis import Redis
cache = Redis(host='localhost', port=6379, db=0)
```

## Support & Issues

### Get Help

1. Check logs: `LOG_LEVEL=DEBUG python -m backend.main`
2. Test endpoints: `curl http://localhost:8000/health-detailed`
3. Review metrics: `curl http://localhost:8000/stats`
4. Check database: `sqlite3 data/app.db "SELECT * FROM audit_events LIMIT 5;"`

### Report Issues

Include:
- Error logs (`LOG_LEVEL=DEBUG`)
- Metrics output (`/stats`)
- Database state (last 10 audit events)
- Environment configuration (sanitized)

## Version History

- **1.0.0** (current): Production-ready backend with database persistence, auth, observability

## License

Proprietary - NexaCore Internal Use Only
