# 🏗️ AI Video Translation Service - Docker & AWS Architecture

## 📋 Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Local Docker Architecture](#local-docker-architecture)
3. [AWS Production Architecture](#aws-production-architecture)
4. [Security Architecture](#security-architecture)
5. [Scaling Architecture](#scaling-architecture)
6. [Cost Architecture](#cost-architecture)

---

## 🔄 Architecture Overview

The AI Video Translation Service is designed with a modern, cloud-native architecture that supports both local development and production deployment on AWS.

### Key Design Principles
- **Containerized**: Everything runs in Docker containers for consistency
- **Scalable**: Horizontal and vertical scaling capabilities
- **Secure**: Defense in depth security model
- **Observable**: Comprehensive logging and monitoring
- **Cost-Optimized**: Efficient resource utilization

---

## 🐳 Local Docker Architecture

### Container Structure
```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Host                              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │           AI Video Translation Container            │    │
│  │  ┌───────────────┐  ┌───────────────┐             │    │
│  │  │   Frontend    │  │   Backend     │             │    │
│  │  │   (Static)    │  │  (FastAPI)    │             │    │
│  │  │               │  │               │             │    │
│  │  │ • HTML/CSS/JS │  │ • REST API    │             │    │
│  │  │ • Templates   │  │ • WebSocket   │             │    │
│  │  │ • Assets      │  │ • Job Queue   │             │    │
│  │  └───────────────┘  └───────────────┘             │    │
│  │                                                    │    │
│  │  ┌───────────────┐  ┌───────────────┐             │    │
│  │  │   AI Models   │  │   Storage     │             │    │
│  │  │               │  │               │             │    │
│  │  │ • Whisper     │  │ • SQLite DB   │             │    │
│  │  │ • NLLB        │  │ • File System │             │    │
│  │  │ • Cache       │  │ • Volumes     │             │    │
│  │  └───────────────┘  └───────────────┘             │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Optional Services                      │    │
│  │  ┌─────────────┐  ┌─────────────┐                  │    │
│  │  │    Redis    │  │    Nginx    │                  │    │
│  │  │  (Queue)    │  │   (Proxy)   │                  │    │
│  │  └─────────────┘  └─────────────┘                  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Volume Mounting Strategy
```yaml
volumes:
  # Application data (persistent)
  - ./uploads:/app/uploads          # Input videos
  - ./output:/app/output           # Translated videos
  - ./logs:/app/logs               # Application logs
  
  # Model cache (persistent for performance)
  - model_cache:/home/app/.cache   # AI model cache
  
  # Configuration (development)
  - ./.env:/app/.env               # Environment variables
```

### Network Architecture
```
┌─────────────────────────────────────────────────┐
│             Docker Network                      │
│         (ai-video-translation-network)          │
│                                                 │
│  ┌─────────────┐    ┌─────────────┐            │
│  │     App     │◄──►│    Redis    │            │
│  │   :8000     │    │   :6379     │            │
│  └─────────────┘    └─────────────┘            │
│         ▲                                      │
│         │                                      │
│  ┌─────────────┐                               │
│  │    Nginx    │                               │
│  │   :80/:443  │                               │
│  └─────────────┘                               │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│              Host Network                       │
│                                                 │
│  localhost:8000 → App                          │
│  localhost:6379 → Redis (dev only)             │
│  localhost:80   → Nginx (production profile)   │
└─────────────────────────────────────────────────┘
```

---

## ☁️ AWS Production Architecture

### High-Level AWS Architecture
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud (us-east-1)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Public Subnets                              │    │
│  │  ┌─────────────────┐                    ┌─────────────────┐        │    │
│  │  │      AZ-1a      │                    │      AZ-1b      │        │    │
│  │  │                 │                    │                 │        │    │
│  │  │ ┌─────────────┐ │                    │ ┌─────────────┐ │        │    │
│  │  │ │     ALB     │ │                    │ │     ALB     │ │        │    │
│  │  │ │   (Active)  │ │◄──────────────────►│ │  (Standby)  │ │        │    │
│  │  │ └─────────────┘ │                    │ └─────────────┘ │        │    │
│  │  │                 │                    │                 │        │    │
│  │  │ ┌─────────────┐ │                    │ ┌─────────────┐ │        │    │
│  │  │ │ NAT Gateway │ │                    │ │ NAT Gateway │ │        │    │
│  │  │ └─────────────┘ │                    │ └─────────────┘ │        │    │
│  │  └─────────────────┘                    └─────────────────┘        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                     │                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                       Private Subnets                              │    │
│  │  ┌─────────────────┐                    ┌─────────────────┐        │    │
│  │  │      AZ-1a      │                    │      AZ-1b      │        │    │
│  │  │                 │                    │                 │        │    │
│  │  │ ┌─────────────┐ │                    │ ┌─────────────┐ │        │    │
│  │  │ │ ECS Fargate │ │                    │ │ ECS Fargate │ │        │    │
│  │  │ │   Task 1    │ │                    │ │   Task 2    │ │        │    │
│  │  │ │             │ │                    │ │             │ │        │    │
│  │  │ │ App:8000    │ │                    │ │ App:8000    │ │        │    │
│  │  │ └─────────────┘ │                    │ └─────────────┘ │        │    │
│  │  └─────────────────┘                    └─────────────────┘        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        AWS Services                                │    │
│  │                                                                     │    │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐       │    │
│  │  │    ECR    │  │ Secrets   │  │    S3     │  │CloudWatch │       │    │
│  │  │  (Images) │  │ Manager   │  │ (Storage) │  │  (Logs)   │       │    │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Detailed Component Architecture

#### 1. Network Layer
```yaml
VPC Configuration:
  - CIDR: 10.0.0.0/16
  - Public Subnets: 10.0.101.0/24, 10.0.102.0/24
  - Private Subnets: 10.0.1.0/24, 10.0.2.0/24
  - Availability Zones: us-east-1a, us-east-1b

Security Groups:
  ALB Security Group:
    - Inbound: 80/443 from 0.0.0.0/0
    - Outbound: 8000 to ECS Security Group
  
  ECS Security Group:
    - Inbound: 8000 from ALB Security Group
    - Outbound: All traffic (for model downloads)
```

#### 2. Compute Layer
```yaml
ECS Fargate Configuration:
  CPU: 2048 (2 vCPU)
  Memory: 8192 MB (8 GB)
  Storage: 20 GB ephemeral
  
Task Definition:
  - Container: ai-video-translation
  - Port: 8000
  - Health Check: /health endpoint
  - Logging: CloudWatch Logs
  
Service Configuration:
  - Desired Count: 2
  - Launch Type: FARGATE
  - Load Balancer: Application Load Balancer
  - Auto Scaling: Target tracking (CPU/Memory)
```

#### 3. Storage Layer
```yaml
ECR (Container Registry):
  - Repository: ai-video-translation
  - Image Scanning: Enabled
  - Lifecycle Policy: 7 days for untagged images

S3 (Object Storage):
  - Bucket: ai-video-translation-production-storage-{account-id}
  - Versioning: Enabled
  - Encryption: AES-256
  - Lifecycle: 30 days for old versions

Secrets Manager:
  - Hugging Face Token: /ai-video-translation/huggingface-token
  - Encryption: AWS KMS
```

#### 4. Load Balancing
```yaml
Application Load Balancer:
  - Scheme: Internet-facing
  - Subnets: Public subnets (multi-AZ)
  - Security Group: ALB Security Group
  - Target Group: ECS tasks on port 8000
  
Health Checks:
  - Path: /health
  - Interval: 30 seconds
  - Timeout: 10 seconds
  - Healthy Threshold: 2
  - Unhealthy Threshold: 5
```

### Traffic Flow
```
Internet → Route 53 (optional) → CloudFront (optional) → ALB → ECS Tasks
                                                          ↓
                                            S3 ← File Storage → CloudWatch Logs
                                                          ↓
                                              Secrets Manager ← Environment Variables
```

---

## 🔐 Security Architecture

### Defense in Depth Model

#### 1. Network Security
```yaml
Network Isolation:
  - VPC with private subnets for compute
  - Public subnets only for load balancers
  - NAT Gateways for outbound internet access
  - Security Groups as stateful firewalls

Traffic Encryption:
  - TLS 1.2+ for all external communications
  - ALB handles SSL termination
  - Internal traffic over private networks
```

#### 2. Container Security
```yaml
Image Security:
  - Multi-stage Docker builds
  - Non-root user in container
  - Minimal base images (Python slim)
  - Regular vulnerability scanning

Runtime Security:
  - Read-only file systems where possible
  - Resource limits (CPU/Memory)
  - No privileged containers
  - Secrets via environment variables only
```

#### 3. Access Control
```yaml
IAM Roles:
  ECS Task Execution Role:
    - ECR image pulling
    - CloudWatch logging
    - Secrets Manager access
    
  ECS Task Role:
    - S3 bucket access (read/write)
    - Limited to specific resources

API Security:
  - Rate limiting (future enhancement)
  - Input validation and sanitization
  - File type and size restrictions
```

#### 4. Data Security
```yaml
Data at Rest:
  - S3 server-side encryption (AES-256)
  - Secrets Manager KMS encryption
  - EBS encryption for temporary storage

Data in Transit:
  - HTTPS/TLS for all API communications
  - WebSocket Secure (WSS) for real-time updates
  - VPC internal traffic isolation
```

---

## 📈 Scaling Architecture

### Horizontal Scaling
```yaml
Auto Scaling Configuration:
  Service Auto Scaling:
    - Min Capacity: 1
    - Max Capacity: 10
    - Target CPU: 70%
    - Target Memory: 80%
    - Scale-out cooldown: 300s
    - Scale-in cooldown: 300s

Load Balancer Scaling:
  - Automatic scaling based on load
  - Multi-AZ distribution
  - Connection draining during scaling
```

### Vertical Scaling
```yaml
Task Definition Scaling:
  Development:
    - CPU: 1024 (1 vCPU)
    - Memory: 4096 MB (4 GB)
  
  Production:
    - CPU: 2048 (2 vCPU)
    - Memory: 8192 MB (8 GB)
  
  High-Load:
    - CPU: 4096 (4 vCPU)
    - Memory: 16384 MB (16 GB)
```

### Performance Optimization
```yaml
Model Caching Strategy:
  - EFS for shared model cache (future)
  - Container-level caching
  - Pre-loading of frequently used models
  - Smart eviction policies

Job Queue Management:
  - In-memory queue for simplicity
  - Redis for distributed queue (optional)
  - Priority-based job processing
  - Circuit breaker patterns
```

---

## 💰 Cost Architecture

### Cost Breakdown (Monthly Estimates)

#### Development Environment
```yaml
Single Task (1 vCPU, 4GB):
  - ECS Fargate: ~$35/month
  - ALB: ~$25/month
  - NAT Gateway: ~$45/month
  - Data Transfer: ~$5/month
  - Total: ~$110/month
```

#### Production Environment
```yaml
Two Tasks (2 vCPU, 8GB each):
  - ECS Fargate: ~$140/month
  - ALB: ~$25/month
  - NAT Gateways (2): ~$90/month
  - Data Transfer: Variable
  - S3 Storage: ~$2/month (100GB)
  - CloudWatch: ~$5/month
  - Secrets Manager: ~$1/month
  - Total: ~$263/month
```

#### High-Availability Production
```yaml
Four Tasks + Spot Instances:
  - ECS Fargate: ~$200/month
  - ECS Fargate Spot: ~$80/month (60% savings)
  - ALB: ~$25/month
  - NAT Gateways: ~$90/month
  - Other services: ~$8/month
  - Total: ~$403/month
```

### Cost Optimization Strategies

#### 1. Compute Optimization
```yaml
Fargate Spot:
  - 50-70% cost reduction
  - Suitable for batch processing
  - Automatic failover to on-demand

Reserved Capacity:
  - 1-year term: 20% savings
  - 3-year term: 50% savings
  - Suitable for predictable workloads
```

#### 2. Scheduling Optimization
```yaml
Auto Scaling Schedules:
  Business Hours (9 AM - 6 PM):
    - Min: 2 tasks
    - Max: 10 tasks
  
  Off Hours (6 PM - 9 AM):
    - Min: 1 task
    - Max: 3 tasks
  
  Weekends:
    - Min: 0 tasks (if acceptable)
    - Max: 2 tasks
```

#### 3. Storage Optimization
```yaml
S3 Lifecycle Policies:
  - Standard → Standard-IA: 30 days
  - Standard-IA → Glacier: 90 days
  - Glacier → Deep Archive: 365 days
  - Delete after: 2555 days (7 years)

Intelligent Tiering:
  - Automatic cost optimization
  - No retrieval fees
  - Monitor access patterns
```

---

## 🔧 Deployment Architecture

### CI/CD Pipeline (Future Enhancement)
```yaml
Development Workflow:
  1. Code Push → GitHub/GitLab
  2. Trigger → GitHub Actions/GitLab CI
  3. Build → Docker Image
  4. Test → Automated Tests
  5. Push → ECR Repository
  6. Deploy → ECS Service Update

Production Deployment:
  1. Tag Release → Version Control
  2. Build → Production Image
  3. Security Scan → Container Scanning
  4. Blue/Green Deploy → ECS Rolling Update
  5. Health Check → Automated Verification
  6. Rollback → Automatic on Failure
```

### Environment Strategy
```yaml
Development:
  - Single task
  - Shared resources
  - Debug logging enabled
  - Cost-optimized

Staging:
  - Production-like setup
  - Reduced capacity
  - Full monitoring
  - Performance testing

Production:
  - Multi-AZ deployment
  - Auto-scaling enabled
  - Full monitoring
  - High availability
```

---

## 📊 Monitoring Architecture

### CloudWatch Integration
```yaml
Metrics Collection:
  - ECS task metrics (CPU, memory, network)
  - ALB metrics (requests, latency, errors)
  - Custom application metrics
  - Cost and billing metrics

Log Aggregation:
  - Application logs → CloudWatch Logs
  - ALB access logs → S3
  - VPC Flow Logs → CloudWatch
  - Container insights enabled

Alerting:
  - High CPU/Memory usage
  - Application errors
  - Health check failures
  - Cost threshold breaches
```

### Health Monitoring
```yaml
Application Health:
  - Health endpoint: /health
  - Deep health checks
  - Database connectivity
  - External service dependencies

Infrastructure Health:
  - ECS service status
  - Task health checks
  - ALB target health
  - Network connectivity
```

---

This architecture provides a robust, scalable, and cost-effective foundation for the AI Video Translation Service, supporting both development workflows and production requirements while maintaining security and operational excellence. 