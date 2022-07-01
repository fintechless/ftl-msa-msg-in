src = {
  backend    = "s3"
  config_key = "terraform/fintechless/ftl-msa-msg-in/aws_k8s_deployment/terraform.tfstate"

  msa            = "msg-in"
  container_port = 5001
}
