# A VPC is the private network your cluster lives in.
# Instead of hand-writing subnets, gateways, and route tables (dozens of resources),
# we use the official AWS VPC module — a pre-built blueprint we fill in.

data "aws_availability_zones" "available" {
  state = "available"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.cluster_name}-vpc"
  cidr = "10.0.0.0/16"   # the network's IP address range

  # Use 2 availability zones (data centers) for the cluster.
  azs             = slice(data.aws_availability_zones.available.names, 0, 2)
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]   # where worker nodes run (not public)
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"] # where the load balancer lives

  enable_nat_gateway   = true   # lets private nodes reach the internet (for pulling images)
  single_nat_gateway   = true   # use ONE nat gateway instead of one-per-AZ -> cheaper
  enable_dns_hostnames = true

  # These tags tell AWS which subnets EKS can use for load balancers.
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }
}
