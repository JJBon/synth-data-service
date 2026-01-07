################################################################################
# AgentCore MCP Server Infrastructure
# Deploys MCP server to AWS Bedrock AgentCore with VPC private networking
################################################################################

################################################################################
# Subnet Detection (Private/Public by tag:type)
################################################################################

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "tag:type"
    values = ["private"]
  }
}

data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "tag:type"
    values = ["public"]
  }
  filter {
    name   = "availability-zone"
    values = ["us-east-1a", "us-east-1b", "us-east-1c", "us-east-1d", "us-east-1f"]
  }
}

data "aws_subnets" "supported" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "tag:type"
    values = ["public"]
  }
  filter {
    name   = "availability-zone"
    values = ["us-east-1b", "us-east-1c", "us-east-1d"]
  }
}

################################################################################
# ECR Repository for MCP Server Container
################################################################################

resource "aws_ecr_repository" "mcp_agentcore" {
  name                 = "mcp-server-agentcore"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.tags
}

################################################################################
# Security Group for AgentCore ENIs
################################################################################

resource "aws_security_group" "agentcore" {
  name        = "agentcore-mcp-sg"
  description = "Security group for AgentCore MCP server ENIs"
  vpc_id      = data.aws_vpc.default.id

  tags = merge(local.tags, { Name = "agentcore-mcp-sg" })
}

resource "aws_vpc_security_group_egress_rule" "allow_all" {
  security_group_id = aws_security_group.agentcore.id
  description       = "Allow all outbound traffic (DNS, HTTPS, etc.)"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "agentcore_ingress" {
  security_group_id = aws_security_group.agentcore.id
  description       = "Allow inbound to MCP server"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

################################################################################
# IAM Role for AgentCore Gateway
################################################################################
# ... (skipping context match, using granular replacement for safety)


################################################################################
# IAM Role for AgentCore Gateway
################################################################################

resource "aws_iam_role" "agentcore_gateway" {
  name = "agentcore-gateway-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "bedrock.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy" "agentcore_logging" {
  name = "agentcore-logging"
  role = aws_iam_role.agentcore_gateway.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "agentcore_gateway" {
  name = "agentcore-gateway-policy"
  role = aws_iam_role.agentcore_gateway.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:InvokeAgentRuntime",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:GetAuthorizationToken",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
      }
    ]
  })
}

################################################################################
# AgentCore Agent Runtime (MCP Server Deployment)
################################################################################

resource "aws_bedrockagentcore_agent_runtime" "mcp_server" {
  agent_runtime_name = "nemo_mcp_server_v9"
  depends_on         = [aws_vpc_endpoint.ecr_api, aws_vpc_endpoint.ecr_dkr, aws_vpc_endpoint.s3, aws_vpc_endpoint.logs]
  role_arn           = aws_iam_role.agentcore_gateway.arn

  agent_runtime_artifact {
    container_configuration {
      container_uri = "${aws_ecr_repository.mcp_agentcore.repository_url}:real-v1"
    }
  }

  network_configuration {
    network_mode = "VPC"
    network_mode_config {
      subnets         = data.aws_subnets.supported.ids
      security_groups = [aws_security_group.agentcore.id]
    }
  }

  environment_variables = {
    NEMO_BASE_URL            = "http://accb172dcda11448d8dadf7a966b1d80-25bd77583b3cf253.elb.us-east-1.amazonaws.com:8080"
    NEMO_DATA_DESIGNER_URL   = "http://accb172dcda11448d8dadf7a966b1d80-25bd77583b3cf253.elb.us-east-1.amazonaws.com:8080"
    MCP_TRANSPORT            = "streamable-http"
    MCP_PORT                 = "8080"
    MCP_HOST                 = "0.0.0.0"
  }

  tags = local.tags
}

# Add Endpoint Resource
resource "aws_bedrockagentcore_agent_runtime_endpoint" "mcp" {
  name             = "nemo_mcp_endpoint"
  agent_runtime_id = aws_bedrockagentcore_agent_runtime.mcp_server.agent_runtime_id
  tags             = local.tags
}

resource "aws_bedrockagentcore_gateway" "mcp" {
  name            = "nemo-mcp-gateway"
  protocol_type   = "MCP"
  role_arn        = aws_iam_role.agentcore_gateway.arn
  authorizer_type = "AWS_IAM"
  description     = "Gateway for NeMo Data Designer MCP server (Terraform Managed Container)"

  tags = local.tags
}

resource "random_id" "target_suffix" {
  byte_length = 4
}

resource "aws_bedrockagentcore_gateway_target" "mcp" {
  gateway_identifier = aws_bedrockagentcore_gateway.mcp.gateway_id
  name               = "mcp-runtime-target-real-${random_id.target_suffix.hex}"

  target_configuration {
    mcp {
      mcp_server {
        endpoint = "https://runtime-bedrock-agentcore.${local.region}.amazonaws.com/runtime/${aws_bedrockagentcore_agent_runtime.mcp_server.agent_runtime_id}/runtime-endpoint/${aws_bedrockagentcore_agent_runtime_endpoint.mcp.name}"
      }
    }
  }
}

################################################################################
# Outputs
################################################################################

output "agentcore_runtime_arn" {
  description = "ARN of the AgentCore MCP runtime"
  value       = aws_bedrockagentcore_agent_runtime.mcp_server.agent_runtime_arn
}

output "agentcore_gateway_url" {
  description = "URL of the AgentCore MCP gateway"
  value       = aws_bedrockagentcore_gateway.mcp.gateway_url
}

output "agentcore_gateway_id" {
  description = "ID of the AgentCore MCP gateway"
  value       = aws_bedrockagentcore_gateway.mcp.gateway_id
}

output "mcp_ecr_repository_url" {
  description = "ECR repository URL for MCP server container"
  value       = aws_ecr_repository.mcp_agentcore.repository_url
}

output "private_subnet_ids" {
  description = "Private subnet IDs for reference"
  value       = data.aws_subnets.private.ids
}
