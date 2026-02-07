#!/bin/bash
set -euo pipefail

# Stop the Crypto Pulse Analytics streaming pipeline
# Stops producer and cancels EMR Serverless jobs

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
INFRA_DIR="${PROJECT_DIR}/infra"

echo "=== Stopping Crypto Pulse Analytics ==="

# Load Terraform outputs
cd "$INFRA_DIR"
EMR_APP_ID=$(terraform output -raw emr_application_id 2>/dev/null || echo "")
cd "$PROJECT_DIR"

# Step 1: Stop the Kinesis producer
echo "Stopping Kinesis producer..."
if [ -f /tmp/crypto-pulse-producer.pid ]; then
  PRODUCER_PID=$(cat /tmp/crypto-pulse-producer.pid)
  if kill -0 "$PRODUCER_PID" 2>/dev/null; then
    kill "$PRODUCER_PID"
    echo "  Producer (PID ${PRODUCER_PID}) stopped."
  else
    echo "  Producer was not running."
  fi
  rm -f /tmp/crypto-pulse-producer.pid
else
  echo "  No producer PID file found."
  # Try to find and kill any running producer
  pkill -f "python.*main.py" 2>/dev/null && echo "  Killed orphan producer process." || echo "  No orphan process found."
fi

# Step 2: Cancel EMR Serverless jobs
if [ -n "$EMR_APP_ID" ]; then
  echo "Cancelling EMR Serverless jobs..."
  RUNNING_JOBS=$(aws emr-serverless list-job-runs \
    --application-id "${EMR_APP_ID}" \
    --states RUNNING SUBMITTED PENDING \
    --query 'jobRuns[].id' --output text 2>/dev/null || echo "")

  if [ -n "$RUNNING_JOBS" ]; then
    for JOB_ID in $RUNNING_JOBS; do
      echo "  Cancelling job: ${JOB_ID}"
      aws emr-serverless cancel-job-run \
        --application-id "${EMR_APP_ID}" \
        --job-run-id "${JOB_ID}" 2>/dev/null || true
    done
  else
    echo "  No running jobs found."
  fi
else
  echo "  Could not determine EMR application ID. Skipping."
fi

# Cleanup temp files
rm -f /tmp/crypto-pulse-jobs.txt

echo ""
echo "=== Streaming Pipeline Stopped ==="
echo ""
echo "Remaining costs (idle):"
echo "  S3 storage:  <\$0.01/day"
echo "  DynamoDB:    \$0 (no reads/writes)"
echo "  Kinesis:     ~\$0.04/hour (on-demand minimum)"
echo ""
echo "To fully stop Kinesis charges, run: terraform destroy"
echo "To restart:  ./scripts/start.sh"
