# BHIV Core Production Deployment Instructions

## 🚀 Complete Deployment Guide

This guide provides step-by-step instructions to deploy the production-ready BHIV Core system.

## 📋 Pre-Deployment Checklist

### System Requirements
- **OS**: Linux/Windows/macOS
- **Docker**: 20.10+ with Docker Compose
- **Python**: 3.11+
- **Memory**: 8GB+ RAM recommended
- **Storage**: 50GB+ available space
- **Network**: Internet access for external APIs

### Required Environment Variables
Create `.env` file with these variables:

```env
# Database Configuration
POSTGRES_PASSWORD=SecurePassword123!
DATABASE_URL=postgresql://bhiv_user:SecurePassword123!@postgres:5432/bhiv_core

# Security Configuration
JWT_SECRET_KEY=super-secret-jwt-key-for-production-change-this
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI API Keys
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Redis Configuration
REDIS_URL=redis://redis:6379

# Monitoring Configuration
PROMETHEUS_URL=http://prometheus:9090
GRAFANA_PASSWORD=admin123

# Alerting Configuration
SLACK_WEBHOOK_URL=your_slack_webhook_url_here
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=your_email@gmail.com
TO_EMAILS=admin@yourcompany.com,ops@yourcompany.com

# Vaani Integration (Optional)
VAANI_USERNAME=admin
VAANI_PASSWORD=secret
VAANI_ENDPOINT=https://vaani-sentinel-gs6x.onrender.com

# External RAG API (Optional)
RAG_API_URL=https://your-rag-api-endpoint.com/rag
RAG_DEFAULT_TOP_K=5
RAG_TIMEOUT=30
```

## 🐳 Option 1: Docker Compose Deployment (Recommended for Development/Staging)

### Step 1: Clone and Setup
```bash
git clone <your-repo-url>
cd v2_Core

# Copy environment template
cp .env.example .env
# Edit .env with your actual values
```

### Step 2: Build and Deploy
```bash
# Build all images
docker-compose build

# Start all services
docker-compose up -d

# Check service status
docker-compose ps
```

### Step 3: Verify Deployment
```bash
# Wait for services to be ready (may take 2-3 minutes)
sleep 180

# Check API Gateway health
curl http://localhost:8000/health

# Check individual services
curl http://localhost:8001/health  # Logistics
curl http://localhost:8002/health  # CRM
curl http://localhost:8003/health  # Agent Orchestration
curl http://localhost:8004/health  # LLM Query
curl http://localhost:8005/health  # Integrations
```

### Step 4: Access Services
- **API Gateway**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Grafana Dashboard**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090

## ☸️ Option 2: Kubernetes Deployment (Recommended for Production)

### Step 1: Prerequisites
```bash
# Ensure kubectl is configured
kubectl cluster-info

# Create namespace
kubectl apply -f k8s/namespace.yaml
```

### Step 2: Configure Secrets
```bash
# Update secrets with your actual values
# Edit k8s/secrets.yaml with base64 encoded values

# Example: echo -n "your_password" | base64
echo -n "SecurePassword123!" | base64

# Apply secrets
kubectl apply -f k8s/secrets.yaml
```

### Step 3: Deploy Infrastructure
```bash
# Deploy in order
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml

# Wait for database to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n bhiv-core --timeout=300s
```

### Step 4: Deploy Services
```bash
# Deploy microservices
kubectl apply -f k8s/logistics-service.yaml
kubectl apply -f k8s/crm-service.yaml
kubectl apply -f k8s/agent-orchestration-service.yaml
kubectl apply -f k8s/llm-query-service.yaml
kubectl apply -f k8s/integrations-service.yaml

# Deploy API Gateway last
kubectl apply -f k8s/api-gateway.yaml

# Wait for all deployments
kubectl rollout status deployment --all -n bhiv-core --timeout=600s
```

### Step 5: Verify Kubernetes Deployment
```bash
# Check all pods
kubectl get pods -n bhiv-core

# Check services
kubectl get services -n bhiv-core

# Check ingress (if configured)
kubectl get ingress -n bhiv-core

# Port forward for testing
kubectl port-forward service/api-gateway-service 8000:80 -n bhiv-core
```

## 🔧 Option 3: Automated Deployment Script

### Use the Production Deployment Script
```bash
# For Docker Compose
python deploy/production_deploy.py docker-compose

# For Kubernetes
python deploy/production_deploy.py kubernetes
```

This script will:
1. Run pre-deployment checks
2. Deploy infrastructure components
3. Deploy microservices in correct order
4. Initialize the system
5. Run post-deployment verification
6. Generate deployment report

## 🧪 Post-Deployment Testing

### Step 1: Run System Integration Test
```bash
python integration/system_integration.py
```

### Step 2: Run Agent Integration Test
```bash
python integration/agent_integration.py
```

### Step 3: Run Production Demo
```bash
python demo/production_demo.py
```

### Step 4: Manual API Testing
```bash
# Get authentication token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Test agent query (replace <token> with actual JWT)
curl -X POST http://localhost:8000/api/agents/vedas/query \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query":"What is dharma?","language":"en"}'
```

## 📊 Monitoring Setup

### Grafana Dashboard Setup
1. Access Grafana: http://localhost:3000
2. Login: admin/admin123
3. Import dashboards from `monitoring/grafana/dashboards/`
4. Configure data sources:
   - Prometheus: http://prometheus:9090
   - Jaeger: http://jaeger:16686

### Prometheus Configuration
1. Access Prometheus: http://localhost:9090
2. Verify targets are up: Status > Targets
3. Test queries:
   - `up` - Service availability
   - `http_requests_total` - Request metrics
   - `bhiv_agents_total` - Agent metrics

## 🚨 Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check logs
docker-compose logs <service-name>
# or for Kubernetes
kubectl logs -l app=<service-name> -n bhiv-core

# Common fixes:
# 1. Check environment variables
# 2. Ensure database is ready
# 3. Check port conflicts
```

#### Database Connection Issues
```bash
# Test database connectivity
docker-compose exec postgres psql -U bhiv_user -d bhiv_core -c "SELECT 1;"

# Reset database
docker-compose down -v
docker-compose up -d postgres
```

#### Memory Issues
```bash
# Check resource usage
docker stats

# Increase Docker memory limit
# Docker Desktop: Settings > Resources > Memory
```

#### Port Conflicts
```bash
# Check port usage (Windows)
netstat -ano | findstr :8000

# Kill process using port
taskkill /PID <PID> /F

# Or change ports in docker-compose.yml
```

### Health Check Commands
```bash
# System health
curl http://localhost:8000/health

# Service-specific health
curl http://localhost:8001/health  # Logistics
curl http://localhost:8002/health  # CRM
curl http://localhost:8003/health  # Agent Orchestration

# Database health
docker-compose exec postgres pg_isready -U bhiv_user

# Redis health
docker-compose exec redis redis-cli ping
```

## 🔄 Maintenance Operations

### Backup Procedures
```bash
# Database backup
docker-compose exec postgres pg_dump -U bhiv_user bhiv_core > backup.sql

# Restore database
docker-compose exec -T postgres psql -U bhiv_user bhiv_core < backup.sql
```

### Update Procedures
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart services
docker-compose build
docker-compose up -d

# For Kubernetes
kubectl set image deployment/api-gateway api-gateway=bhiv/api-gateway:latest -n bhiv-core
kubectl rollout status deployment/api-gateway -n bhiv-core
```

### Scaling Operations
```bash
# Docker Compose scaling
docker-compose up -d --scale logistics=3 --scale crm=2

# Kubernetes scaling
kubectl scale deployment logistics-service --replicas=5 -n bhiv-core
```

## 📈 Performance Optimization

### Resource Allocation
```yaml
# In docker-compose.yml, add resource limits:
services:
  api-gateway:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Database Optimization
```sql
-- Connect to database and run:
-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
```

## 🔐 Security Hardening

### Production Security Checklist
- [ ] Change all default passwords
- [ ] Use strong JWT secrets
- [ ] Enable HTTPS/TLS
- [ ] Configure firewall rules
- [ ] Set up log monitoring
- [ ] Enable audit logging
- [ ] Configure backup encryption

### SSL/TLS Setup
```bash
# Generate SSL certificates (for production)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/private.key -out ssl/certificate.crt

# Update docker-compose.yml to use SSL
```

## 📞 Support and Next Steps

### Getting Help
1. Check logs: `docker-compose logs` or `kubectl logs`
2. Review health endpoints: `/health` on each service
3. Check monitoring dashboards in Grafana
4. Review documentation in `/docs/` directory

### Production Readiness
After successful deployment:
1. Run load tests
2. Configure monitoring alerts
3. Set up backup procedures
4. Document operational procedures
5. Train operations team

## 🎉 Deployment Complete!

Your BHIV Core production system is now deployed and ready for use. The system includes:

- ✅ 6 Microservices with auto-scaling
- ✅ 12 Enhanced AI Agents
- ✅ Enterprise Security (JWT, RBAC, Audit)
- ✅ Threat Detection & Response
- ✅ Comprehensive Observability
- ✅ Production Monitoring & Alerting

**Access Points:**
- API Gateway: http://localhost:8000
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- API Docs: http://localhost:8000/docs

**Next Steps:**
1. Configure your specific AI API keys
2. Set up production monitoring alerts
3. Run the demo: `python demo/production_demo.py`
4. Begin using the enhanced agent system!

🚀 **BHIV Core is now production-ready and enterprise-grade!**
