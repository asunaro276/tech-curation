REGION  := ap-northeast-1
TFSTATE := s3://tfstate-nakano/tech-curation/terraform.tfstate

# Resolve ECR URL from terraform output after `make apply`
ECR_URL := $(shell cd terraform && terraform output -raw ecr_repository_url 2>/dev/null)

.PHONY: init apply build deploy

init:
	cd terraform && terraform init

apply:
	cd terraform && terraform apply

build:
	@if [ -z "$(ECR_URL)" ]; then echo "ERROR: ECR_URL not set. Run 'make apply' first."; exit 1; fi
	aws ecr get-login-password --region $(REGION) | \
	  docker login --username AWS --password-stdin $(ECR_URL)
	docker build -t $(ECR_URL):latest .
	docker push $(ECR_URL):latest

deploy: build
	lambroll deploy \
	  --skip-configuration \
	  --tfstate $(TFSTATE) \
	  --function lambroll/collect/function.json
	lambroll deploy \
	  --skip-configuration \
	  --tfstate $(TFSTATE) \
	  --function lambroll/improve/function.json
