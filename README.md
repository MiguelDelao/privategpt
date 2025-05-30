# PrivateGPT Legal AI - Professional Document Analysis System

**Version:** 1.4  
**Target:** Legal professionals and law firms  
**Focus:** Data sovereignty, compliance, and comprehensive audit trails

## 📋 Overview

PrivateGPT Legal AI is a self-hosted AI assistant specifically designed for legal professionals. It provides secure document analysis, RAG-powered Q&A, and comprehensive compliance monitoring without any third-party data egress.

### 🎯 Key Features

- **🔒 Data Sovereignty:** Fully self-hosted with zero third-party LLM API calls
- **⚖️ Legal Compliance:** 7-year audit trails, attorney-client privilege protection
- **🧠 Advanced RAG:** Automatic document chunking with Weaviate and BGE embeddings
- **🚀 Simple Deployment:** Single-command Docker Compose setup
- **📊 Comprehensive Monitoring:** Grafana dashboards with legal-specific metrics
- **🔐 Security:** JWT authentication with role-based access control

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Legal AI System                          │
├─────────────────────────────────────────────────────────────┤
│  Traefik Gateway (Port 80)                                │
│  ├── /           → Streamlit UI                           │
│  ├── /grafana    → Monitoring Dashboards                 │
│  ├── /n8n        → Document Processing                   │
│  └── /prometheus → System Metrics                        │
├─────────────────────────────────────────────────────────────┤
│  Core Services                                             │
│  ├── 🧠 Ollama (LLaMA-3 8B/70B)                          │
│  ├── 🗃️ Weaviate (Auto-chunking Vector DB)                │
│  ├── 🔐 JWT Auth Service                                   │
│  ├── 📄 n8n Document Processing                           │
│  └── 📊 Monitoring Stack (Grafana + Prometheus + Loki)    │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Hardware:** GPU-enabled cloud instance (RTX 4090 or A100)
- **Software:** Docker & Docker Compose with NVIDIA Container Toolkit
- **Storage:** Minimum 200GB for development, 500GB for production

### 1. Clone and Setup

```bash
git clone <repository-url>
cd privategpt

# Copy environment template
cp env.example .env

# Edit environment variables
nano .env
```

### 2. Configure Environment

Update `.env` with your specific settings:

```bash
# Security (REQUIRED - Change these!)
JWT_SECRET_KEY=your-super-secret-jwt-key-here
WEAVIATE_API_KEY=your-weaviate-api-key-here
GRAFANA_ADMIN_PASSWORD=your-secure-grafana-password
N8N_PASSWORD=your-secure-n8n-password

# Models
OLLAMA_MODEL_DEV=llama3:8b      # Development
OLLAMA_MODEL_PROD=llama3:70b    # Production
```

### 3. Deploy System

```bash
# Single command deployment
docker-compose up -d

# Monitor startup
docker-compose logs -f
```

### 4. Initial Setup

```bash
# Download LLM model (first time only)
docker exec -it ollama-service ollama pull llama3:8b

# Create admin user
curl -X POST http://localhost/api/auth/create-user \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourfirm.com",
    "password": "SecurePassword123!",
    "role": "admin",
    "client_matters": ["General", "ClientA_Matter1"]
  }'
```

### 5. Access the System

- **Main Application:** http://localhost/
- **Monitoring Dashboard:** http://localhost/grafana
- **Document Workflows:** http://localhost/n8n
- **System Metrics:** http://localhost/prometheus

**Default Login:** `admin@legal-ai.local` / `admin123`

## 📊 Monitoring & Compliance

### Legal Compliance Features

✅ **7-year audit log retention**  
✅ **Attorney-client privilege protection**  
✅ **Client matter data segregation**  
✅ **Comprehensive activity tracking**  
✅ **Security incident monitoring**  
✅ **Billable time integration**

### Key Metrics Monitored

- Authentication events and security alerts
- Document access with user/matter tracking
- AI query logging with source attribution
- System performance and availability
- Compliance violations and investigations

### Grafana Dashboards

1. **Executive Dashboard:** Usage, ROI, compliance scores
2. **Compliance Dashboard:** Audit trails, security events
3. **Operations Dashboard:** System health, performance

## 🔧 Configuration

### User Management

```bash
# Create new user (admin only)
curl -X POST http://localhost/api/auth/create-user \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "attorney@firm.com",
    "password": "SecurePass123!",
    "role": "partner",
    "client_matters": ["ClientX_Contract2024"]
  }'
```

### Document Processing

The system automatically:
1. Extracts text from PDF/DOCX/TXT files
2. Sends full documents to Weaviate for auto-chunking
3. Generates embeddings using BGE model
4. Makes documents searchable within minutes

### RAG Configuration

- **Model:** LLaMA-3 8B (dev) / 70B (prod)
- **Embeddings:** BGE (CPU-based for cost efficiency)
- **Chunking:** Automatic via Weaviate
- **Context:** Top 3 relevant document chunks per query

## 🛡️ Security

### Multi-Layer Security

- **Authentication:** JWT with 8-hour expiration
- **Authorization:** Role-based access control
- **Data Protection:** LUKS disk encryption
- **Network:** Docker network isolation
- **Monitoring:** Failed login detection and alerting

### Compliance Controls

- **Data Retention:** 7-year policy for legal compliance
- **Access Control:** Client matter segregation
- **Audit Trails:** Immutable logging with PII redaction
- **Privacy:** No third-party data egress

## 💰 Cost Analysis

### Development Environment
- **Hardware:** RTX 4090 (~$0.50/hour)
- **Monthly Cost:** $300-600
- **Use Case:** Testing, training, proof-of-concept

### Production Environment
- **Hardware:** A100 80GB (~$1.89/hour)
- **Monthly Cost:** $600-1200
- **Use Case:** Live legal research, client work

### Cloud Provider Recommendations

| Provider | Cost (A100) | Pros | Best For |
|----------|-------------|------|----------|
| **RunPod** | $1.89/hr | ML-focused, reliable | Production |
| **Vast.ai** | $1.20/hr | Cheapest option | Development |
| **Lambda Labs** | $1.10/hr | ML-optimized | Production |

## 🔍 Troubleshooting

### Common Issues

**🚨 Service Won't Start**
```bash
# Check logs
docker-compose logs service-name

# Restart specific service
docker-compose restart service-name
```

**🚨 GPU Not Detected**
```bash
# Verify NVIDIA runtime
docker run --gpus all nvidia/cuda:11.0-base nvidia-smi

# Check Docker daemon.json
cat /etc/docker/daemon.json
```

**🚨 Authentication Failing**
```bash
# Reset admin password
docker exec -it auth-service python -c "
from auth_service import hash_password
print(hash_password('newpassword123'))
"
```

### Health Checks

```bash
# System health
curl http://localhost/health

# Service status
docker-compose ps

# Resource usage
docker stats
```

## 📈 Scaling & Production

### Performance Optimization

1. **GPU Model Selection**
   - Development: LLaMA-3 8B (4GB VRAM)
   - Production: LLaMA-3 70B (40GB VRAM)

2. **Storage Optimization**
   - Use NVMe SSDs for database storage
   - Implement log rotation policies
   - Regular backup verification

3. **Network Optimization**
   - Use CDN for static assets
   - Implement caching strategies
   - Monitor bandwidth usage

### Production Checklist

- [ ] Change all default passwords
- [ ] Configure backup procedures
- [ ] Set up monitoring alerts
- [ ] Implement log rotation
- [ ] Configure firewall rules
- [ ] Set up SSL certificates
- [ ] Document emergency procedures

## 🛣️ Roadmap

### Phase 1 (Months 1-3)
- [ ] LLaMA-3 70B production deployment
- [ ] Enhanced Grafana dashboards
- [ ] Advanced user management UI
- [ ] Document upload via web interface

### Phase 2 (Months 3-6)
- [ ] Fine-tuning on legal corpus
- [ ] Multi-tenant architecture
- [ ] Advanced security features (MFA)
- [ ] API endpoints for integrations

### Phase 3 (Months 6-12)
- [ ] SaaS offering capabilities
- [ ] E-discovery workflow integration
- [ ] Professional liability insurance integration
- [ ] Advanced compliance automation

## 📞 Support

### Documentation
- [Design Documents](./mind/privategpt_mind/)
- [API Documentation](./docs/api/)
- [Compliance Guide](./docs/compliance/)

### Community
- **Issues:** Create GitHub issues for bugs
- **Discussions:** Join community discussions
- **Security:** Report security issues privately

---

**⚖️ Legal Notice:** This system is designed for legal professionals. All AI-generated content should be reviewed by qualified attorneys. The system does not constitute legal advice and should not be relied upon as such.

**🔒 Privacy:** This system operates with complete data sovereignty - no data leaves your infrastructure. 