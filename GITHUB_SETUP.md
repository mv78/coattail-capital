# GitHub Setup Guide

## For Mike Veksler (Repo Owner)

### Step 1: Create the Repository

```bash
# Go to GitHub and create a new repo:
# https://github.com/new
# 
# Repository name: coattail-capital
# Description: "Riding smart money so you don't have to think 🐋"
# Visibility: Public (for portfolio) or Private (while building)
# Do NOT initialize with README, .gitignore, or license (we have these)
```

### Step 2: Initialize and Push

```bash
# Extract the project
tar xzf coattail-capital-principal.tar.gz
cd coattail-capital

# Initialize git
git init
git add .
git commit -m "Initial commit: Coat Tail Capital - whale tracking analytics platform

- Real-time CEX data ingestion (Binance, Coinbase)
- PySpark Structured Streaming on EMR Serverless
- Data quality framework with DLQ routing
- Apache Iceberg lakehouse on S3
- Step Functions batch orchestration
- Lake Formation data governance
- BMAD agentic development specs

Co-authored-by: Frank D'Avanzo <frank@example.com>"

# Add remote and push
git remote add origin git@github.com:mveksler/coattail-capital.git
git branch -M main
git push -u origin main
```

### Step 3: Add Frank as Collaborator

1. Go to: `https://github.com/mveksler/coattail-capital/settings/access`
2. Click "Add people"
3. Search for `TheFrankBuilder`
4. Select "Write" access (or "Admin" if you want him to manage settings too)
5. Click "Add TheFrankBuilder to this repository"

Frank will get an email to accept the invitation.

### Step 4: Set Up Branch Protection (Optional but Recommended)

1. Go to: `https://github.com/mveksler/coattail-capital/settings/branches`
2. Click "Add rule"
3. Branch name pattern: `main`
4. Enable:
   - ✅ Require a pull request before merging
   - ✅ Require approvals (1)
   - ✅ Require status checks to pass (select `lint-and-test`, `terraform-validate`)
5. Click "Create"

This ensures you both review each other's code.

### Step 5: Enable GitHub Actions

Actions should be enabled by default. Verify at:
`https://github.com/mveksler/coattail-capital/actions`

The CI workflow will run on every PR and push to main.

---

## For Frank D'Avanzo (Collaborator)

### After Mike Adds You

```bash
# Accept the collaboration invite (check email or GitHub notifications)

# Clone the repo
git clone git@github.com:mveksler/coattail-capital.git
cd coattail-capital

# Create your feature branch
git checkout -b frank/day1-producer

# Make changes, commit, push
git add .
git commit -m "feat: implement Kinesis producer for Binance WebSocket"
git push -u origin frank/day1-producer

# Create PR on GitHub for Mike to review
```

### Recommended Branch Naming

```
mike/day1-infra          # Mike's Day 1 infrastructure work
frank/day1-producer      # Frank's Day 1 producer work
mike/day2-spark-jobs     # Mike's Day 2 PySpark jobs
frank/day2-data-quality  # Frank's Day 2 data quality module
```

---

## Workflow During the Weekend

### Saturday Morning

```bash
# Both: Pull latest main
git checkout main
git pull

# Mike: Start on infrastructure
git checkout -b mike/day1-infra

# Frank: Start on specs review
git checkout -b frank/day1-specs
```

### When Ready to Merge

```bash
# Push your branch
git push -u origin mike/day1-infra

# Create PR on GitHub
# Add the other person as reviewer
# Wait for CI to pass
# Get approval, merge to main
```

### After Merge

```bash
# Both: Update local main
git checkout main
git pull

# Start next feature branch from updated main
git checkout -b mike/day2-spark-jobs
```

---

## Secrets Setup (For AWS Deployment via CI)

If you want GitHub Actions to deploy to AWS automatically:

1. Go to: `https://github.com/mveksler/coattail-capital/settings/secrets/actions`
2. Add these secrets:
   - `AWS_ACCESS_KEY_ID` — Your AWS access key
   - `AWS_SECRET_ACCESS_KEY` — Your AWS secret key
   - `AWS_REGION` — `us-west-2`

**Note:** For the weekend project, you'll likely deploy manually from your laptops. CI secrets are optional.

---

## Useful Git Commands

```bash
# See what branch you're on
git branch

# See all branches (local + remote)
git branch -a

# Switch to existing branch
git checkout main

# Create and switch to new branch
git checkout -b feature/new-thing

# See status of changes
git status

# Stage all changes
git add .

# Commit with message
git commit -m "feat: add whale detection logic"

# Push current branch
git push

# Pull latest from remote
git pull

# See commit history
git log --oneline -10

# Discard local changes to a file
git checkout -- path/to/file

# Stash changes temporarily
git stash
git stash pop
```

---

## Commit Message Convention

Use conventional commits for clean history:

```
feat: add new feature
fix: fix a bug
docs: documentation changes
refactor: code refactoring
test: add or update tests
chore: maintenance tasks
```

Examples:
```
feat: implement volume anomaly detection Spark job
fix: handle null timestamps in trade events
docs: add architecture diagram to README
refactor: extract data quality checks to common module
test: add unit tests for whale threshold detection
chore: update Terraform provider versions
```
