# 🚀 AI Video Translation Service - Deployment Guide

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Docker Testing](#local-docker-testing)
3. [AWS Production Deployment](#aws-production-deployment)
4. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
5. [Cost Optimization](#cost-optimization)

---

## 🔧 Prerequisites

### Local Development
```bash
# Required software
- Docker Desktop 4.0+
- Docker Compose 2.0+
- Git
- Text editor (VS Code recommended)

# Optional but recommended
- AWS CLI 2.0+
- curl or Postman for API testing
```

### AWS Deployment
```bash
# Required AWS services access
- ECR (Elastic Container Registry)
- ECS (Elastic Container Service) 
- EC2 (for ALB and NAT Gateways)
- VPC (Virtual Private Cloud)
- IAM (Identity and Access Management)
- Secrets Manager
- CloudWatch Logs
- S3 (Simple Storage Service)

# Required credentials
- AWS Account with Administrator access
- Hugging Face API Token
- Domain name (optional, for HTTPS)
```

---

## 🐳 Local Docker Testing

### Step 1: Clone and Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd ai-video-translation

# Copy environment template
cp env.example .env

# Edit .env file with your settings
vim .env  # or nano .env
```

### Step 2: Configure Environment
Edit `.env` file with your credentials:
```bash
# Required: Get from https://huggingface.co/settings/tokens
HUGGING_FACE_TOKEN=hf_your_token_here

# Application settings (defaults usually work)
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Storage directories (will be created automatically)
OUTPUT_DIRECTORY=output/
UPLOAD_DIRECTORY=uploads/
```

### Step 3: Build and Run with Docker Compose
```bash
# Build and start the service
docker-compose up --build

# Or run in background
docker-compose up -d --build

# Check logs
docker-compose logs -f

# Stop the service
docker-compose down
```

### Step 4: Test the Application
```bash
# Test the web interface
open http://localhost:8000/

# Test the health endpoint
curl http://localhost:8000/health

# Test API documentation
open http://localhost:8000/docs
```

### Step 5: Upload Test Video
1. **Via Web Interface:**
   - Navigate to `http://localhost:8000/`
   - Drag & drop an MP4 file (max 200MB)
   - Select source and target languages
   - Click "Start Translation"
   - Monitor real-time progress

2. **Via API:**
   ```bash
   # Upload a video file
   curl -X POST "http://localhost:8000/api/v1/upload" \
     -F "file=@test_video.mp4" \
     -F "target_language=spa" \
     -F "source_language=eng"
   
   # Check status (replace JOB_ID with actual ID)
   curl "http://localhost:8000/api/v1/jobs/JOB_ID/status"
   
   # Download result when complete
   curl "http://localhost:8000/api/v1/jobs/JOB_ID/download" -o translated.mp4
   ```

### Step 6: Development Workflow
```bash
# View running containers
docker-compose ps

# Access container shell for debugging
docker-compose exec ai-video-translation bash

# View container logs
docker-compose logs ai-video-translation

# Restart specific service
docker-compose restart ai-video-translation

# Clean up everything
docker-compose down -v --rmi all
```

---

## ☁️ AWS Production Deployment

### Phase 1: AWS Prerequisites Setup

#### 1.1 Install AWS CLI
```bash
# macOS
brew install awscli

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Windows
# Download from: https://awscli.amazonaws.com/AWSCLIV2.msi
```

#### 1.2 Configure AWS CLI
```bash
# Configure AWS credentials
aws configure

# You'll need:
# - AWS Access Key ID
# - AWS Secret Access Key  
# - Default region (e.g., us-east-1)
# - Default output format (json)

# Verify configuration
aws sts get-caller-identity
```

#### 1.3 Set Required Environment Variables
```bash
# Set your AWS account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Set your preferred region
export AWS_REGION=us-east-1

# Set your Hugging Face token
export HUGGING_FACE_TOKEN=hf_your_token_here
```

### Phase 2: Infrastructure Deployment

#### 2.1 Deploy Infrastructure with CloudFormation
```bash
# Create the CloudFormation stack
aws cloudformation create-stack \
  --stack-name ai-video-translation-infra \
  --template-body file://aws/cloudformation-infrastructure.yml \
  --parameters ParameterKey=HuggingFaceToken,ParameterValue=$HUGGING_FACE_TOKEN \
  --capabilities CAPABILITY_IAM \
  --region $AWS_REGION

# Monitor stack creation
aws cloudformation describe-stacks \
  --stack-name ai-video-translation-infra \
  --region $AWS_REGION \
  --query 'Stacks[0].StackStatus'

# Wait for completion (takes 10-15 minutes)
aws cloudformation wait stack-create-complete \
  --stack-name ai-video-translation-infra \
  --region $AWS_REGION

# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name ai-video-translation-infra \
  --region $AWS_REGION \
  --query 'Stacks[0].Outputs'
```

#### 2.2 Verify Infrastructure
```bash
# Check if ECS cluster is created
aws ecs describe-clusters \
  --clusters ai-video-translation-production-cluster \
  --region $AWS_REGION

# Check if ECR repository is created
aws ecr describe-repositories \
  --repository-names ai-video-translation \
  --region $AWS_REGION

# Check if S3 bucket is created
aws s3 ls | grep ai-video-translation
```

### Phase 3: Application Deployment

#### 3.1 Deploy Using Automated Script
```bash
# Make deployment script executable
chmod +x aws/deploy.sh

# Run deployment with default settings
./aws/deploy.sh

# Or with custom parameters
./aws/deploy.sh -r us-west-2 -c my-cluster -s my-service
```

#### 3.2 Manual Deployment (Alternative)

**Build and Push Docker Image:**
```bash
# Get ECR repository URI
ECR_URI=$(aws cloudformation describe-stacks \
  --stack-name ai-video-translation-infra \
  --region $AWS_REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`ECRRepository`].OutputValue' \
  --output text)

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_URI

# Build and tag image
docker build -t ai-video-translation:latest .
docker tag ai-video-translation:latest $ECR_URI:latest

# Push to ECR
docker push $ECR_URI:latest
```

**Update ECS Service:**
```bash
# Update task definition with new image
sed "s|YOUR_ACCOUNT_ID|$AWS_ACCOUNT_ID|g" aws/task-definition.json > task-def-updated.json

# Register new task definition
aws ecs register-task-definition \
  --cli-input-json file://task-def-updated.json \
  --region $AWS_REGION

# Update ECS service
aws ecs update-service \
  --cluster ai-video-translation-production-cluster \
  --service ai-video-translation-production-service \
  --task-definition ai-video-translation-task \
  --region $AWS_REGION

# Wait for deployment to complete
aws ecs wait services-stable \
  --cluster ai-video-translation-production-cluster \
  --services ai-video-translation-production-service \
  --region $AWS_REGION
```

### Phase 4: DNS and SSL Setup (Optional)

#### 4.1 Get Load Balancer DNS
```bash
# Get ALB endpoint
ALB_DNS=$(aws cloudformation describe-stacks \
  --stack-name ai-video-translation-infra \
  --region $AWS_REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`ALBEndpoint`].OutputValue' \
  --output text)

echo "Your application will be available at: http://$ALB_DNS"
```

#### 4.2 Configure Custom Domain (Optional)
```bash
# If you have a domain, create a Route 53 hosted zone
aws route53 create-hosted-zone \
  --name yourdomain.com \
  --caller-reference $(date +%s)

# Create an A record pointing to the ALB
# (Use AWS Console or CLI to create the record)
```

#### 4.3 Add HTTPS/SSL (Optional)
```bash
# Request SSL certificate via ACM
aws acm request-certificate \
  --domain-name yourdomain.com \
  --validation-method DNS \
  --region $AWS_REGION

# Add HTTPS listener to ALB (requires certificate ARN)
# This is typically done through AWS Console or additional CloudFormation
```

---

## 📊 Monitoring & Troubleshooting

### Application Health Monitoring
```bash
# Check ECS service status
aws ecs describe-services \
  --cluster ai-video-translation-production-cluster \
  --services ai-video-translation-production-service \
  --region $AWS_REGION

# Check task health
aws ecs list-tasks \
  --cluster ai-video-translation-production-cluster \
  --service-name ai-video-translation-production-service \
  --region $AWS_REGION

# View application logs
aws logs tail /ecs/ai-video-translation-production --follow
```

### Load Balancer Health
```bash
# Check target group health
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --names ai-video-translation-production-tg \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text) \
  --region $AWS_REGION
```

### Container Resource Usage
```bash
# Check container insights (if enabled)
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=ai-video-translation-production-service \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region $AWS_REGION
```

### Common Issues and Solutions

#### Issue 1: Service Not Starting
```bash
# Check ECS service events
aws ecs describe-services \
  --cluster ai-video-translation-production-cluster \
  --services ai-video-translation-production-service \
  --region $AWS_REGION \
  --query 'services[0].events'

# Common solutions:
# - Check Hugging Face token in Secrets Manager
# - Verify ECR image URI in task definition
# - Check security group rules
# - Verify IAM roles and permissions
```

#### Issue 2: Health Check Failing
```bash
# Check container logs
aws logs get-log-events \
  --log-group-name /ecs/ai-video-translation-production \
  --log-stream-name ecs/ai-video-translation/TASK_ID

# Common solutions:
# - Verify health check endpoint (/health)
# - Check application startup time
# - Review container resource limits
```

#### Issue 3: High Memory Usage
```bash
# Scale up task resources
# Update task definition with higher memory allocation
# Example: Change from 8192 to 16384 MB

# Or scale out (add more tasks)
aws ecs update-service \
  --cluster ai-video-translation-production-cluster \
  --service ai-video-translation-production-service \
  --desired-count 4 \
  --region $AWS_REGION
```

---

## 💰 Cost Optimization

### Understanding AWS Costs

**Estimated Monthly Costs (us-east-1, 24/7 operation):**
- **ECS Fargate (2 tasks, 2vCPU, 8GB):** ~$70-100/month
- **Application Load Balancer:** ~$25/month  
- **NAT Gateways (2):** ~$90/month
- **Data Transfer:** Variable (~$0.09/GB)
- **S3 Storage:** ~$0.023/GB/month
- **CloudWatch Logs:** ~$0.50/GB/month

**Total:** ~$185-215/month (excluding data transfer and storage)

### Cost Optimization Strategies

#### 1. Use Fargate Spot
```bash
# Update task definition to use FARGATE_SPOT
# Potential savings: 50-70% on compute costs
# Trade-off: Tasks may be interrupted
```

#### 2. Auto Scaling
```bash
# Implement ECS auto scaling based on CPU/memory
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/ai-video-translation-production-cluster/ai-video-translation-production-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 1 \
  --max-capacity 10 \
  --region $AWS_REGION
```

#### 3. Scheduled Scaling
```bash
# Scale down during low usage hours
# Scale up during peak hours
# Can save 40-60% on compute costs
```

#### 4. Single NAT Gateway
```bash
# Use single NAT Gateway instead of two
# Savings: ~$45/month
# Trade-off: Reduced high availability
```

#### 5. Reserved Capacity (for predictable workloads)
```bash
# Consider EC2 Reserved Instances for steady-state workloads
# Potential savings: 30-50% on compute costs
```

---

## 🔄 Maintenance & Updates

### Regular Maintenance Tasks

#### Weekly
```bash
# Check application health
curl http://YOUR_ALB_DNS/health

# Review CloudWatch logs for errors
aws logs filter-log-events \
  --log-group-name /ecs/ai-video-translation-production \
  --start-time $(date -d '7 days ago' +%s)000 \
  --filter-pattern "ERROR"
```

#### Monthly
```bash
# Update dependencies and rebuild image
# Review AWS costs and optimize
# Check for AWS service updates
# Update SSL certificates (if using custom domain)
```

### Deployment Updates
```bash
# For application updates, run:
./aws/deploy.sh

# For infrastructure updates:
aws cloudformation update-stack \
  --stack-name ai-video-translation-infra \
  --template-body file://aws/cloudformation-infrastructure.yml \
  --capabilities CAPABILITY_IAM \
  --region $AWS_REGION
```

### Backup and Recovery
```bash
# S3 bucket has versioning enabled by default
# Task definitions are version-controlled automatically
# For full recovery, redeploy infrastructure + latest application
```

---

## 🚨 Emergency Procedures

### Scale Down (Cost Control)
```bash
# Immediately scale to 0 tasks
aws ecs update-service \
  --cluster ai-video-translation-production-cluster \
  --service ai-video-translation-production-service \
  --desired-count 0 \
  --region $AWS_REGION
```

### Complete Shutdown
```bash
# Delete CloudFormation stack (saves all costs)
aws cloudformation delete-stack \
  --stack-name ai-video-translation-infra \
  --region $AWS_REGION

# Warning: This deletes ALL resources including data!
```

### Quick Recovery
```bash
# Redeploy infrastructure
aws cloudformation create-stack \
  --stack-name ai-video-translation-infra \
  --template-body file://aws/cloudformation-infrastructure.yml \
  --parameters ParameterKey=HuggingFaceToken,ParameterValue=$HUGGING_FACE_TOKEN \
  --capabilities CAPABILITY_IAM \
  --region $AWS_REGION

# Redeploy application
./aws/deploy.sh
```

---

## ✅ Deployment Checklist

### Pre-Deployment
- [ ] AWS CLI configured and tested
- [ ] Hugging Face token obtained and tested
- [ ] Docker installed and working
- [ ] Local testing completed successfully
- [ ] Domain name ready (if using custom domain)

### Infrastructure Deployment
- [ ] CloudFormation stack deployed successfully
- [ ] ECS cluster created and running
- [ ] ECR repository created
- [ ] S3 bucket created with proper permissions
- [ ] Secrets Manager contains Hugging Face token
- [ ] Load balancer and target groups healthy

### Application Deployment  
- [ ] Docker image built and pushed to ECR
- [ ] ECS task definition registered
- [ ] ECS service updated and stable
- [ ] Health checks passing
- [ ] Application accessible via load balancer

### Post-Deployment Verification
- [ ] Web interface loads correctly
- [ ] API endpoints respond properly
- [ ] File upload and translation working
- [ ] WebSocket connections functioning
- [ ] Logs are being written to CloudWatch
- [ ] Monitoring and alerting configured

### Production Readiness
- [ ] SSL certificate configured (if using HTTPS)
- [ ] Domain name configured (if applicable)
- [ ] Auto-scaling policies configured
- [ ] Backup and recovery procedures tested
- [ ] Cost monitoring and alerts set up
- [ ] Security review completed

---

**🎉 Congratulations! Your AI Video Translation Service is now running in production!**

**Access your service at:** `http://YOUR_ALB_DNS/`

**For support and updates, refer to the main README.md and project documentation.** 