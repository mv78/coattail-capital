#!/bin/bash
# protect-critical-files.sh
# PreToolUse hook: blocks edits to sensitive files deterministically.
# Exit 0 = allow, Exit 2 = block

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

PROTECTED_PATTERNS=(
  ".env"
  "terraform.tfvars"
  ".git/"
  "secrets/"
  "credentials"
  ".pem"
  ".key"
  "id_rsa"
  "id_ed25519"
)

for pattern in "${PROTECTED_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]]; then
    echo "BLOCKED: Edit to '$FILE_PATH' denied — matches protected pattern '$pattern'" >&2
    exit 2
  fi
done

exit 0
