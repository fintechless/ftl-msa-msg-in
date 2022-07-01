src = {
  backend    = "s3"
  config_key = "terraform/fintechless/ftl-msa-msg-in/aws_k8s_ingress/terraform.tfstate"

  name = "ftl-msa-msg-in-tg"
}

tags = {
  Description = "AWS LB Target Group for MSA MSG IN -- Used by the VPC Link NLB"
}
