src = {
  backend         = "s3"
  config_key_ecr  = "terraform/fintechless/ftl-msa-msg-in/aws_ecr_repository/terraform.tfstate"
  config_key_node = "terraform/fintechless/ftl-msa-msg-in/aws_eks_node_group/terraform.tfstate"

  msa           = "msg-in"
  replicas      = 1
  image_version = "latest"
}
