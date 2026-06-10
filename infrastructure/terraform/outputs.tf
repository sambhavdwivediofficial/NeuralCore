# infrastructure/terraform/outputs.tf

output "eks_cluster_id" {
  description = "EKS Cluster ID"
  value       = aws_eks_cluster.main.id
}

output "eks_cluster_endpoint" {
  description = "EKS Cluster endpoint"
  value       = aws_eks_cluster.main.endpoint
  sensitive   = false
}

output "eks_cluster_version" {
  description = "EKS Cluster Kubernetes version"
  value       = aws_eks_cluster.main.version
}

output "eks_cluster_security_group_id" {
  description = "EKS Cluster security group ID"
  value       = aws_security_group.eks_cluster.id
}

output "eks_node_group_id" {
  description = "EKS Node Group ID"
  value       = aws_eks_node_group.main.id
}

output "eks_node_group_arn" {
  description = "EKS Node Group ARN"
  value       = aws_eks_node_group.main.arn
}

output "rds_endpoint" {
  description = "RDS database endpoint"
  value       = aws_db_instance.postgres.endpoint
  sensitive   = false
}

output "rds_port" {
  description = "RDS database port"
  value       = aws_db_instance.postgres.port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_db_instance.postgres.db_name
}

output "rds_resource_id" {
  description = "RDS resource ID"
  value       = aws_db_instance.postgres.resource_id
  sensitive   = true
}

output "elasticache_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
  sensitive   = false
}

output "elasticache_port" {
  description = "ElastiCache Redis port"
  value       = aws_elasticache_cluster.redis.port
}

output "s3_bucket_name" {
  description = "S3 bucket name for uploads"
  value       = aws_s3_bucket.uploads.id
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.uploads.arn
}

output "s3_bucket_region" {
  description = "S3 bucket region"
  value       = aws_s3_bucket.uploads.region
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "VPC CIDR block"
  value       = aws_vpc.main.cidr_block
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "nat_gateway_ips" {
  description = "NAT Gateway Elastic IPs"
  value       = aws_eip.nat[*].public_ip
}

output "load_balancer_endpoint" {
  description = "Network Load Balancer endpoint"
  value       = aws_lb.main.dns_name
}

output "load_balancer_arn" {
  description = "Load Balancer ARN"
  value       = aws_lb.main.arn
}

output "load_balancer_security_group_id" {
  description = "Load Balancer security group ID"
  value       = aws_security_group.alb.id
}

output "iam_role_arn" {
  description = "IAM role ARN for EKS nodes"
  value       = aws_iam_role.eks_node_role.arn
}

output "kms_key_id" {
  description = "KMS key ID for encryption"
  value       = aws_kms_key.main.id
  sensitive   = false
}

output "kms_key_arn" {
  description = "KMS key ARN"
  value       = aws_kms_key.main.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.eks.name
}

output "aws_account_id" {
  description = "AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "AWS region"
  value       = data.aws_region.current.name
}

output "ecr_repository_urls" {
  description = "ECR repository URLs for Docker images"
  value = {
    api     = aws_ecr_repository.api.repository_url
    worker  = aws_ecr_repository.worker.repository_url
    frontend = aws_ecr_repository.frontend.repository_url
    engine  = aws_ecr_repository.engine.repository_url
  }
}

output "kubernetes_config" {
  description = "Kubernetes configuration command"
  value       = "aws eks update-kubeconfig --region ${data.aws_region.current.name} --name ${aws_eks_cluster.main.id}"
  sensitive   = false
}

output "environment" {
  description = "Deployment environment"
  value       = var.environment
}

output "project_name" {
  description = "Project name"
  value       = var.project_name
}

output "kubernetes_namespace" {
  description = "Kubernetes namespace for NeuralCore"
  value       = "neuralcore"
}

output "application_endpoints" {
  description = "Application endpoints"
  value = {
    api       = "https://api.${var.domain_name}"
    dashboard = "https://dashboard.${var.domain_name}"
    docs      = "https://docs.${var.domain_name}"
  }
}

output "monitoring_endpoints" {
  description = "Monitoring and observability endpoints"
  value = {
    prometheus = "https://prometheus.${var.domain_name}"
    grafana    = "https://grafana.${var.domain_name}"
    loki       = "https://loki.${var.domain_name}"
  }
}

output "terraform_workspace" {
  description = "Terraform workspace name"
  value       = terraform.workspace
}

output "deployment_summary" {
  description = "Deployment summary"
  value = {
    environment     = var.environment
    region          = data.aws_region.current.name
    account_id      = data.aws_caller_identity.current.account_id
    eks_version     = aws_eks_cluster.main.version
    node_count      = var.node_group_desired_size
    instance_types  = join(", ", var.node_instance_types)
    db_instance     = aws_db_instance.postgres.instance_class
    cache_instance  = var.elasticache_node_type
    timestamp       = timestamp()
  }
}
