# Deployment Guide

This guide covers every deployment topology for NeuralCore — from a single-developer local setup to a production-grade Kubernetes cluster handling millions of requests per day. Read the section that matches your deployment target.

---

## 1. Deployment Architectures

### 1.1 Single-Node (Development)

```
┌─────────────────────────────────────────────────────┐
│                   Single Machine                    │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐│
│  │ Frontend │  │   API    │  │      Workers       ││
│  │ Next.js  │  │ FastAPI  │  │  Celery (4 workers)││
│  │ :5242    │  │  :8000   │  │                    ││
│  └──────────┘  └──────────┘  └────────────────────┘│
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐│
│  │PostgreSQL│  │  Redis   │  │       Qdrant       ││
│  │  :5432   │  │  :6379   │  │       :6333        ││
│  └──────────┘  └──────────┘  └────────────────────┘│
└─────────────────────────────────────────────────────┘
```

### 1.2 Multi-Node Production (Recommended)

```
                         Internet
                            │
                    ┌───────▼────────┐
                    │  Load Balancer │  (AWS ALB / Nginx / Caddy)
                    │  TLS Termination│
                    └───────┬────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
       ┌──────▼──┐   ┌──────▼──┐   ┌──────▼──┐
       │  API-1  │   │  API-2  │   │  API-3  │    (Stateless, N replicas)
       │ :8000   │   │ :8000   │   │ :8000   │
       └─────────┘   └─────────┘   └─────────┘
              │             │             │
              └──────────┬──────────────┘
                         │
        ┌────────────────┼─────────────────┐
        │                │                 │
┌───────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
│  PostgreSQL  │  │    Redis    │  │    Qdrant   │
│  Primary +   │  │  Sentinel / │  │   Cluster   │
│  2 Replicas  │  │  Cluster    │  │  3 nodes    │
└──────────────┘  └─────────────┘  └─────────────┘
        │
┌───────▼──────┐
│   Workers    │
│ Celery w/    │
│ autoscaling  │
└──────────────┘
```

---

## 2. Prerequisites

### Hardware Minimums

| Role | CPU | RAM | Disk | Notes |
|------|-----|-----|------|-------|
| Development | 4 cores | 8 GB | 50 GB SSD | Single node |
| Small production | 8 cores | 16 GB | 200 GB SSD | Up to 10K req/day |
| Medium production | 16 cores | 32 GB | 500 GB NVMe | Up to 500K req/day |
| Qdrant node | 8 cores | 32 GB | 1 TB NVMe | Per million vectors |
| Worker node | 4 cores | 8 GB | 50 GB | Per 10 concurrent tasks |

### Software Requirements

```bash
# Required
docker >= 24.0
docker compose >= 2.20
git >= 2.40

# For Kubernetes deployment
kubectl >= 1.28
helm >= 3.12

# For local development (without Docker)
python >= 3.12
node >= 20.0
npm >= 10.0
```

---

## 3. Local Development (Docker Compose)

The fastest way to get a full NeuralCore stack running locally.

### 3.1 Clone & Configure

```bash
git clone https://github.com/yourorg/neuralcore.git
cd NeuralCore

# Copy environment templates
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

### 3.2 Set Required Secrets

Edit `.env`:

```bash
# Required: at least one LLM provider
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...

# Required: JWT secret (generate with: openssl rand -base64 32)
JWT_SECRET_KEY=your-super-secret-jwt-key-minimum-32-characters
```

### 3.3 Start the Stack

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f api

# Check health
curl http://localhost:8000/health
```

### 3.4 Initialize the Database

```bash
# Run migrations
docker compose exec api alembic upgrade head

# Seed development data (optional)
docker compose exec api python scripts/seed_dev_data.py
```

### 3.5 Start Frontend (separately, for HMR)

```bash
cd frontend
npm install
npm run dev
# Available at http://localhost:5242
```

### 3.6 Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:5242 | admin@neuralcore.com / admin |
| API | http://localhost:8000 | — |
| API Docs | http://localhost:8000/docs | — |
| Grafana | http://localhost:3001 | admin / admin |
| Prometheus | http://localhost:9090 | — |
| Qdrant UI | http://localhost:6333/dashboard | — |

### 3.7 Stop & Clean Up

```bash
# Stop all services
docker compose down

# Stop and delete all data (volumes)
docker compose down -v

# Rebuild images
docker compose build --no-cache api
```

---

## 4. Self-Hosted Production (Docker Compose)

For teams deploying on a single VM or bare-metal server with production hardening.

### 4.1 System Preparation

```bash
# Ubuntu 22.04 LTS recommended
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt install docker-compose-plugin

# Configure system limits
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
echo "fs.file-max=65536" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 4.2 Create docker-compose.prod.yml

Create a production override file:

```yaml
# docker-compose.prod.yml
version: '3.9'

services:
  api:
    image: ghcr.io/yourorg/neuralcore-api:${VERSION:-latest}
    restart: always
    environment:
      NEURALCORE_ENV: production
      WORKERS: "8"
      LOG_LEVEL: info
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"

  workers:
    image: ghcr.io/yourorg/neuralcore-worker:${VERSION:-latest}
    restart: always
    environment:
      NEURALCORE_ENV: production
    command: celery -A workers.tasks worker --loglevel=info --concurrency=8
    deploy:
      resources:
        limits:
          cpus: '8'
          memory: 16G

  postgres:
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - /data/postgres:/var/lib/postgresql/data

  redis:
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --appendonly yes
      --maxmemory 4gb
      --maxmemory-policy allkeys-lru
      --save 900 1
      --save 300 10
```

### 4.3 Production Startup

```bash
# Deploy
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Run migrations
docker compose exec api alembic upgrade head

# Verify
docker compose ps
curl https://your-domain.com/health
```

### 4.4 Automatic Updates

```bash
# /etc/cron.d/neuralcore-update
0 2 * * * /opt/neuralcore/scripts/update.sh >> /var/log/neuralcore-update.log 2>&1
```

```bash
#!/bin/bash
# scripts/update.sh
set -e

cd /opt/neuralcore

# Pull latest images
docker compose pull

# Rolling restart
docker compose up -d --no-deps api
sleep 10
docker compose exec api alembic upgrade head
docker compose up -d --no-deps workers

echo "Update complete at $(date)"
```

---

## 5. Kubernetes Deployment

### 5.1 Helm Chart Installation

```bash
# Add the NeuralCore Helm repo
helm repo add neuralcore https://charts.neuralcore.ai
helm repo update

# Create namespace
kubectl create namespace neuralcore

# Create secrets
kubectl create secret generic neuralcore-secrets \
  --from-literal=jwt-secret="$(openssl rand -base64 32)" \
  --from-literal=openai-api-key="sk-proj-..." \
  --from-literal=database-password="$(openssl rand -base64 24)" \
  --from-literal=redis-password="$(openssl rand -base64 24)" \
  -n neuralcore

# Install
helm install neuralcore neuralcore/neuralcore \
  --namespace neuralcore \
  --values values.prod.yaml
```

### 5.2 values.prod.yaml

```yaml
global:
  environment: production
  imageTag: "1.4.2"
  imagePullPolicy: IfNotPresent

api:
  replicaCount: 3
  image:
    repository: ghcr.io/yourorg/neuralcore-api
  resources:
    requests:
      cpu: "500m"
      memory: "1Gi"
    limits:
      cpu: "2000m"
      memory: "4Gi"
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80
  podDisruptionBudget:
    enabled: true
    minAvailable: 2
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector:
            matchExpressions:
              - key: app
                operator: In
                values: ["neuralcore-api"]
          topologyKey: kubernetes.io/hostname

workers:
  replicaCount: 2
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 80
  celery:
    concurrency: 8
    queues: ["default", "high_priority", "ingestion"]

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
  hosts:
    - host: api.neuralcore.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: neuralcore-api-tls
      hosts:
        - api.neuralcore.yourdomain.com

postgresql:
  enabled: true
  primary:
    persistence:
      size: 100Gi
      storageClass: gp3
  readReplicas:
    replicaCount: 2

redis:
  enabled: true
  architecture: replication
  sentinel:
    enabled: true

qdrant:
  enabled: true
  replicaCount: 3
  persistence:
    size: 500Gi

monitoring:
  prometheus:
    enabled: true
  grafana:
    enabled: true
  loki:
    enabled: true
```

### 5.3 Verify Deployment

```bash
# Check all pods
kubectl get pods -n neuralcore

# Check API health
kubectl port-forward svc/neuralcore-api 8000:8000 -n neuralcore
curl http://localhost:8000/health

# View logs
kubectl logs -l app=neuralcore-api -n neuralcore --tail=100 -f

# Run migrations
kubectl exec -it deploy/neuralcore-api -n neuralcore -- alembic upgrade head
```

---

## 6. Cloud Provider Guides

### 6.1 AWS (EKS + RDS + ElastiCache)

```bash
# Create EKS cluster
eksctl create cluster \
  --name neuralcore-prod \
  --region us-east-1 \
  --nodegroup-name api-nodes \
  --node-type m6i.xlarge \
  --nodes 3 \
  --nodes-min 3 \
  --nodes-max 10 \
  --managed

# Create RDS PostgreSQL
aws rds create-db-instance \
  --db-instance-identifier neuralcore-postgres \
  --db-instance-class db.r6g.xlarge \
  --engine postgres \
  --engine-version 15 \
  --master-username neuralcore \
  --master-user-password "$DB_PASSWORD" \
  --allocated-storage 200 \
  --storage-type gp3 \
  --multi-az \
  --backup-retention-period 7

# Create ElastiCache Redis
aws elasticache create-replication-group \
  --replication-group-id neuralcore-redis \
  --replication-group-description "NeuralCore Redis" \
  --cache-node-type cache.r6g.large \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-clusters 3 \
  --automatic-failover-enabled

# Update Helm values to use managed services
helm upgrade neuralcore neuralcore/neuralcore \
  --set postgresql.enabled=false \
  --set postgresql.externalHost="neuralcore-postgres.xxxx.us-east-1.rds.amazonaws.com" \
  --set redis.enabled=false \
  --set redis.externalHost="neuralcore-redis.xxxx.ng.0001.use1.cache.amazonaws.com"
```

### 6.2 GCP (GKE + Cloud SQL + Memorystore)

```bash
# Create GKE cluster
gcloud container clusters create neuralcore-prod \
  --zone us-central1-a \
  --machine-type n2-standard-4 \
  --num-nodes 3 \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 15 \
  --enable-autorepair \
  --enable-autoupgrade

# Create Cloud SQL
gcloud sql instances create neuralcore-postgres \
  --database-version=POSTGRES_15 \
  --tier=db-custom-4-16384 \
  --region=us-central1 \
  --availability-type=REGIONAL \
  --backup-start-time=02:00
```

### 6.3 Azure (AKS + Azure Database + Azure Cache)

```bash
# Create AKS cluster
az aks create \
  --resource-group neuralcore-rg \
  --name neuralcore-prod \
  --node-count 3 \
  --node-vm-size Standard_D4s_v3 \
  --enable-cluster-autoscaler \
  --min-count 3 \
  --max-count 15

# Create Azure Database for PostgreSQL
az postgres flexible-server create \
  --resource-group neuralcore-rg \
  --name neuralcore-postgres \
  --sku-name Standard_D4s_v3 \
  --tier GeneralPurpose \
  --version 15 \
  --high-availability ZoneRedundant
```

---

## 7. Database Setup & Migrations

### 7.1 Initial Setup

```bash
# Connect to PostgreSQL
psql -h localhost -U neuralcore -d neuralcore

# Verify extensions
SELECT * FROM pg_extension;
# Should show: uuid-ossp, pgcrypto, pg_trgm, vector (if using pgvector)

# Run all migrations
alembic upgrade head

# Verify migration status
alembic current
alembic history
```

### 7.2 Running Migrations in Production

**Never run migrations directly on production.** Always:

1. Test migration on staging first
2. Take a database backup
3. Run migrations during low-traffic window
4. Have rollback ready

```bash
# Step 1: Backup
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -F c -f backup_$(date +%Y%m%d_%H%M%S).dump

# Step 2: Test migration
psql -h staging-db -U neuralcore -c "SELECT version FROM alembic_version"
alembic --config alembic.staging.ini upgrade head

# Step 3: Production migration
kubectl exec -it deploy/neuralcore-api -n neuralcore -- alembic upgrade head

# Step 4: Verify
kubectl exec -it deploy/neuralcore-api -n neuralcore -- alembic current
```

### 7.3 Rollback

```bash
# Roll back one migration
alembic downgrade -1

# Roll back to specific revision
alembic downgrade abc123def456

# List available revisions
alembic history --verbose
```

### 7.4 PostgreSQL Row-Level Security

NeuralCore uses PostgreSQL RLS for tenant isolation. Enable it:

```sql
-- Enable RLS on all tenant-scoped tables
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_bases ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE runs ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY tenant_isolation ON agents
  USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

---

## 8. Environment Variables Reference

### Core Application

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEURALCORE_ENV` | Yes | `development` | `development`, `staging`, `production` |
| `JWT_SECRET_KEY` | Yes | — | Min 32 chars. Use `openssl rand -base64 32` |
| `LOG_LEVEL` | No | `info` | `debug`, `info`, `warning`, `error` |
| `API_HOST` | No | `0.0.0.0` | Host to bind to |
| `API_PORT` | No | `8000` | Port to listen on |
| `WORKERS` | No | `4` | Uvicorn worker processes |

### Database

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_HOST` | Yes | PostgreSQL hostname |
| `DATABASE_PORT` | No | Default: `5432` |
| `DATABASE_NAME` | Yes | Database name |
| `DATABASE_USER` | Yes | Database user |
| `DATABASE_PASSWORD` | Yes | Database password |
| `DATABASE_POOL_SIZE` | No | Default: `20` |
| `DATABASE_MAX_OVERFLOW` | No | Default: `40` |
| `DATABASE_SSL_MODE` | No | `disable`/`require`/`verify-full` |

### Redis

| Variable | Required | Description |
|----------|----------|-------------|
| `REDIS_HOST` | Yes | Redis hostname |
| `REDIS_PORT` | No | Default: `6379` |
| `REDIS_PASSWORD` | Yes | Redis password |
| `REDIS_DB` | No | Default: `0` |
| `REDIS_MAX_CONNECTIONS` | No | Default: `100` |

### Qdrant

| Variable | Required | Description |
|----------|----------|-------------|
| `QDRANT_HOST` | Yes | Qdrant hostname |
| `QDRANT_PORT` | No | Default: `6333` |
| `QDRANT_API_KEY` | Yes | Qdrant API key |
| `QDRANT_GRPC_PORT` | No | Default: `6334` |

### LLM Providers

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | If using OpenAI | `sk-proj-...` |
| `OPENAI_ORGANIZATION` | No | OpenAI org ID |
| `ANTHROPIC_API_KEY` | If using Anthropic | `sk-ant-...` |
| `COHERE_API_KEY` | If using Cohere | Cohere key |
| `MISTRAL_API_KEY` | If using Mistral | Mistral key |
| `DEFAULT_LLM_PROVIDER` | No | Default: `openai` |
| `DEFAULT_LLM_MODEL` | No | Default: `gpt-4o` |

### Celery Workers

| Variable | Required | Description |
|----------|----------|-------------|
| `CELERY_BROKER_URL` | Yes | `redis://:password@host:6379/0` |
| `CELERY_RESULT_BACKEND` | Yes | `redis://:password@host:6379/1` |
| `WORKER_CONCURRENCY` | No | Default: `8` |
| `WORKER_TIME_LIMIT` | No | Default: `3600` (seconds) |

---

## 9. TLS & Reverse Proxy

### 9.1 Caddy (Recommended — automatic TLS)

```
# /etc/caddy/Caddyfile

api.yourdomain.com {
    reverse_proxy localhost:8000 {
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        transport http {
            response_header_timeout 300s
        }
    }
    
    # SSE streaming support
    @sse path /api/v1/agents/*/stream
    header @sse Cache-Control no-cache
    
    encode zstd gzip
    
    log {
        output file /var/log/caddy/access.log
        format json
    }
}
```

```bash
# Install Caddy
sudo apt install caddy

# Start
sudo systemctl enable caddy
sudo systemctl start caddy
```

### 9.2 Nginx

```nginx
# /etc/nginx/sites-available/neuralcore
upstream neuralcore_api {
    server 127.0.0.1:8000 weight=1 max_fails=3 fail_timeout=30s;
    keepalive 64;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    ssl_session_cache   shared:SSL:10m;

    client_max_body_size 100m;
    
    # SSE streaming
    location ~ ^/api/v1/agents/.*/stream {
        proxy_pass http://neuralcore_api;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_set_header X-Accel-Buffering no;
        proxy_read_timeout 600s;
        proxy_buffering off;
        chunked_transfer_encoding on;
    }

    location / {
        proxy_pass http://neuralcore_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 10s;
        proxy_send_timeout 120s;
    }
    
    location /health {
        proxy_pass http://neuralcore_api;
        access_log off;
    }
}
```

---

## 10. Secret Management

### 10.1 HashiCorp Vault (Recommended)

```bash
# Configure Vault AppRole auth
vault auth enable approle
vault write auth/approle/role/neuralcore-api \
  secret_id_ttl=24h \
  token_num_uses=0 \
  token_ttl=1h \
  token_max_ttl=4h \
  bound_cidr_list="10.0.0.0/8"

# Store secrets
vault kv put secret/neuralcore/production \
  openai_api_key="sk-proj-..." \
  jwt_secret_key="$(openssl rand -base64 32)" \
  database_password="$(openssl rand -base64 24)"
```

In your application, read secrets at startup:

```python
import hvac

def get_secrets():
    client = hvac.Client(url=os.getenv("VAULT_ADDR"))
    client.auth.approle.login(
        role_id=os.getenv("VAULT_ROLE_ID"),
        secret_id=os.getenv("VAULT_SECRET_ID"),
    )
    return client.secrets.kv.read_secret_version(
        path="neuralcore/production"
    )["data"]["data"]
```

### 10.2 AWS Secrets Manager

```python
import boto3, json

def get_secret(secret_name: str) -> dict:
    client = boto3.client("secretsmanager", region_name="us-east-1")
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])
```

### 10.3 Kubernetes Secrets (Basic)

```bash
kubectl create secret generic neuralcore-app-secrets \
  --from-literal=jwt-secret="$(openssl rand -base64 32)" \
  --from-literal=openai-api-key="sk-proj-..." \
  -n neuralcore

# Reference in deployment
env:
  - name: JWT_SECRET_KEY
    valueFrom:
      secretKeyRef:
        name: neuralcore-app-secrets
        key: jwt-secret
```

---

## 11. Scaling & High Availability

### 11.1 API Scaling

The API is **stateless** — scale horizontally by adding replicas. All session state is in Redis, all data is in PostgreSQL/Qdrant.

```bash
# Docker Compose
docker compose up -d --scale api=5

# Kubernetes
kubectl scale deployment neuralcore-api --replicas=10 -n neuralcore

# HPA already configured via Helm values
kubectl get hpa -n neuralcore
```

### 11.2 Worker Scaling

Workers are CPU/IO-bound. Scale based on queue depth:

```bash
# Monitor queue depth
docker compose exec redis redis-cli -a $REDIS_PASSWORD LLEN celery

# Scale workers
docker compose up -d --scale workers=8
```

For Kubernetes, use KEDA (Kubernetes Event-Driven Autoscaler):

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: neuralcore-workers
  namespace: neuralcore
spec:
  scaleTargetRef:
    name: neuralcore-workers
  minReplicaCount: 2
  maxReplicaCount: 20
  triggers:
    - type: redis
      metadata:
        address: neuralcore-redis:6379
        listName: celery
        listLength: "5"
```

### 11.3 Database HA

**PostgreSQL:**
- Use streaming replication (1 primary + 2 read replicas minimum)
- Use connection pooling with PgBouncer (NeuralCore includes it in the Helm chart)
- Failover via Patroni or managed DB failover (RDS Multi-AZ)

**Redis:**
- Use Redis Sentinel (minimum 3 nodes) for automatic failover
- Or Redis Cluster for horizontal scaling

**Qdrant:**
- Use Qdrant cluster mode with 3+ nodes
- Enable replication factor ≥ 2 for all collections

---

## 12. Backup & Disaster Recovery

### 12.1 PostgreSQL Backup

```bash
# Daily backup script
#!/bin/bash
# /etc/cron.d/neuralcore-db-backup

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backups/postgres

pg_dump \
  -h "$DATABASE_HOST" \
  -U "$DATABASE_USER" \
  -d "$DATABASE_NAME" \
  -F c \
  -Z 9 \
  -f "$BACKUP_DIR/neuralcore_$TIMESTAMP.dump"

# Upload to S3
aws s3 cp "$BACKUP_DIR/neuralcore_$TIMESTAMP.dump" \
  "s3://neuralcore-backups/postgres/"

# Retain 30 days
find "$BACKUP_DIR" -mtime +30 -delete
```

### 12.2 Qdrant Snapshot

```bash
# Create snapshot
curl -X POST "http://localhost:6333/collections/my_collection/snapshots"

# List snapshots
curl "http://localhost:6333/collections/my_collection/snapshots"

# Upload to S3
aws s3 sync /qdrant/storage/snapshots/ s3://neuralcore-backups/qdrant/
```

### 12.3 Recovery RTO/RPO Targets

| Component | RPO (data loss) | RTO (recovery time) |
|-----------|-----------------|---------------------|
| PostgreSQL | < 5 minutes (WAL streaming) | < 10 minutes |
| Redis | < 1 second (AOF enabled) | < 2 minutes |
| Qdrant | < 24 hours (daily snapshot) | < 30 minutes |
| App containers | 0 (stateless) | < 2 minutes |

---

## 13. Monitoring Stack

The monitoring stack includes Prometheus, Grafana, and Loki. See the docker-compose.yml — all services are pre-configured.

### 13.1 Key Dashboards (Grafana)

- **NeuralCore Overview** — Request rate, error rate, latency P50/P95/P99
- **Agent Performance** — Run success rate, avg steps, cost per run, top agents
- **LLM Usage** — Token usage, cost by provider/model, API errors
- **Infrastructure** — CPU/RAM/disk for all services
- **Database** — Query performance, connections, replication lag
- **Queue Health** — Celery task rate, queue depth, worker utilization

### 13.2 Critical Alerts

Configure in Prometheus:

```yaml
# infrastructure/monitoring/alerts.yml
groups:
  - name: neuralcore_critical
    rules:
      - alert: APIHighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "API error rate > 5%"

      - alert: DatabaseConnectionsHigh
        expr: pg_stat_activity_count > 150
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "PostgreSQL connections approaching limit"

      - alert: AgentRunQueueDepth
        expr: celery_queue_length{queue="default"} > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Agent run queue depth > 1000"
```

---

## 14. Upgrades & Rollbacks

### 14.1 Rolling Upgrade (Zero Downtime)

```bash
# 1. Pull new images
docker compose pull

# 2. Rolling restart API (one at a time if using multiple compose files)
docker compose up -d --no-deps --scale api=3 api
sleep 30
docker compose exec api alembic upgrade head

# 3. Restart workers (after API is confirmed healthy)
docker compose up -d --no-deps workers

# Kubernetes — automatic via rolling update strategy
kubectl set image deployment/neuralcore-api \
  api=ghcr.io/yourorg/neuralcore-api:1.5.0 \
  -n neuralcore
kubectl rollout status deployment/neuralcore-api -n neuralcore
```

### 14.2 Rollback

```bash
# Docker Compose — revert to previous image tag
VERSION=1.4.2 docker compose up -d api workers

# Kubernetes
kubectl rollout undo deployment/neuralcore-api -n neuralcore
kubectl rollout undo deployment/neuralcore-workers -n neuralcore

# Database rollback
alembic downgrade -1
```

### 14.3 Pre-Upgrade Checklist

- [ ] Read the [CHANGELOG](CHANGELOG.md) for breaking changes
- [ ] Take database snapshot
- [ ] Test on staging
- [ ] Confirm rollback plan
- [ ] Notify team of maintenance window
- [ ] Monitor error rate for 30 minutes after upgrade

---

## 15. Troubleshooting

### API Won't Start

```bash
# Check logs
docker compose logs api --tail=50

# Common causes:
# 1. Cannot connect to database
docker compose exec api python -c "from core.database import engine; print(engine.execute('SELECT 1').scalar())"

# 2. Missing environment variables
docker compose exec api python -c "from core.config import settings; print(settings.dict())"

# 3. Migration not applied
docker compose exec api alembic current
```

### Workers Failing to Start

```bash
# Check Celery logs
docker compose logs workers --tail=50

# Test Celery connection manually
docker compose exec workers celery -A workers.tasks inspect ping

# Verify Redis connection
docker compose exec workers python -c "
import redis
r = redis.Redis(host='redis', port=6379, password='$REDIS_PASSWORD')
print(r.ping())
"
```

### CORS Errors (Frontend → API)

CORS errors almost always mean the frontend and backend are running in different modes simultaneously. Checklist:

1. Is Docker API running AND local uvicorn running? Kill one.
2. Is `NEXT_PUBLIC_API_URL` in `frontend/.env.local` pointing to the right port?
3. Does the backend's `CORS_ORIGINS` include the frontend URL?

```bash
# Check what's on port 8000
netstat -tlnp | grep 8000

# Verify CORS config in running API
curl -i -X OPTIONS http://localhost:8000/api/v1/agents \
  -H "Origin: http://localhost:5242" \
  -H "Access-Control-Request-Method: GET"
# Should return 200 with Access-Control-Allow-Origin header
```

### Database Connection Pool Exhausted

```bash
# Check current connections
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c \
  "SELECT count(*), state FROM pg_stat_activity GROUP BY state"

# Increase pool size (in env)
DATABASE_POOL_SIZE=40
DATABASE_MAX_OVERFLOW=80

# Emergency: kill idle connections
psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
         WHERE state = 'idle' AND query_start < NOW() - INTERVAL '10 minutes'"
```

### Qdrant Collection Not Found

```bash
# List all collections
curl http://localhost:6333/collections

# Recreate collection from KB
docker compose exec api python -m scripts.rebuild_vector_index --kb-id kb_xyz789
```

### High Memory Usage

```bash
# Check container memory
docker stats --no-stream

# Common causes:
# 1. Celery workers not restarting after task limit
WORKER_MAX_TASKS_PER_CHILD=1000  # Already set in docker-compose

# 2. Qdrant index not fitted to available RAM
# Reduce payload index or use disk-based storage for cold data
curl -X PATCH http://localhost:6333/collections/my_collection \
  -d '{"optimizers_config": {"indexing_threshold": 0}}'
```

---

*For deployment support, enterprise licensing, or managed hosting inquiries, contact [deploy@neuralcore.ai](mailto:deploy@neuralcore.ai).*
