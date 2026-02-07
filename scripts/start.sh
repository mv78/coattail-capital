#!/bin/bash
set -euo pipefail

# Start the Crypto Pulse Analytics streaming pipeline
# This starts the producer and submits Spark jobs to EMR Serverless

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
INFRA_DIR="${PROJECT_DIR}/infra"

echo "=== Starting Crypto Pulse Analytics ==="

# Load Terraform outputs
echo "Loading infrastructure configuration..."
cd "$INFRA_DIR"
KINESIS_STREAM=$(terraform output -raw kinesis_stream_name)
EMR_APP_ID=$(terraform output -raw emr_application_id)
EMR_ROLE_ARN=$(terraform output -raw emr_execution_role_arn)
PROCESSED_BUCKET=$(terraform output -raw processed_bucket)
CHECKPOINT_BUCKET=$(terraform output -raw checkpoint_bucket)
ALERTS_TABLE=$(terraform output -raw dynamodb_alerts_table)
GLUE_DATABASE=$(terraform output -raw glue_database)
cd "$PROJECT_DIR"

echo "  Kinesis Stream: ${KINESIS_STREAM}"
echo "  EMR App:        ${EMR_APP_ID}"
echo "  S3 Processed:   ${PROCESSED_BUCKET}"
echo ""

# Step 1: Upload latest Spark jobs to S3
echo "Uploading Spark jobs to S3..."
aws s3 sync src/spark-jobs/ "s3://${PROCESSED_BUCKET}/jobs/" --exclude "__pycache__/*" --exclude "*.pyc"
echo "  Done."

# Step 2: Start the Kinesis producer
echo "Starting Kinesis producer..."
export KINESIS_STREAM_NAME="${KINESIS_STREAM}"
export AWS_REGION="${AWS_REGION:-us-west-2}"
export SYMBOLS="${SYMBOLS:-btcusdt,ethusdt,solusdt}"

cd src/producer
nohup python main.py > /tmp/crypto-pulse-producer.log 2>&1 &
PRODUCER_PID=$!
echo "  Producer PID: ${PRODUCER_PID}"
echo "${PRODUCER_PID}" > /tmp/crypto-pulse-producer.pid
cd "$PROJECT_DIR"

# Wait for producer to initialize
sleep 5
if kill -0 "$PRODUCER_PID" 2>/dev/null; then
  echo "  Producer running."
else
  echo "  ERROR: Producer failed to start. Check /tmp/crypto-pulse-producer.log"
  exit 1
fi

# Step 3: Submit PySpark streaming jobs to EMR Serverless
echo "Submitting Spark jobs to EMR Serverless..."

SPARK_PARAMS="--conf spark.jars.packages=org.apache.iceberg:iceberg-spark-runtime-3.4_2.12:1.4.2 \
--conf spark.sql.catalog.glue_catalog=org.apache.iceberg.spark.SparkCatalog \
--conf spark.sql.catalog.glue_catalog.catalog-impl=org.apache.iceberg.aws.glue.GlueCatalog \
--conf spark.sql.catalog.glue_catalog.warehouse=s3://${PROCESSED_BUCKET}/iceberg/ \
--conf spark.streaming.kinesis.stream=${KINESIS_STREAM} \
--conf spark.crypto.dynamodb.table=${ALERTS_TABLE} \
--conf spark.crypto.checkpoint.path=s3://${CHECKPOINT_BUCKET}/checkpoints/"

for JOB in volume_anomaly whale_detector spread_calculator; do
  echo "  Submitting ${JOB}..."
  JOB_RUN_ID=$(aws emr-serverless start-job-run \
    --application-id "${EMR_APP_ID}" \
    --execution-role-arn "${EMR_ROLE_ARN}" \
    --job-driver "{
      \"sparkSubmit\": {
        \"entryPoint\": \"s3://${PROCESSED_BUCKET}/jobs/${JOB}.py\",
        \"sparkSubmitParameters\": \"${SPARK_PARAMS}\"
      }
    }" \
    --query 'jobRunId' --output text)
  echo "    Job Run ID: ${JOB_RUN_ID}"
  echo "${JOB}=${JOB_RUN_ID}" >> /tmp/crypto-pulse-jobs.txt
done

echo ""
echo "=== Streaming Pipeline Started ==="
echo ""
echo "Monitor:"
echo "  Producer log:  tail -f /tmp/crypto-pulse-producer.log"
echo "  EMR jobs:      aws emr-serverless list-job-runs --application-id ${EMR_APP_ID}"
echo "  Kinesis:       aws kinesis describe-stream-summary --stream-name ${KINESIS_STREAM}"
echo "  CloudWatch:    $(terraform -chdir=${INFRA_DIR} output -raw cloudwatch_dashboard_url)"
echo ""
echo "Stop with: ./scripts/stop.sh"
