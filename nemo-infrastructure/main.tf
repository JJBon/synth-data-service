locals {
  name   = "nemo-data-cluster"
  region = "us-east-1"

  tags = {
    Project    = "nemo-microservices"
    Environment = "dev"
    Terraform   = "true"
  }
}

################################################################################
# Networking (Default VPC)
################################################################################

data "aws_vpc" "default" {
  default = true
}

# Filter subnets to valid AZs for EKS (us-east-1a, 1b, 1c, 1d, 1f)
# Explicitly excluding us-east-1e as per error message
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "availability-zone"
    values = ["us-east-1a", "us-east-1b", "us-east-1c", "us-east-1d", "us-east-1f"]
  }
}

################################################################################
# EKS Cluster
################################################################################

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = local.name
  cluster_version = "1.30"

  cluster_endpoint_public_access  = true
  
  # Give the creator of the cluster admin permissions
  enable_cluster_creator_admin_permissions = true

  vpc_id     = data.aws_vpc.default.id
  subnet_ids = data.aws_subnets.default.ids

  eks_managed_node_group_defaults = {
    ami_type = "AL2_x86_64"
    
    # Explicitly configure network interface to request Public IP
    # This is required for Default VPC without NAT Gateway
    network_interfaces = [{
      delete_on_termination       = true
      associate_public_ip_address = true
    }]

    # Grant permissions for EBS CSI Driver (Lazy fix since IRSA isn't set up)
    iam_role_additional_policies = {
      AmazonEBSCSIDriverPolicy = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
    }
  }

  eks_managed_node_groups = {
    # Lightweight Core: Just enough for system pods + Flux
    core = {
      name = "core-node-group"
      instance_types = ["t3.medium"] # 2 vCPU, 4GB RAM

      min_size     = 1
      max_size     = 2
      desired_size = 1
    }

    # GPU Workload: Scales from 0
    gpu = {
      name = "gpu-node-group"
      instance_types = ["g5.xlarge"] # A10G GPU
      
      ami_type = "AL2_x86_64_GPU"

      # "Resourceful": Keep at 0 until needed
      min_size     = 0
      max_size     = 1
      desired_size = 0

      taints = {
        dedicated = {
          key    = "nvidia.com/gpu"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      }
      
      # Labels to help with scheduling if needed
      labels = {
        "accelerator" = "gpu"
      }
    }
  }

  tags = local.tags
}

################################################################################
# EKS Addons
################################################################################

module "eks_blueprints_addons" {
  source = "aws-ia/eks-blueprints-addons/aws"
  version = "~> 1.16"

  cluster_name      = module.eks.cluster_name
  cluster_endpoint  = module.eks.cluster_endpoint
  cluster_version   = module.eks.cluster_version
  oidc_provider_arn = module.eks.oidc_provider_arn

  eks_addons = {
    aws-ebs-csi-driver = {
      most_recent = true
    }
    coredns = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
  }

  # Enable Load Balancer Controller for Ingress
  enable_aws_load_balancer_controller = true
  
  # Enable Karpenter for smarter scaling (optional, but good for scaling from 0)
  # Keeping it simple for now with standard ASG, user can manually scale or use Cluster Autoscaler
  # enable_karpenter = true 

  tags = local.tags
}

# --- ECR Repositories ---

resource "aws_ecr_repository" "mcp_server" {
  name                 = "mcp-server-sdk"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "streamlit_ui" {
  name                 = "streamlit-ui"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "langgraph_server" {
  name                 = "langgraph-server"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# --- Outputs ---

output "ecr_repository_urls" {
  description = "URLs of the ECR repositories"
  value = {
    mcp_server       = aws_ecr_repository.mcp_server.repository_url
    streamlit_ui     = aws_ecr_repository.streamlit_ui.repository_url
    langgraph_server = aws_ecr_repository.langgraph_server.repository_url
  }
}
