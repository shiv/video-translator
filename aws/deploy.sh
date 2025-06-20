#!/bin/bash
set -e

# AI Video Translation Service - AWS Deployment Script
# This script builds and deploys the application to AWS ECS Fargate

# Configuration
AWS_REGION="us-east-1"
ECR_REPOSITORY="ai-video-translation"
ECS_CLUSTER="ai-video-translation-cluster"
ECS_SERVICE="ai-video-translation-service"
TASK_DEFINITION_FAMILY="ai-video-translation-task"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if AWS CLI is configured
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI is not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    print_success "AWS CLI is configured"
}

# Function to get AWS account ID
get_account_id() {
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    print_status "Using AWS Account ID: $AWS_ACCOUNT_ID"
}

# Function to create ECR repository if it doesn't exist
create_ecr_repository() {
    print_status "Checking if ECR repository exists..."
    
    if ! aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION &> /dev/null; then
        print_status "Creating ECR repository: $ECR_REPOSITORY"
        aws ecr create-repository \
            --repository-name $ECR_REPOSITORY \
            --region $AWS_REGION \
            --image-scanning-configuration scanOnPush=true
        print_success "ECR repository created"
    else
        print_success "ECR repository already exists"
    fi
}

# Function to login to ECR
ecr_login() {
    print_status "Logging in to ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
    print_success "Logged in to ECR"
}

# Function to build and push Docker image
build_and_push() {
    print_status "Building Docker image..."
    
    # Build the image
    docker build -t $ECR_REPOSITORY:latest .
    
    # Tag for ECR
    ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest"
    docker tag $ECR_REPOSITORY:latest $ECR_URI
    
    print_status "Pushing image to ECR..."
    docker push $ECR_URI
    
    print_success "Image pushed to ECR: $ECR_URI"
}

# Function to update task definition
update_task_definition() {
    print_status "Updating task definition..."
    
    # Replace placeholders in task definition
    sed "s/YOUR_ACCOUNT_ID/$AWS_ACCOUNT_ID/g" aws/task-definition.json > aws/task-definition-updated.json
    
    # Register new task definition
    aws ecs register-task-definition \
        --cli-input-json file://aws/task-definition-updated.json \
        --region $AWS_REGION
    
    print_success "Task definition updated"
}

# Function to update ECS service
update_ecs_service() {
    print_status "Updating ECS service..."
    
    # Check if service exists
    if aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE --region $AWS_REGION &> /dev/null; then
        # Update existing service
        aws ecs update-service \
            --cluster $ECS_CLUSTER \
            --service $ECS_SERVICE \
            --task-definition $TASK_DEFINITION_FAMILY \
            --region $AWS_REGION
        print_success "ECS service updated"
    else
        print_warning "ECS service does not exist. Please create it manually or use the CloudFormation template."
    fi
}

# Function to wait for deployment
wait_for_deployment() {
    print_status "Waiting for deployment to complete..."
    
    aws ecs wait services-stable \
        --cluster $ECS_CLUSTER \
        --services $ECS_SERVICE \
        --region $AWS_REGION
    
    print_success "Deployment completed successfully!"
}

# Function to clean up
cleanup() {
    if [ -f "aws/task-definition-updated.json" ]; then
        rm aws/task-definition-updated.json
    fi
}

# Main deployment function
main() {
    print_status "Starting AI Video Translation Service deployment to AWS..."
    
    # Check prerequisites
    check_aws_cli
    get_account_id
    
    # ECR operations
    create_ecr_repository
    ecr_login
    build_and_push
    
    # ECS operations
    update_task_definition
    update_ecs_service
    wait_for_deployment
    
    # Cleanup
    cleanup
    
    print_success "Deployment completed! Your service should be available shortly."
    print_status "Check the ECS console for service status and load balancer endpoint."
}

# Help function
show_help() {
    echo "AI Video Translation Service - AWS Deployment Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -r, --region   AWS region (default: us-east-1)"
    echo "  -c, --cluster  ECS cluster name (default: ai-video-translation-cluster)"
    echo "  -s, --service  ECS service name (default: ai-video-translation-service)"
    echo ""
    echo "Examples:"
    echo "  $0                           # Deploy with default settings"
    echo "  $0 -r us-west-2             # Deploy to us-west-2 region"
    echo "  $0 -c my-cluster            # Deploy to custom cluster"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -r|--region)
            AWS_REGION="$2"
            shift 2
            ;;
        -c|--cluster)
            ECS_CLUSTER="$2"
            shift 2
            ;;
        -s|--service)
            ECS_SERVICE="$2"
            shift 2
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Run main function
main 