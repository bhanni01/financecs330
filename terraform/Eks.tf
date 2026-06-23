# The EKS cluster itself, plus its worker nodes.
# Again we use the official EKS module — the pre-built blueprint that expands
# into the cluster, node group, IAM roles, and security groups for us.

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = "1.30"

  # Run the cluster inside the VPC we defined in vpc.tf
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # Let your laptop (the creator) access the cluster's API to run kubectl.
  cluster_endpoint_public_access           = true
  enable_cluster_creator_admin_permissions = true

  # The worker nodes: the actual servers your app pods run on.
  eks_managed_node_groups = {
    default = {
      # t3.small is small & cheap; 2 nodes is enough for a demo.
      instance_types = ["t3.small"]
      min_size       = 1
      max_size       = 3
      desired_size   = 2
    }
  }
}

# After the cluster is built, print the command to connect kubectl to it.
output "configure_kubectl" {
  description = "Run this to point kubectl at your new EKS cluster"
  value       = "aws eks update-kubeconfig --region ${var.region} --name ${var.cluster_name}"
}
