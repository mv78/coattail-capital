#!/bin/bash
set -euo pipefail

# Bootstrap Terraform remote state resources
# Run this ONCE before first terraform init

AWS_REGION="${AWS_REGION:-us-west-2}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
STATE_BUCKET="coattail-capital-tfstate-${ACCOUNT_ID}"
LOCK_TABLE="coattail-capital-tflock"

echo "=== Bootstrapping Terraform State ==="
echo "Region:     ${AWS_REGION}"
echo "Account:    ${ACCOUNT_ID}"
echo "S3 Bucket:  ${STATE_BUCKET}"
echo "Lock Table: ${LOCK_TABLE}"
echo ""

# Create S3 bucket for state
echo "Creating S3 state bucket..."
if aws s3api head-bucket --bucket "${STATE_BUCKET}" 2>/dev/null; then
  echo "  Bucket already exists, skipping."
else
  aws s3api create-bucket \
    --bucket "${STATE_BUCKET}" \
    --region "${AWS_REGION}" \
    --create-bucket-configuration LocationConstraint="${AWS_REGION}"

  aws s3api put-bucket-encryption \
    --bucket "${STATE_BUCKET}" \
    --server-side-encryption-configuration '{
      "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
    }'

  aws s3api put-bucket-versioning \
    --bucket "${STATE_BUCKET}" \
    --versioning-configuration Status=Enabled

  aws s3api put-public-access-block \
    --bucket "${STATE_BUCKET}" \
    --public-access-block-configuration \
      BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

  echo "  Bucket created."
fi

# Create DynamoDB table for state locking
echo "Creating DynamoDB lock table..."
if aws dynamodb describe-table --table-name "${LOCK_TABLE}" --region "${AWS_REGION}" 2>/dev/null; then
  echo "  Table already exists, skipping."
else
  aws dynamodb create-table \
    --table-name "${LOCK_TABLE}" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "${AWS_REGION}"

  echo "  Table created."
fi

echo ""
echo "=== Bootstrap Complete ==="
echo ""
echo "Next steps:"
echo "  1. Uncomment the backend config in infra/backend.tf"
echo "  2. Update the bucket name to: ${STATE_BUCKET}"
echo "  3. Run: cd infra && terraform init"
